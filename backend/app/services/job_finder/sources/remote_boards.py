from __future__ import annotations

from .company_careers import discover_company_careers_jobs


def discover_remote_board_jobs(url: str, query: str = "", location: str = "Bay Area") -> list[dict]:
    candidates = discover_company_careers_jobs(url, query, location)
    for candidate in candidates:
        candidate["source_type"] = "remote_board"
        candidate["raw_data"] = {**dict(candidate.get("raw_data") or {}), "source": "remote_board_url"}
    return candidates

