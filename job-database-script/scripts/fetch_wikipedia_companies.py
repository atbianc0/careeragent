import os
import requests
from bs4 import BeautifulSoup
import argparse

def fetch_sp500() -> list[str]:
    """Fetches the S&P 500 company names from Wikipedia."""
    print("Fetching S&P 500 companies...")
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    companies = set()
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find('table', {'id': 'constituents'})
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if cols:
                name = cols[1].text.strip()
                companies.add(name)
    except Exception as e:
        print(f"Error fetching S&P 500: {e}")
    return list(companies)

def fetch_unicorns() -> list[str]:
    """Fetches the list of Unicorn startup companies from Wikipedia."""
    print("Fetching Unicorn startups...")
    url = "https://en.wikipedia.org/wiki/List_of_unicorn_startup_companies"
    companies = set()
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        # There are multiple tables for unicorns (by region, etc.)
        tables = soup.find_all('table', {'class': 'wikitable'})
        for table in tables:
            for row in table.find_all('tr')[1:]:
                # Usually the company name is in the first or second column
                cols = row.find_all('td')
                if cols:
                    name = cols[0].text.strip()
                    # Some tables might have rank first
                    if name.isdigit() and len(cols) > 1:
                        name = cols[1].text.strip()
                    companies.add(name)
    except Exception as e:
        print(f"Error fetching Unicorns: {e}")
    return list(companies)

def main():
    parser = argparse.ArgumentParser(description="Fetch major company lists from Wikipedia.")
    parser.add_argument("--output", type=str, default="data/company_names.txt", help="Path to append company names.")
    args = parser.parse_args()

    all_companies = set()
    
    sp500 = fetch_sp500()
    print(f"Found {len(sp500)} S&P 500 companies.")
    all_companies.update(sp500)
    
    unicorns = fetch_unicorns()
    print(f"Found {len(unicorns)} Unicorn startups.")
    all_companies.update(unicorns)

    # Basic cleanup
    cleaned_companies = set()
    for name in all_companies:
        # Remove citation brackets like [1]
        import re
        name = re.sub(r'\[\d+\]', '', name)
        name = name.strip()
        if len(name) > 1:
            cleaned_companies.add(name)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "a", encoding="utf-8") as f:
        for c in cleaned_companies:
            f.write(c + "\n")

    print(f"\nSuccessfully appended {len(cleaned_companies)} company names to {args.output}.")
    print(f"You can now run: python scripts/generate_from_company_names.py --input {args.output}")

if __name__ == "__main__":
    main()
