import argparse

def generate_queries():
    roles = [
        "Data Engineer", "Data Scientist", "Machine Learning Engineer", 
        "Analytics Engineer", "Data Analyst"
    ]
    
    locations = [
        "San Francisco", "Bay Area", "Palo Alto", "Santa Clara", "San Jose"
    ]
    
    roles_str = " OR ".join([f'"{r}"' for r in roles])
    locations_str = " OR ".join([f'"{l}"' for l in locations])

    queries = {
        "Lever": f'site:jobs.lever.co ({roles_str}) ({locations_str})',
        "Greenhouse": f'site:boards.greenhouse.io ({roles_str}) ({locations_str})',
        "Ashby": f'site:jobs.ashbyhq.com ("Data Engineer" OR "Data Scientist" OR "Machine Learning Engineer") ("New Grad" OR "Entry Level" OR "Early Career")',
        "Workday": f'site:myworkdayjobs.com ("Data Engineer" OR "Data Scientist" OR "Machine Learning Engineer") ("Santa Clara" OR "San Francisco" OR "Bay Area")'
    }

    print("=== Google Search Query Helper ===\n")
    print("Copy and paste these queries into Google, then paste the result URLs into data/source_seeds/pasted_search_results.txt\n")
    
    for ats, query in queries.items():
        print(f"--- {ats} ---")
        print(query)
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Google search strings for ATS Discovery")
    parser.parse_args()
    generate_queries()
