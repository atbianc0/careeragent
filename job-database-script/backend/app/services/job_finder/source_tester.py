import requests
from bs4 import BeautifulSoup
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def test_job_source(source: dict) -> dict:
    """
    Tests if a job source is valid by trying to fetch public jobs.
    source must have: ats_type, base_url, company
    """
    ats_type = source.get("ats_type")
    base_url = source.get("base_url")
    company = source.get("company")
    
    result = {
        "base_url": base_url,
        "ats_type": ats_type,
        "company": company,
        "status": "unsupported",
        "jobs_found": 0,
        "error": None,
        "warnings": []
    }

    if not base_url or not company:
        result["status"] = "invalid"
        result["error"] = "Missing base_url or company"
        return result

    try:
        max_retries = 3
        
        if ats_type == "lever":
            for attempt in range(max_retries):
                api_url = f"https://api.lever.co/v0/postings/{company}?mode=json"
                res = requests.get(api_url, headers=HEADERS, timeout=10)
                if res.status_code == 429:
                    time.sleep(2)
                    continue
                if res.status_code == 200:
                    data = res.json()
                    result["status"] = "valid"
                    result["jobs_found"] = len(data)
                else:
                    # Fallback to page fetch
                    res = requests.get(base_url, headers=HEADERS, timeout=10)
                    if res.status_code == 200 and company.lower() in res.text.lower():
                        result["status"] = "valid"
                        result["warnings"].append("Could not access API, validated via HTML page.")
                    elif res.status_code == 404:
                        result["status"] = "invalid"
                        result["error"] = "Board not found (404)"
                    else:
                        result["status"] = "blocked"
                break

        elif ats_type == "greenhouse":
            for attempt in range(max_retries):
                api_url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
                res = requests.get(api_url, headers=HEADERS, timeout=10)
                if res.status_code == 429:
                    time.sleep(2)
                    continue
                if res.status_code == 200:
                    data = res.json()
                    jobs = data.get("jobs", [])
                    result["status"] = "valid"
                    result["jobs_found"] = len(jobs)
                else:
                    # Fallback to page fetch
                    res = requests.get(base_url, headers=HEADERS, timeout=10)
                    if res.status_code == 200:
                        result["status"] = "valid"
                        result["warnings"].append("API failed, validated via HTML page.")
                    elif res.status_code == 404:
                        result["status"] = "invalid"
                        result["error"] = "Board not found (404)"
                    else:
                        result["status"] = "blocked"
                break

        elif ats_type == "ashby":
            graphql_url = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
            payload = {
                "operationName": "ApiJobBoardWithTeams",
                "variables": {
                    "organizationHostedJobsPageName": company
                },
                "query": "query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) { jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) { jobPostings { id } } }"
            }
            
            for attempt in range(max_retries):
                res = requests.post(graphql_url, json=payload, headers=HEADERS, timeout=10)
                
                if res.status_code == 429:
                    time.sleep(2)
                    continue
                    
                if res.status_code == 200:
                    try:
                        json_data = res.json()
                    except:
                        result["status"] = "invalid"
                        result["error"] = "Non-JSON response"
                        break
                        
                    # Ashby rate limits can return 200 OK with an error key
                    if "error" in json_data and "Rate limit exceeded" in str(json_data["error"]):
                        time.sleep(2)
                        continue
                        
                    data = json_data.get("data", {})
                    job_board = data.get("jobBoard")
                    
                    if job_board is None:
                        result["status"] = "invalid"
                        result["error"] = "Board not found (GraphQL returned null)"
                    else:
                        result["status"] = "valid"
                        postings = job_board.get("jobPostings", [])
                        result["jobs_found"] = len(postings)
                elif res.status_code == 404:
                    result["status"] = "invalid"
                    result["error"] = "Board not found (404)"
                else:
                    result["status"] = "blocked"
                break

        elif ats_type == "workday":
            for attempt in range(max_retries):
                res = requests.get(base_url, headers=HEADERS, timeout=10)
                if res.status_code == 429:
                    time.sleep(2)
                    continue
                result["status"] = "valid" if res.status_code == 200 else "partial"
                result["warnings"].append("Workday may require JS/API support and may not expose all jobs.")
                break
            
        else:
            # Unknown
            result["status"] = "unsupported"
            result["warnings"].append("Unknown ATS type, unable to test automatically.")
            
    except requests.exceptions.Timeout:
        result["status"] = "invalid"
        result["error"] = "Timeout fetching source"
    except Exception as e:
        result["status"] = "invalid"
        result["error"] = str(e)

    return result
