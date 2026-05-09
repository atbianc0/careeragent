from __future__ import annotations

import time
from html import unescape
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from app.utils.text import normalize_whitespace

USER_AGENT = "CareerAgent/0.12 Job Finder (safe source discovery; contact: local-user)"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"}
TIMEOUT_SECONDS = 10
RATE_LIMIT_SECONDS = 0.25
MAX_DESCRIPTION_CHARS = 80_000


def clean_text(value: str | None) -> str:
    return normalize_whitespace(unescape(value or "").replace("\xa0", " "))


def safe_get(url: str, *, timeout: int = TIMEOUT_SECONDS, respect_robots: bool = True) -> requests.Response:
    if respect_robots and not robots_allowed(url):
        raise ValueError(f"robots.txt does not allow fetching {url}")
    time.sleep(RATE_LIMIT_SECONDS)
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    return response


def robots_allowed(url: str) -> bool:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    try:
        response = requests.get(robots_url, headers=HEADERS, timeout=3)
        if response.status_code >= 400:
            return True
        parser.parse(response.text.splitlines())
    except Exception:
        return True
    return parser.can_fetch(USER_AGENT, url)


def html_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return "\n".join(line for line in (clean_text(part) for part in soup.get_text("\n", strip=True).splitlines()) if line)


def soup_for(url: str) -> BeautifulSoup:
    return BeautifulSoup(safe_get(url).text, "html.parser")


def absolute_url(base_url: str, href: str | None) -> str:
    return urljoin(base_url, href or "")


def query_matches(candidate: dict, query: str | None, location: str | None = None) -> bool:
    text = " ".join(
        [
            str(candidate.get("title") or ""),
            str(candidate.get("location") or ""),
            str(candidate.get("description_snippet") or ""),
            str(candidate.get("job_description") or ""),
        ]
    ).lower()
    query_terms = [term for term in clean_text(query).lower().split() if len(term) > 2]
    role_hit = not query_terms or any(term in text for term in query_terms)
    location_text = clean_text(location).lower()
    location_hit = not location_text or location_text == "bay area" or location_text in text or "remote" in text
    return role_hit and location_hit


def infer_company_from_url(url: str) -> str:
    hostname = (urlparse(url).hostname or "").lower()
    for suffix in ["boards.greenhouse.io", "jobs.lever.co", "jobs.ashbyhq.com", "ashbyhq.com", "myworkdayjobs.com", "workdayjobs.com"]:
        hostname = hostname.replace(suffix, "")
    parts = [part for part in hostname.split(".") if part and part not in {"www", "jobs", "careers"}]
    if parts:
        return parts[0].replace("-", " ").title()
    return "Unknown Company"


def make_candidate(
    *,
    source_type: str,
    source_name: str | None,
    company: str | None,
    title: str | None,
    location: str | None,
    url: str,
    description: str | None = None,
    raw_data: dict | None = None,
) -> dict:
    description_text = clean_text(description)[:MAX_DESCRIPTION_CHARS]
    return {
        "source_type": source_type,
        "source_name": source_name,
        "company": clean_text(company) or infer_company_from_url(url),
        "title": clean_text(title),
        "location": clean_text(location),
        "url": url,
        "description_snippet": description_text[:500],
        "job_description": description_text,
        "raw_data": raw_data or {},
    }
