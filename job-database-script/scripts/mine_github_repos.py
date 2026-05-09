import os
import requests
import re
import argparse
import time

def extract_urls_from_text(text: str) -> list[str]:
    # We only care about known ATS platforms
    URL_REGEX = re.compile(r'https?://(?:jobs\.lever\.co|boards\.greenhouse\.io|jobs\.ashbyhq\.com|[^"\'\s]+\.myworkdayjobs\.com)[^\s<>"\']*')
    return URL_REGEX.findall(text)

def mine_repo(repo_url: str) -> list[str]:
    print(f"Mining {repo_url}...")
    try:
        res = requests.get(repo_url, timeout=15)
        if res.status_code == 200:
            return extract_urls_from_text(res.text)
        else:
            print(f"Failed to fetch {repo_url}: {res.status_code}")
    except Exception as e:
        print(f"Error fetching {repo_url}: {e}")
    return []

def main():
    parser = argparse.ArgumentParser(description="Mine public GitHub repos for ATS links.")
    parser.add_argument("--output", type=str, default="data/source_seeds/ats_sources_seed.txt", help="Path to append found links.")
    args = parser.parse_args()

    # List of known public markdown files containing lots of tech company links
    TARGETS = [
        "https://raw.githubusercontent.com/poteto/hiring-without-whiteboards/master/README.md",
        "https://raw.githubusercontent.com/j-delaney/easy-application/master/README.md",
        "https://raw.githubusercontent.com/pittcsc/Summer2024-Internships/dev/README.md",
        "https://raw.githubusercontent.com/SimplifyJobs/Summer2024-Internships/dev/README.md",
        "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md",
        "https://raw.githubusercontent.com/Ouckah/Summer2025-Internships/main/README.md",
        "https://raw.githubusercontent.com/cvrve/Summer2025-Internships/main/README.md",
        "https://raw.githubusercontent.com/bsovs/Fall2024-Internships/main/README.md",
        "https://raw.githubusercontent.com/AlanChen4/Summer-2024-SWE-Internships/main/README.md"
    ]

    all_urls = set()
    for target in TARGETS:
        found = mine_repo(target)
        print(f"Found {len(found)} raw ATS links from {target}")
        all_urls.update(found)
        time.sleep(1) # Be polite to GitHub raw servers

    # Clean trailing punctuation from markdown links
    cleaned_urls = set()
    for url in all_urls:
        url = url.rstrip(").,") # remove markdown parenthesis or punctuation
        cleaned_urls.add(url)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "a", encoding="utf-8") as f:
        for url in cleaned_urls:
            f.write(url + "\n")

    print(f"\nTotal unique ATS links mined: {len(cleaned_urls)}")
    print(f"Appended to {args.output}")
    print(f"You can now run: python scripts/discover_job_sources.py --all --seed-file {args.output} --test --store")

if __name__ == "__main__":
    main()
