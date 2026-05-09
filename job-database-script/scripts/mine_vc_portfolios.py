import requests
import json
import os

def mine_yc_companies():
    """
    Paginates through the public Y Combinator API to extract active startup names.
    """
    print("Mining Y Combinator startup directory...")
    
    base_url = "https://api.ycombinator.com/v0.1/companies"
    page = 1
    companies_collected = []
    
    # We will use a session to reuse connections
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json"
    })
    
    while True:
        try:
            print(f"Fetching YC Page {page}...", end="\r")
            res = session.get(f"{base_url}?page={page}", timeout=10)
            
            if res.status_code != 200:
                print(f"\nFailed to fetch page {page}. Status: {res.status_code}")
                break
                
            data = res.json()
            companies = data.get("companies", [])
            
            if not companies:
                print(f"\nReached end of YC directory at page {page}.")
                break
                
            for c in companies:
                # Some companies might not have names, but it's rare
                name = c.get("name")
                if name:
                    companies_collected.append(name.strip())
            
            page += 1
            
        except Exception as e:
            print(f"\nError fetching YC directory on page {page}: {e}")
            break

    print(f"Successfully collected {len(companies_collected)} YC companies.")
    return list(set(companies_collected))

def main():
    os.makedirs("data", exist_ok=True)
    out_file = "data/startup_names.txt"
    
    all_startups = []
    
    # 1. Y Combinator
    yc_names = mine_yc_companies()
    all_startups.extend(yc_names)
    
    # Can add a16z, Sequoia, etc. here in the future
    
    # Deduplicate and sort
    final_names = sorted(list(set(all_startups)))
    
    with open(out_file, "w", encoding="utf-8") as f:
        for name in final_names:
            if name:
                f.write(f"{name}\n")
                
    print(f"Exported {len(final_names)} unique startup names to {out_file}")

if __name__ == "__main__":
    main()
