# CareerAgent Job Database Source Discovery

CareerAgent cannot search every company on Lever/Greenhouse globally unless it knows the company board URLs. This source discovery system builds that database. It finds and stores company job board links for each ATS/source type, so the CareerAgent app can use these saved boards for later searching.

## Features

- Scans and normalizes URLs from various sources (seed files, pasted results, career pages).
- Normalizes links automatically to their base ATS boards (Lever, Greenhouse, Ashby, Workday).
- Preserves exact Lever casing for fetches but uses normalized lowercased URLs for deduplication.
- Tests if boards are valid by hitting public endpoints.
- Avoids automatic scraping of Google, LinkedIn, and Indeed.
- No API keys required.

## Quick Start: Precision Targeting 1k+ Startups and Big Tech Boards

The absolute most reliable way to find **thousands of valid startup boards** and the **exact custom career pages of Big Tech companies** is to use our DuckDuckGo (DDG) scrapers. DDG allows programmatic HTML scraping without CAPTCHAs, returning direct links to working boards instead of guessing slugs.

### Objective 1: Get 1,000+ Valid Startups
Run the DDG Mass Scraper. This programmatically searches DuckDuckGo across 30+ keywords for Lever, Greenhouse, and Ashby sites. Every link it finds is guaranteed to be a real, indexed board.
```bash
# 1. Mass scrape DuckDuckGo for startup boards
python scripts/scrape_ddg_startups.py

# 2. Process, test, and store the valid ones! (Skips any already in your DB)
python scripts/discover_job_sources.py --all --seed-file data/source_seeds/ats_sources_seed.txt --test --store --skip-existing --export-json outputs/source_discovery/job_sources.json --export-csv outputs/source_discovery/job_sources.csv
```

### Objective 2: Get All Big Tech Career Pages
Big tech companies often use custom URLs (e.g., `careers.google.com`) or Workday. First, ensure you have the massive list of companies (S&P 500 + Unicorns), then run the Precision Finder to extract their top DDG career page result.
```bash
# 1. Fetch 1,400+ massive companies (if you haven't already)
python scripts/fetch_wikipedia_companies.py

# 2. Find their exact career pages (limit set to 500 for demo, remove limit to do all 1400)
python scripts/find_big_tech_boards.py --limit 500

# 3. Process and extract any nested ATS links from those career pages!
python scripts/discover_job_sources.py --all --career-pages-file data/source_seeds/company_career_pages.txt --test --store --skip-existing --export-json outputs/source_discovery/job_sources.json --export-csv outputs/source_discovery/job_sources.csv
```
You will now have a massively populated `outputs/source_discovery/job_sources.csv` ready for CareerAgent, featuring thousands of working startup links and real Big Tech boards!

---

## Building the ATS Source Database

The discovery script accepts several methods to gather sources:

### 1. Seed Files

You can provide a seed file containing raw text or JSON lists of job URLs. 
File: `data/source_seeds/ats_sources_seed.txt`

Add lines like:
```text
https://jobs.lever.co/zoox
https://boards.greenhouse.io/databricks
```

### 2. Pasted Google Results

Since we do not scrape Google automatically, you can use the Google Query Helper to generate search strings, run them manually in your browser, and paste the result links into:
`data/source_seeds/pasted_search_results.txt`

To generate queries:
```bash
python scripts/generate_google_queries.py
```

### 3. Company Career Pages

You can supply a list of main company domains/career pages in `data/source_seeds/company_career_pages.txt`. The script will fetch the page and search for ATS links.

### 4. Search API (Programmatic Google Search)

If you have a SerpApi key, you can automatically run Google searches:
1. Create a `.env` file containing:
   ```env
   SEARCH_PROVIDER=serpapi
   SEARCH_API_KEY=your_key_here
   SEARCH_MAX_RESULTS=50
   ```
2. The script will automatically pull from the API when you run `discover_job_sources.py`.

### 5. Automated Scaling Methods (Getting 500+ Links Fast)

To get hundreds of valid boards immediately without an API key, use these two helper scripts:

**Method A: Mine Public GitHub Repositories**
We scan well-known public repositories (like "Hiring Without Whiteboards") for direct links to Lever, Greenhouse, and Ashby boards:
```bash
python scripts/mine_github_repos.py
```
This automatically appends hundreds of links to your seed file.

**Method B: Massive Company Dataset (S&P 500 + Unicorns)**
If you want to immediately target all big tech companies and funded startups, you can use the Wikipedia fetcher which downloads their names, and then use the Precision ATS Finder to search DuckDuckGo for their exact Lever/Greenhouse/Ashby link:
```bash
python scripts/fetch_wikipedia_companies.py
python scripts/generate_from_company_names.py --input data/company_names.txt --limit 500
```
This searches for each company rather than guessing, guaranteeing that the ATS links appended to your seed file are real and actively indexed!

**Method C: Direct Google Scraper**
If you want to directly scrape Google search results for ATS links without an API, you can use the built-in direct Google scraper. Note: This relies on simple HTTP requests and may occasionally be rate-limited by Google (429 Too Many Requests).
```bash
python scripts/scrape_google_for_ats.py --pages 3
```
This will run standard searches and append any discovered job boards directly to your seed file.

---

## How to Run the Script

Run the discovery script to collect, test, and export your job sources.

### Process all sources from a seed file, test them, and save to database
```bash
python scripts/discover_job_sources.py --all --seed-file data/source_seeds/ats_sources_seed.txt --store --test
```

*(Note: Depending on how you run it, you could also use `python discover_job_sources.py ...` if you run it from within the `scripts/` directory).*

### Process only Lever sources from pasted search results and export to JSON/CSV
```bash
python scripts/discover_job_sources.py --source lever --pasted-results-file data/source_seeds/pasted_search_results.txt --export-json outputs/source_discovery/job_sources.json --export-csv outputs/source_discovery/job_sources.csv
```

### Process career pages (dry run, do not store to DB)
```bash
python scripts/discover_job_sources.py --all --career-pages-file data/source_seeds/company_career_pages.txt --dry-run
```

## Options Reference

- `--all`: Process all ATS types.
- `--source <ats>`: Process only specific ATS type(s) (lever, greenhouse, ashby, workday, unknown).
- `--seed-file <path>`: Input file containing URLs.
- `--pasted-results-file <path>`: Input file containing pasted text/URLs.
- `--career-pages-file <path>`: Input file containing company URLs to scan.
- `--limit <int>`: Max number of raw URLs to process.
- `--test`: Send requests to check if the board is valid and has jobs.
- `--store`: Store valid results into the local database.
- `--export-json <path>`: Export results to a JSON file.
- `--export-csv <path>`: Export results to a CSV file.
- `--dry-run`: Skip writing to the database.
- `--skip-existing`: Skips testing sources that are already present in the local database. Perfect for iteratively adding more sources without redundant API hits.
- `--keep-invalid`: Store sources to DB even if they test as invalid.

## Outputs

When exporting, the script produces:
- **JSON**: e.g., `outputs/source_discovery/job_sources.json` containing the normalized structures.
- **CSV**: e.g., `outputs/source_discovery/job_sources.csv` containing flat columns for easier spreadsheet viewing.
- **Database**: Records are inserted into the `job_sources` table using the `JobSource` SQLAlchemy model.

## Search Saved Sources in App

Once you've built the source database, CareerAgent can use it for automated job hunting:
1. Load `JobSource` records from the database where `enabled=True`.
2. Present buttons in the UI for users to "Search Lever Sources", "Search Greenhouse Sources", etc.
3. Upon clicking, the backend pulls the valid URLs and runs its standard job extraction logic against those known boards.

## Limitations

- **Lever Slugs**: Lever slugs can be case-sensitive. The normalizer detects and preserves the casing while still deduping properly via lowercased `normalized_url`.
- **Workday**: Workday testing is limited because it often requires JS execution and does not always expose public API endpoints simply. The script will label these as valid/partial.
- **LinkedIn/Indeed**: Cannot be automated through this script; they remain manual only.
- **Anti-Bot Defenses**: The script uses a standard User-Agent, but heavily protected boards (Cloudflare, etc.) may still block the `test` phase. It will mark these as `blocked` or `invalid`.
