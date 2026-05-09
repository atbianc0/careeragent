#!/bin/bash

# Exit on any error
set -e

echo "🚀 Starting Full CareerAgent ATS Discovery Pipeline..."
echo "======================================================"

echo -e "\n[1/7] ⛏️  Mining public GitHub repositories (10+ Repositories)..."
python scripts/mine_github_repos.py

echo -e "\n[2/7] 🚀 Mining HackerNews 'Who is hiring' threads for thousands of startup links..."
python scripts/mine_hacker_news.py

echo -e "\n[3/7] 🚀 Mining Venture Capital Portfolios (Y Combinator) for startup names..."
python scripts/mine_vc_portfolios.py

echo -e "\n[4/7] 📚 Fetching massive company lists and generating ATS permutations..."
python scripts/fetch_wikipedia_companies.py
# Brute forcing permutations on ALL collected names
python scripts/generate_from_company_names.py --input data/company_names.txt
python scripts/generate_from_company_names.py --input data/startup_names.txt

echo -e "\n[5/7] 🏢 Precision searching (Unblockable) for Big Tech custom career pages..."
python scripts/find_big_tech_boards.py --limit 1500

echo -e "\n[6/7] 🚀 Mass scraping (Unblockable) for valid Startup ATS boards..."
python scripts/scrape_ddg_startups.py

echo -e "\n[7/7] 💾 Processing, Testing, Deduplicating, and Exporting all links..."
# This runs the main pipeline on ALL generated sources, skips what's already in the DB, and exports only valid ones.
python scripts/discover_job_sources.py \
    --all \
    --seed-file data/source_seeds/ats_sources_seed.txt \
    --career-pages-file data/source_seeds/company_career_pages.txt \
    --test \
    --store \
    --skip-existing \
    --limit 100000 \
    --export-json outputs/source_discovery/job_sources.json \
    --export-csv outputs/source_discovery/job_sources.csv

echo "======================================================"
echo "✅ Pipeline Complete!"
echo "Your final, 100% valid database is available at: outputs/source_discovery/job_sources.csv"
