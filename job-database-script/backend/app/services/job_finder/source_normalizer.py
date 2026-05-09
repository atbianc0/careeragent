import re
from urllib.parse import urlparse

def detect_ats_source_type(url: str) -> str:
    """
    Detects the ATS source type from a URL.
    """
    domain = urlparse(url).netloc.lower()
    
    if "jobs.lever.co" in domain:
        return "lever"
    elif "boards.greenhouse.io" in domain or "job-boards.greenhouse.io" in domain:
        return "greenhouse"
    elif "jobs.ashbyhq.com" in domain:
        return "ashby"
    elif "myworkdayjobs.com" in domain or "workdayjobs.com" in domain:
        return "workday"
    return "unknown"

def extract_company_name(url: str, ats_type: str) -> str | None:
    """
    Extracts the company name/slug from the URL based on ATS type.
    """
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    domain = parsed.netloc.lower()

    if ats_type == "lever":
        if path_parts:
            return path_parts[0]
        return None
    elif ats_type == "greenhouse":
        if path_parts:
            return path_parts[0]
        return None
    elif ats_type == "ashby":
        if path_parts:
            return path_parts[0]
        return None
    elif ats_type == "workday":
        if path_parts:
            # Example: https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite
            return path_parts[0]
        # Alternatively, get company from subdomain if present?
        # e.g., nvidia.wd5...
        subdomain_parts = domain.split('.')
        if len(subdomain_parts) > 2:
            return subdomain_parts[0]
        return None
    return None

def normalize_ats_board_url(url: str) -> dict:
    """
    Normalizes a job posting URL to its base company board URL.
    Returns:
        {
            "ats_type": "lever",
            "base_url": "https://jobs.lever.co/zoox",
            "company": "zoox"
        }
    """
    ats_type = detect_ats_source_type(url)
    
    if ats_type == "unknown":
        return {
            "ats_type": "unknown",
            "base_url": url,
            "company": None
        }

    company = extract_company_name(url, ats_type)
    if not company:
        # Fallback if we couldn't parse company
        return {
            "ats_type": ats_type,
            "base_url": url,
            "company": None
        }

    parsed = urlparse(url)
    scheme = parsed.scheme if parsed.scheme else "https"
    domain = parsed.netloc

    # Reconstruct the base URL
    if ats_type == "lever":
        base_url = f"{scheme}://{domain}/{company}"
    elif ats_type == "greenhouse":
        base_url = f"{scheme}://{domain}/{company}"
    elif ats_type == "ashby":
        base_url = f"{scheme}://{domain}/{company}"
    elif ats_type == "workday":
        base_url = f"{scheme}://{domain}/{company}"
    else:
        base_url = url

    return {
        "ats_type": ats_type,
        "base_url": base_url,
        "company": company
    }
