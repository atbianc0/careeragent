from __future__ import annotations

from urllib.parse import urlparse

from .common import html_text, infer_company_from_url, make_candidate, safe_get

MANUAL_WARNING = "CareerAgent does not automatically scrape LinkedIn/Indeed. Paste job descriptions manually for best results."


def discover_manual_links(urls: list[str]) -> list[dict]:
    candidates: list[dict] = []
    for url in urls:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        source_type = "linkedin_manual" if "linkedin." in hostname else "indeed_manual" if "indeed." in hostname else "manual_link"
        title = "Manual job link"
        description = MANUAL_WARNING if source_type in {"linkedin_manual", "indeed_manual"} else "Manual job link saved for review."
        try:
            if source_type not in {"linkedin_manual", "indeed_manual"}:
                response = safe_get(url)
                text = html_text(response.text)
                description = text[:2000] or description
        except Exception:
            pass
        candidates.append(
            make_candidate(
                source_type=source_type,
                source_name=hostname,
                company=infer_company_from_url(url),
                title=title,
                location="Unknown",
                url=url,
                description=description,
                raw_data={"source": source_type, "warnings": [MANUAL_WARNING] if source_type in {"linkedin_manual", "indeed_manual"} else []},
            )
        )
    return candidates

