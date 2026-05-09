import os
import requests
import re
import argparse
import time

def extract_urls_from_text(text: str) -> list[str]:
    URL_REGEX = re.compile(r'https?://(?:jobs\.lever\.co|boards\.greenhouse\.io|jobs\.ashbyhq\.com|[^"\'\s]+\.myworkdayjobs\.com)[^\s<>"\']*')
    return URL_REGEX.findall(text)

def get_latest_who_is_hiring_threads() -> list[int]:
    """Fetches recent 'Who is hiring' thread IDs submitted by 'whoishiring' on HN."""
    print("Fetching recent 'Who is hiring' threads from HackerNews...")
    try:
        user_res = requests.get("https://hacker-news.firebaseio.com/v0/user/whoishiring.json", timeout=15)
        if user_res.status_code == 200:
            submissions = user_res.json().get("submitted", [])
            # Only test the last 20 submissions to find recent "Ask HN: Who is hiring?"
            threads = []
            for item_id in submissions[:20]:
                item_res = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json", timeout=10)
                if item_res.status_code == 200:
                    item = item_res.json()
                    if item and "Ask HN: Who is hiring?" in item.get("title", ""):
                        threads.append(item_id)
                        if len(threads) >= 3: # Let's just process the last 3 months
                            break
            return threads
    except Exception as e:
        print(f"Error fetching HN threads: {e}")
    return []

def mine_hn_thread(thread_id: int) -> list[str]:
    print(f"Mining HN thread {thread_id}...")
    urls = set()
    try:
        item_res = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{thread_id}.json", timeout=15)
        if item_res.status_code == 200:
            item = item_res.json()
            kids = item.get("kids", [])
            print(f"Found {len(kids)} top-level comments to parse.")
            
            # For each top level comment, extract ATS URLs
            for i, kid_id in enumerate(kids):
                if i % 100 == 0 and i > 0:
                    print(f"  Processed {i}/{len(kids)} comments...")
                
                try:
                    comment_res = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{kid_id}.json", timeout=10)
                    if comment_res.status_code == 200:
                        comment = comment_res.json()
                        text = comment.get("text", "")
                        if text:
                            found = extract_urls_from_text(text)
                            urls.update(found)
                except Exception:
                    pass
                # HN API has no auth key, but let's not overwhelm it
                time.sleep(0.01)
    except Exception as e:
        print(f"Error mining HN thread {thread_id}: {e}")
        
    return list(urls)

def main():
    parser = argparse.ArgumentParser(description="Mine HackerNews 'Who is hiring' threads for ATS links.")
    parser.add_argument("--output", type=str, default="data/source_seeds/ats_sources_seed.txt", help="Path to append found links.")
    args = parser.parse_args()

    threads = get_latest_who_is_hiring_threads()
    if not threads:
        print("No HN threads found.")
        return

    all_urls = set()
    for t in threads:
        found = mine_hn_thread(t)
        print(f"Found {len(found)} ATS links in thread {t}")
        all_urls.update(found)

    if all_urls:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "a", encoding="utf-8") as f:
            for url in all_urls:
                f.write(url + "\n")
        print(f"\nTotal unique ATS links mined from HackerNews: {len(all_urls)}")
        print(f"Appended to {args.output}")
        print(f"You can now run: python scripts/discover_job_sources.py --all --seed-file {args.output} --test --store --skip-existing")

if __name__ == "__main__":
    main()
