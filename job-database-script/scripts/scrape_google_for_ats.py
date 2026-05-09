import os
import requests
from bs4 import BeautifulSoup
import argparse
import time
import random
import re

# List of common User-Agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5.2 Safari/605.1.15",
]

def scrape_google(query: str, pages: int = 1) -> list[str]:
    """
    Scrapes Google search results for the given query directly without an API.
    """
    print(f"Scraping Google for: {query}")
    urls = set()
    
    for page in range(pages):
        start = page * 10
        url = f"https://www.google.com/search?q={query}&start={start}"
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                # Find all links
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    # Google result links sometimes look like /url?q=https://...
                    if "/url?q=" in href:
                        href = href.split("/url?q=")[1].split("&")[0]
                        
                    # Basic filter for ATS boards
                    if any(board in href for board in ["jobs.lever.co", "boards.greenhouse.io", "jobs.ashbyhq.com", "myworkdayjobs.com"]):
                        urls.add(href)
            elif res.status_code == 429:
                print("Rate limited by Google (429 Too Many Requests). Stopping.")
                break
            else:
                print(f"Failed to fetch Google page. Status: {res.status_code}")
                
            # Random delay to avoid quick bans
            time.sleep(random.uniform(2.0, 5.0))
            
        except Exception as e:
            print(f"Error scraping Google: {e}")
            break
            
    return list(urls)

def main():
    parser = argparse.ArgumentParser(description="Scrape Google directly for ATS links.")
    parser.add_argument("--output", type=str, default="data/source_seeds/ats_sources_seed.txt", help="Path to append found links.")
    parser.add_argument("--pages", type=int, default=3, help="Number of Google search pages to scrape per query.")
    args = parser.parse_args()

    queries = [
        'site:jobs.lever.co "Data Engineer" OR "Software Engineer"',
        'site:boards.greenhouse.io "Data Engineer" OR "Software Engineer"',
        'site:jobs.ashbyhq.com "Data Engineer" OR "Software Engineer"'
    ]

    all_found = set()
    for q in queries:
        found = scrape_google(q, pages=args.pages)
        print(f"Found {len(found)} links for query: {q}")
        all_found.update(found)
        time.sleep(random.uniform(3.0, 7.0))

    if all_found:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "a", encoding="utf-8") as f:
            for url in all_found:
                f.write(url + "\n")
        print(f"\nTotal unique ATS links scraped from Google: {len(all_found)}")
        print(f"Appended to {args.output}")
        print(f"You can now run: python scripts/discover_job_sources.py --all --seed-file {args.output} --test --store")
    else:
        print("\nNo links found. Google may have blocked the requests. Consider using undetected-chromedriver or an API if this persists.")

if __name__ == "__main__":
    main()
