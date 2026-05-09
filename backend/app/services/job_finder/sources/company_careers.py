from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .ashby import discover_ashby_jobs
from .common import absolute_url, clean_text, infer_company_from_url, make_candidate, query_matches, safe_get
from .greenhouse import discover_greenhouse_jobs
from .lever import discover_lever_jobs
from .workday import discover_workday_jobs

ATS_HINTS = ("greenhouse.io", "lever.co", "ashbyhq.com", "myworkdayjobs.com", "workdayjobs.com")
JOB_LINK_HINTS = ("job", "career", "position", "opening", "apply")
MAX_LINKS = 20


def _dispatch_ats_link(url: str, query: str, location: str) -> list[dict]:
    hostname = (urlparse(url).hostname or "").lower()
    if "lever.co" in hostname:
        return discover_lever_jobs(url, query, location)
    if "greenhouse.io" in hostname:
        return discover_greenhouse_jobs(url, query, location)
    if "ashbyhq.com" in hostname:
        return discover_ashby_jobs(url, query, location)
    if "myworkdayjobs.com" in hostname or "workdayjobs.com" in hostname:
        return discover_workday_jobs(url, query, location)
    return []


def discover_company_careers_jobs(url: str, query: str = "", location: str = "Bay Area") -> list[dict]:
    response = safe_get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    seen: set[str] = set()
    candidates: list[dict] = []
    links: list[tuple[str, str]] = []

    for link in soup.find_all("a", href=True):
        href = absolute_url(url, link.get("href"))
        if href in seen:
            continue
        seen.add(href)
        label = clean_text(link.get_text(" ", strip=True))
        lowered = f"{href} {label}".lower()
        if any(hint in lowered for hint in ATS_HINTS + JOB_LINK_HINTS):
            links.append((href, label))
        if len(links) >= MAX_LINKS:
            break

    for href, label in links:
        hostname = (urlparse(href).hostname or "").lower()
        if any(hint in hostname for hint in ATS_HINTS):
            try:
                candidates.extend(_dispatch_ats_link(href, query, location))
                continue
            except Exception as exc:
                candidates.append(
                    make_candidate(
                        source_type="company_careers",
                        source_name=infer_company_from_url(url),
                        company=infer_company_from_url(url),
                        title=label or "ATS job link",
                        location="Unknown",
                        url=href,
                        description=f"ATS link discovered but detailed source fetch failed: {exc}",
                        raw_data={"source": "company_careers_ats_link", "error": str(exc)},
                    )
                )
                continue

        candidate = make_candidate(
            source_type="company_careers",
            source_name=infer_company_from_url(url),
            company=infer_company_from_url(url),
            title=label or "Company career link",
            location="Unknown",
            url=href,
            description="Job-like link found on a company careers page.",
            raw_data={"source": "company_careers_link"},
        )
        if query_matches(candidate, query, location):
            candidates.append(candidate)

    return candidates[:MAX_LINKS]

