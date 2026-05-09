from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .common import absolute_url, html_text, make_candidate, query_matches, safe_get


def _ashby_slug(company_or_url: str) -> str:
    value = (company_or_url or "").strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.netloc:
        parts = [part for part in parsed.path.split("/") if part]
        if parsed.netloc.endswith("ashbyhq.com") and parts:
            return parts[0]
        return parts[0] if parts else parsed.netloc.split(".")[0]
    return value


def _html_candidates(url: str, query: str, location: str) -> list[dict]:
    response = safe_get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    candidates = []
    for link in soup.find_all("a", href=True):
        href = absolute_url(url, link.get("href"))
        label = link.get_text(" ", strip=True)
        if "ashbyhq.com" not in href and "/job/" not in href.lower():
            continue
        candidate = make_candidate(
            source_type="ashby",
            source_name=_ashby_slug(url),
            company=_ashby_slug(url).replace("-", " ").title(),
            title=label or "Unknown Title",
            location="Unknown",
            url=href,
            description=label,
            raw_data={"source": "ashby_html_link"},
        )
        if query_matches(candidate, query, location):
            candidates.append(candidate)
    if not candidates and "/job/" in url:
        title = soup.find(["h1", "title"])
        candidate = make_candidate(
            source_type="ashby",
            source_name=_ashby_slug(url),
            company=_ashby_slug(url).replace("-", " ").title(),
            title=title.get_text(" ", strip=True) if title else "Unknown Title",
            location="Unknown",
            url=url,
            description=html_text(response.text),
            raw_data={"source": "ashby_job_html_fallback"},
        )
        if query_matches(candidate, query, location):
            candidates.append(candidate)
    return candidates


def discover_ashby_jobs(company_or_url: str, query: str = "", location: str = "Bay Area") -> list[dict]:
    slug = _ashby_slug(company_or_url)
    if not slug:
        return []
    api_url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
    try:
        payload = safe_get(api_url, respect_robots=False).json()
    except Exception:
        return _html_candidates(company_or_url, query, location) if urlparse(company_or_url).netloc else []

    candidates = []
    for job in payload.get("jobs", []) if isinstance(payload, dict) else []:
        location_text = (
            ", ".join(str(item) for item in job.get("locationNames") or [])
            or str(job.get("locationName") or "")
            or str((job.get("location") or {}).get("name") if isinstance(job.get("location"), dict) else "")
        )
        description = job.get("descriptionHtml") or job.get("descriptionPlain") or ""
        candidate = make_candidate(
            source_type="ashby",
            source_name=slug,
            company=slug.replace("-", " ").title(),
            title=job.get("title"),
            location=location_text,
            url=job.get("jobUrl") or f"https://jobs.ashbyhq.com/{slug}/{job.get('id')}",
            description=html_text(description),
            raw_data=job,
        )
        if candidate["url"] and query_matches(candidate, query, location):
            candidates.append(candidate)
    return candidates
