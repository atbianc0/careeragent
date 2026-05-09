import os
import argparse
import time
import random
from ddgs import DDGS

def scrape_ddg_ats(ats_domain: str, keyword: str) -> list[str]:
    print(f"Scraping DDG for {ats_domain} with keyword '{keyword}'...")
    urls = set()
    query = f"site:{ats_domain} {keyword}"
    
    try:
        # DDGS bypasses rate limits
        results = list(DDGS().text(query, max_results=50))
        for res in results:
            url = res.get("href", "")
            if ats_domain in url:
                urls.add(url)
    except Exception as e:
        print(f"Error scraping DDG: {e}")
        
    time.sleep(random.uniform(1.0, 2.0))
    return list(urls)

def main():
    parser = argparse.ArgumentParser(description="Mass Scrape DuckDuckGo for Valid Startup ATS Links using DDGS.")
    parser.add_argument("--output", type=str, default="data/source_seeds/ats_sources_seed.txt", help="Path to append found links.")
    args = parser.parse_args()

    ats_domains = ["jobs.lever.co", "boards.greenhouse.io", "jobs.ashbyhq.com"]
    keywords = [
        "engineer", "software", "data", "developer", "product", "design", "marketing", "sales", 
        "analyst", "manager", "director", "operations", "recruiter", "accountant", "finance", "legal"
    ]

    all_found = set()
    for ats in ats_domains:
        for kw in keywords:
            found = scrape_ddg_ats(ats, kw)
            print(f"  -> Found {len(found)} links.")
            all_found.update(found)

    if all_found:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "a", encoding="utf-8") as f:
            for url in all_found:
                f.write(url + "\n")
        print(f"\nTotal unique ATS links scraped from DuckDuckGo: {len(all_found)}")
        print(f"Appended to {args.output}")
        print(f"You can now run: python scripts/discover_job_sources.py --all --seed-file {args.output} --test --store --skip-existing")
    else:
        print("\nNo links found. DDG may have temporarily blocked the IP, or ddgs needs an update.")

if __name__ == "__main__":
    main()
