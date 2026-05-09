import os
import sys
import json
import csv
import argparse
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import List, Set, Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.job_finder.source_normalizer import normalize_ats_board_url
from backend.app.services.job_finder.source_tester import test_job_source
from backend.app.database import SessionLocal, Base, engine
from backend.app.models.job_source import JobSource
from sqlalchemy.orm import Session

load_dotenv()

# Pre-compile a regex for finding URLs in text
URL_REGEX = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')

# Ensure DB schema exists
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def extract_urls_from_text(text: str) -> List[str]:
    return URL_REGEX.findall(text)

def process_seed_file(file_path: str) -> List[str]:
    if not os.path.exists(file_path):
        print(f"Seed file not found: {file_path}")
        return []
    
    urls = []
    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.endswith(".json"):
            try:
                data = json.load(f)
                if isinstance(data, list):
                    urls = [item for item in data if isinstance(item, str)]
            except json.JSONDecodeError:
                pass
        else:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
    return urls

def process_pasted_results(file_path: str) -> List[str]:
    if not os.path.exists(file_path):
        print(f"Pasted results file not found: {file_path}")
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return extract_urls_from_text(text)

def discover_from_career_pages(file_path: str) -> List[str]:
    if not os.path.exists(file_path):
        print(f"Career pages file not found: {file_path}")
        return []
    
    urls = process_seed_file(file_path)
    discovered = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    for url in urls:
        try:
            print(f"Fetching career page: {url}")
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                page_urls = extract_urls_from_text(res.text)
                # Filter to known ATS
                for pu in page_urls:
                    if any(domain in pu for domain in [
                        "jobs.lever.co", "boards.greenhouse.io", "job-boards.greenhouse.io",
                        "jobs.ashbyhq.com", "myworkdayjobs.com", "workdayjobs.com"
                    ]):
                        discovered.append(pu)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            
    return discovered

def run_search_api(provider: str, api_key: str, limit: int) -> List[str]:
    """
    Executes a search via a supported Search API (e.g., SerpApi) to discover links programmatically.
    """
    print(f"Using Search API: {provider}")
    urls = []
    
    if provider.lower() == "serpapi":
        # SerpApi implementation
        # Uses standard Google search
        # E.g. https://serpapi.com/search.json?q=site:jobs.lever.co+OR+site:boards.greenhouse.io&api_key=...
        
        # We will cycle through a few standard queries to get a broad set of results
        queries = [
            'site:jobs.lever.co "Data Engineer" OR "Software Engineer"',
            'site:boards.greenhouse.io "Data Engineer" OR "Software Engineer"',
            'site:jobs.ashbyhq.com "Data Engineer" OR "Software Engineer"',
            'site:myworkdayjobs.com "Data Engineer" OR "Software Engineer"'
        ]
        
        for q in queries:
            if len(urls) >= limit:
                break
            try:
                print(f"Executing query: {q}")
                res = requests.get("https://serpapi.com/search.json", params={
                    "engine": "google",
                    "q": q,
                    "api_key": api_key,
                    "num": min(100, limit - len(urls)) # Request max 100 per page
                }, timeout=15)
                
                if res.status_code == 200:
                    data = res.json()
                    organic_results = data.get("organic_results", [])
                    for result in organic_results:
                        link = result.get("link")
                        if link:
                            urls.append(link)
                else:
                    print(f"SerpApi Error: {res.status_code}")
            except Exception as e:
                print(f"Error calling SerpApi: {e}")
    else:
        print(f"Search API provider '{provider}' is not supported yet.")
        
    return urls

def main():
    parser = argparse.ArgumentParser(description="CareerAgent Source Discovery Script")
    parser.add_argument("--all", action="store_true", help="Run all sources")
    parser.add_argument("--source", action="append", choices=["lever", "greenhouse", "ashby", "workday", "company_careers"], help="Specific source to run")
    parser.add_argument("--seed-file", type=str, help="Path to seed file")
    parser.add_argument("--pasted-results-file", type=str, help="Path to pasted results file")
    parser.add_argument("--career-pages-file", type=str, help="Path to company career pages file")
    parser.add_argument("--limit", type=int, default=500, help="Max sources to process")
    parser.add_argument("--test", action="store_true", help="Test sources")
    parser.add_argument("--store", action="store_true", help="Store sources in database")
    parser.add_argument("--keep-invalid", action="store_true", help="Store even if invalid")
    parser.add_argument("--export-json", type=str, help="Export to JSON path")
    parser.add_argument("--export-csv", type=str, help="Export to CSV path")
    parser.add_argument("--dry-run", action="store_true", help="Do not save to DB")
    parser.add_argument("--skip-existing", action="store_true", help="Skip testing sources already in the database")
    
    args = parser.parse_args()

    # Determine which sources are allowed
    allowed_sources = set(args.source) if args.source else set()
    if args.all:
        allowed_sources = {"lever", "greenhouse", "ashby", "workday", "company_careers", "unknown"}

    raw_urls = set()

    # 1. Seed file
    if args.seed_file:
        raw_urls.update(process_seed_file(args.seed_file))

    # 2. Pasted results
    if args.pasted_results_file:
        raw_urls.update(process_pasted_results(args.pasted_results_file))

    # 3. Optional Search API
    search_provider = os.getenv("SEARCH_PROVIDER", "none")
    search_api_key = os.getenv("SEARCH_API_KEY", "")
    if search_provider != "none" and search_api_key:
        api_limit = int(os.getenv("SEARCH_MAX_RESULTS", 50))
        raw_urls.update(run_search_api(search_provider, search_api_key, api_limit))
    else:
        print("Search API not configured. Using seed/pasted links only.")

    # 4. Career pages
    if args.career_pages_file:
        raw_urls.update(discover_from_career_pages(args.career_pages_file))

    print(f"Found {len(raw_urls)} raw URLs to process.")

    # Normalization
    normalized_sources: Dict[str, dict] = {}
    
    for url in list(raw_urls)[:args.limit]:
        norm = normalize_ats_board_url(url)
        ats_type = norm["ats_type"]
        
        if ats_type == "unknown" and "unknown" not in allowed_sources:
            continue
        if ats_type != "unknown" and ats_type not in allowed_sources and not args.all:
            continue
            
        base_url = norm["base_url"]
        
        # Dedupe by normalized lower case to handle lever casing collisions
        dedupe_key = base_url.lower()
        if dedupe_key not in normalized_sources:
            norm["discovery_method"] = "script"
            normalized_sources[dedupe_key] = norm

    sources_to_process = list(normalized_sources.values())
    print(f"Normalized to {len(sources_to_process)} unique base boards.")

    # Filter out existing if requested
    if args.skip_existing:
        db = next(get_db())
        new_sources = []
        skipped = 0
        for src in sources_to_process:
            dedupe_key = src["base_url"].lower()
            if db.query(JobSource).filter(JobSource.normalized_url == dedupe_key).first():
                skipped += 1
            else:
                new_sources.append(src)
        sources_to_process = new_sources
        print(f"Skipped {skipped} existing sources. Testing {len(sources_to_process)} new sources.")

    # Testing
    if args.test:
        print("Testing sources...")
        for src in sources_to_process:
            if src["ats_type"] == "unknown":
                src["status"] = "unsupported"
                src["jobs_found"] = 0
                continue
                
            test_res = test_job_source(src)
            src["status"] = test_res.get("status", "unsupported")
            src["jobs_found"] = test_res.get("jobs_found", 0)
            src["error"] = test_res.get("error")
            src["warnings"] = test_res.get("warnings", [])
            print(f"Tested {src['base_url']} -> {src['status']} ({src['jobs_found']} jobs)")
    else:
        for src in sources_to_process:
            src["status"] = "untested"
            src["jobs_found"] = 0

    # Filter out invalid sources from the export list if we tested them and didn't ask to keep them
    if args.test and not args.keep_invalid:
        original_count = len(sources_to_process)
        sources_to_process = [s for s in sources_to_process if s.get("status") in ["valid", "partial"]]
        print(f"\nFiltered out {original_count - len(sources_to_process)} invalid sources. Exporting/Storing {len(sources_to_process)} valid sources.")

    # Storing
    if args.store and not args.dry_run:
        print("Storing in DB...")
        db = next(get_db())
        
        stored_count = 0
        for src in sources_to_process:
            is_valid = src.get("status") in ["valid", "partial"]

            dedupe_key = src["base_url"].lower()
            existing = db.query(JobSource).filter(JobSource.normalized_url == dedupe_key).first()
            
            if existing:
                existing.status = src.get("status", "valid")
                existing.total_jobs_found = src.get("jobs_found", 0)
                existing.enabled = is_valid if args.test else existing.enabled
                if src.get("error"):
                    existing.last_error = src["error"]
                if is_valid:
                    from datetime import datetime
                    existing.last_success_at = datetime.utcnow()
            else:
                new_src = JobSource(
                    company=src.get("company"),
                    ats_type=src.get("ats_type"),
                    base_url=src["base_url"], # preserves casing
                    normalized_url=dedupe_key,
                    discovery_method=src.get("discovery_method"),
                    enabled=is_valid if args.test else True,
                    status=src.get("status", "untested"),
                    total_jobs_found=src.get("jobs_found", 0),
                    last_error=src.get("error")
                )
                db.add(new_src)
            stored_count += 1
            
        db.commit()
        print(f"Stored/Updated {stored_count} sources in database.")

    # Determine what to export: if we stored to DB, pull everything from DB to preserve history
    if args.store and not args.dry_run:
        db = next(get_db())
        # Fetch all enabled sources
        all_db_sources = db.query(JobSource).filter(JobSource.enabled == True).all()
        export_list = []
        for s in all_db_sources:
            export_list.append({
                "company": s.company,
                "ats_type": s.ats_type,
                "base_url": s.base_url,
                "normalized_url": s.normalized_url,
                "status": s.status,
                "jobs_found": s.total_jobs_found,
                "error": s.last_error,
                "discovery_method": s.discovery_method
            })
        print(f"\nPulled {len(export_list)} total valid sources from the database for export.")
    else:
        export_list = sources_to_process

    # Export JSON
    if args.export_json:
        os.makedirs(os.path.dirname(args.export_json), exist_ok=True)
        with open(args.export_json, "w", encoding="utf-8") as f:
            json.dump(export_list, f, indent=2)
        print(f"Exported JSON to {args.export_json}")

    # Export CSV
    if args.export_csv:
        os.makedirs(os.path.dirname(args.export_csv), exist_ok=True)
        keys = ["company", "ats_type", "base_url", "normalized_url", "status", "jobs_found", "last_error", "discovery_method"]
        with open(args.export_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for src in export_list:
                writer.writerow({
                    "company": src.get("company"),
                    "ats_type": src.get("ats_type"),
                    "base_url": src.get("base_url"),
                    "normalized_url": src.get("normalized_url", src.get("base_url", "").lower()),
                    "status": src.get("status"),
                    "jobs_found": src.get("jobs_found", 0),
                    "last_error": src.get("error", ""),
                    "discovery_method": src.get("discovery_method", "")
                })
        print(f"Exported CSV to {args.export_csv}")

    print("\nSummary:")
    print(f"Newly processed this run: {len(sources_to_process)}")
    valid_count = sum(1 for s in sources_to_process if s.get("status") in ["valid", "partial"])
    print(f"Newly Valid/Partial this run: {valid_count}")
    if args.store and not args.dry_run:
        print(f"Total Valid in Database (Exported): {len(export_list)}")

if __name__ == "__main__":
    main()
