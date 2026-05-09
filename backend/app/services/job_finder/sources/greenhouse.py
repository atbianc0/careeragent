from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .common import html_text, make_candidate, query_matches, safe_get


def _greenhouse_board_token(company_or_url: str) -> str:
    value = (company_or_url or "").strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.netloc:
        parts = [part for part in parsed.path.split("/") if part]
        if parsed.netloc.endswith("greenhouse.io") and parts:
            if parts[0] == "embed" and len(parts) > 1:
                return parts[1]
            return parts[0]
        return parts[0] if parts else parsed.netloc.split(".")[0]
    return value


def _html_fallback(url: str, query: str, location: str) -> list[dict]:
    response = safe_get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    text = html_text(response.text)
    title = soup.find(["h1", "title"])
    candidate = make_candidate(
        source_type="greenhouse",
        source_name=_greenhouse_board_token(url),
        company=_greenhouse_board_token(url).replace("-", " ").title(),
        title=title.get_text(" ", strip=True) if title else "Unknown Title",
        location="Unknown",
        url=url,
        description=text,
        raw_data={"source": "greenhouse_html_fallback"},
    )
    return [candidate] if query_matches(candidate, query, location) else []


def discover_greenhouse_jobs(company_or_url: str, query: str = "", location: str = "Bay Area") -> list[dict]:
    token = _greenhouse_board_token(company_or_url)
    if not token:
        return []
    if re.search(r"/jobs?/\d+", company_or_url):
        return _html_fallback(company_or_url, query, location)

    api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    try:
        payload = safe_get(api_url, respect_robots=False).json()
    except Exception:
        return _html_fallback(company_or_url, query, location) if urlparse(company_or_url).netloc else []

    candidates = []
    for job in payload.get("jobs", []) if isinstance(payload, dict) else []:
        offices = job.get("offices") or []
        location_obj = job.get("location") if isinstance(job.get("location"), dict) else {}
        location_text = (
            location_obj.get("name")
            or ", ".join(office.get("name", "") for office in offices if isinstance(office, dict))
            or ""
        )
        content = job.get("content") or job.get("absolute_url") or ""
        candidate = make_candidate(
            source_type="greenhouse",
            source_name=token,
            company=token.replace("-", " ").title(),
            title=job.get("title"),
            location=location_text,
            url=job.get("absolute_url") or "",
            description=html_text(content),
            raw_data=job,
        )
        if candidate["url"] and query_matches(candidate, query, location):
            candidates.append(candidate)
    return candidates
