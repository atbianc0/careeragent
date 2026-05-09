from __future__ import annotations

from urllib.parse import urlparse

from app.services.jobs.parser import extract_workday_metadata_from_url, is_workday_url, try_workday_api_fetch

from .common import make_candidate, query_matches


def discover_workday_jobs(company_or_url: str, query: str = "", location: str = "Bay Area") -> list[dict]:
    url = (company_or_url or "").strip()
    if not url or not is_workday_url(url):
        return []
    parsed = urlparse(url)
    metadata = extract_workday_metadata_from_url(url) if "/job/" in parsed.path else {}
    if not metadata:
        return []

    api_metadata = try_workday_api_fetch(url)
    title = api_metadata.get("title") or metadata.get("title")
    location_text = api_metadata.get("location") or metadata.get("location")
    description = api_metadata.get("job_description") or ""
    if str(title or "").lower().startswith("unknown"):
        title = ""
    if str(location_text or "").lower().startswith("unknown"):
        location_text = ""

    candidate = make_candidate(
        source_type="workday",
        source_name=str(metadata.get("tenant") or parsed.hostname or "workday"),
        company=api_metadata.get("company") or metadata.get("company"),
        title=title,
        location=location_text,
        url=url,
        description=description,
        raw_data={
            "source": "workday_url",
            **metadata,
            "workday_api": api_metadata,
            "warnings": list(api_metadata.get("warnings") or []) + list(metadata.get("warnings") or []),
        },
    )
    return [candidate] if query_matches(candidate, query, location) else []
