import os
import argparse
import time
import random
from ddgs import DDGS

def find_career_page(company_name: str) -> str:
    print(f"Finding career page for: {company_name}...")
    query = f"{company_name} careers"
    
    try:
        # DDGS handles rate limits and bypassing automatically
        results = list(DDGS().text(query, max_results=1))
        if results:
            url = results[0].get("href", "")
            # Filter out obvious non-career junk
            if not any(bad in url for bad in ["wikipedia.org", "linkedin.com", "indeed.com", "glassdoor.com", "salary.com", "bloomberg.com"]):
                return url
    except Exception as e:
        print(f"Error scraping DDG for {company_name}: {e}")
        
    return None

def main():
    parser = argparse.ArgumentParser(description="Find precise career pages for Big Tech companies using DDGS.")
    parser.add_argument("--input", type=str, default="data/company_names.txt", help="File with company names.")
    parser.add_argument("--output", type=str, default="data/source_seeds/company_career_pages.txt", help="Output file for career page links.")
    parser.add_argument("--limit", type=int, default=1500, help="Max companies to process in this run.")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Input file not found: {args.input}")
        return

    with open(args.input, "r", encoding="utf-8") as f:
        companies = [line.strip() for line in f if line.strip()][:args.limit]
    
    found_pages = set()
    for company in companies:
        career_url = find_career_page(company)
        if career_url:
            print(f"  -> Found: {career_url}")
            found_pages.add(career_url)
        else:
            print("  -> Not found or skipped.")
            
        # DDGS is robust, but a small sleep is still polite
        time.sleep(random.uniform(1.0, 2.5))

    if found_pages:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "a", encoding="utf-8") as f:
            for url in found_pages:
                f.write(url + "\n")
        print(f"\nTotal career pages found: {len(found_pages)}")
        print(f"Appended to {args.output}")
        print(f"You can now run: python scripts/discover_job_sources.py --all --career-pages-file {args.output} --test --store --skip-existing")

if __name__ == "__main__":
    main()
