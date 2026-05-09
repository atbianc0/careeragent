import os
import re
import argparse

def get_company_slugs(name: str) -> list[str]:
    """
    Generates multiple slug permutations for a company name.
    E.g. "Data Hub Inc." -> ["datahub", "data-hub", "data_hub", "data%20hub", "data%10hub"]
    """
    # Remove common suffixes
    clean_name = re.sub(r'(?i)\b(inc|llc|corp|corporation|ltd|group)\b\.?', '', name).strip()
    
    slugs = set()
    
    # 1. No spaces, lowercase alphanumeric
    slug_alphanumeric = re.sub(r'[^a-zA-Z0-9]', '', clean_name).lower()
    if slug_alphanumeric:
        slugs.add(slug_alphanumeric)
        
    # 2. Hyphenated (replace spaces/punctuation with hyphens)
    slug_hyphenated = re.sub(r'[^a-zA-Z0-9]+', '-', clean_name).strip('-').lower()
    if slug_hyphenated:
        slugs.add(slug_hyphenated)
        
    # 3. Underscored
    slug_underscored = slug_hyphenated.replace('-', '_')
    if slug_underscored:
        slugs.add(slug_underscored)
        
    # 4. URL encoded spaces (%20)
    slug_percent20 = clean_name.lower().replace(' ', '%20')
    if slug_percent20:
        slugs.add(slug_percent20)
        
    # 5. User specific edge case (%10)
    slug_percent10 = clean_name.lower().replace(' ', '%10')
    if slug_percent10:
        slugs.add(slug_percent10)
        
    return list(slugs)

def generate_urls(company_name: str) -> list[str]:
    slugs = get_company_slugs(company_name)
    urls = []
    
    for slug in slugs:
        urls.extend([
            f"https://jobs.lever.co/{slug}",
            f"https://boards.greenhouse.io/{slug}",
            f"https://jobs.ashbyhq.com/{slug}"
        ])
    return urls

def main():
    parser = argparse.ArgumentParser(description="Generate ATS URLs from a list of company names.")
    parser.add_argument("--input", type=str, required=True, help="Path to input text file containing company names (one per line).")
    parser.add_argument("--output", type=str, default="data/source_seeds/ats_sources_seed.txt", help="Path to output seed file. Appends to existing.")
    parser.add_argument("--limit", type=int, default=10000, help="Max companies to process.")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found.")
        return

    generated = set()
    with open(args.input, "r", encoding="utf-8") as f:
        companies = [line.strip() for line in f if line.strip()][:args.limit]

    for name in companies:
        urls = generate_urls(name)
        generated.update(urls)

    # Append to seed file
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "a", encoding="utf-8") as f:
        for url in generated:
            f.write(url + "\n")
            
    print(f"Generated {len(generated)} URLs from {args.input} and appended to {args.output}.")
    print(f"You can now run: python scripts/discover_job_sources.py --all --seed-file {args.output} --test --store --skip-existing")

if __name__ == "__main__":
    main()
