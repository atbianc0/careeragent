from __future__ import annotations

from urllib.parse import urlparse

from .common import make_candidate, query_matches, safe_get


def _lever_company_slug(company_or_url: str) -> str:
    value = (company_or_url or "").strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.netloc:
        parts = [part for part in parsed.path.split("/") if part]
        if parsed.netloc.endswith("jobs.lever.co") and parts:
            return parts[0]
        return parts[0] if parts else parsed.netloc.split(".")[0]
    return value


def discover_lever_jobs(company_or_url: str, query: str = "", location: str = "Bay Area") -> list[dict]:
    slug = _lever_company_slug(company_or_url)
    if not slug:
        return []
    parsed = urlparse(company_or_url)
    if parsed.netloc.endswith("jobs.lever.co") and len([part for part in parsed.path.split("/") if part]) >= 2:
        parts = [part for part in parsed.path.split("/") if part]
        return [
            make_candidate(
                source_type="lever",
                source_name=parts[0],
                company=parts[0].replace("-", " ").title(),
                title=parts[-1].replace("-", " ").title(),
                location="Unknown",
                url=company_or_url,
                description="Direct Lever job link saved for review.",
                raw_data={"source": "direct_lever_url"},
            )
        ]

    api_url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    response = safe_get(api_url, respect_robots=False)
    postings = response.json()
    candidates = []
    for posting in postings if isinstance(postings, list) else []:
        categories = dict(posting.get("categories") or {})
        location_text = categories.get("location")
        if not location_text and isinstance(posting.get("workplaceType"), str):
            location_text = posting.get("workplaceType")
        candidate = make_candidate(
            source_type="lever",
            source_name=slug,
            company=slug.replace("-", " ").title(),
            title=posting.get("text"),
            location=location_text,
            url=posting.get("hostedUrl") or posting.get("applyUrl") or "",
            description=posting.get("descriptionPlain") or posting.get("description"),
            raw_data=posting,
        )
        if candidate["url"] and query_matches(candidate, query, location):
            candidates.append(candidate)
    return candidates
