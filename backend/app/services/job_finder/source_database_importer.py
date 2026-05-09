from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.job_finder import JobSource
from app.services.job_finder.dedupe import normalize_url
from app.services.job_finder.sources.common import infer_company_from_url

DEFAULT_SOURCE_CSV_PATH = "job-database-script/outputs/source_discovery/job_sources.csv"
DEFAULT_SOURCE_JSON_PATH = "job-database-script/outputs/source_discovery/job_sources.json"
VALID_ENABLED_STATUSES = {"", "valid", "partial", "working", "ok"}
DISABLED_STATUSES = {"invalid", "blocked", "error", "failed", "closed"}
BLOCKED_HOST_PARTS = ("linkedin.", "indeed.", "google.")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _list_warnings(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
        return [value.strip()] if value.strip() else []
    return [str(value).strip()]


def _infer_ats_type(value: str, url: str) -> str:
    raw = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "company": "company_careers",
        "company_career": "company_careers",
        "career_page": "company_careers",
        "career_pages": "company_careers",
        "custom": "company_careers",
        "unknown": "company_careers",
    }
    if raw in aliases:
        return aliases[raw]
    if raw in {"lever", "greenhouse", "ashby", "workday", "company_careers"}:
        return raw

    host = (urlparse(url).hostname or "").lower()
    if "lever.co" in host:
        return "lever"
    if "greenhouse.io" in host:
        return "greenhouse"
    if "ashbyhq.com" in host:
        return "ashby"
    if "myworkdayjobs.com" in host or "workdayjobs.com" in host:
        return "workday"
    return "company_careers"


def _is_allowed_public_source_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    host = (parsed.hostname or "").lower()
    return not any(part in host for part in BLOCKED_HOST_PARTS)


def load_sources_from_csv(path: str) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_sources_from_json(path: str) -> list[dict]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return [dict(item) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("sources"), list):
        return [dict(item) for item in payload["sources"] if isinstance(item, dict)]
    return []


def normalize_source_record(record: dict) -> dict:
    base_url = _clean(
        record.get("base_url")
        or record.get("url")
        or record.get("source_url")
        or record.get("career_url")
        or record.get("normalized_url")
    )
    if not base_url or not _is_allowed_public_source_url(base_url):
        return {"valid": False, "invalid_reason": "Missing, invalid, or disallowed source URL.", "raw_record": record}

    normalized = _clean(record.get("normalized_url")) or normalize_url(base_url)
    ats_type = _infer_ats_type(_clean(record.get("ats_type") or record.get("source_type")), base_url)
    status = _clean(record.get("status")).lower()
    company = _clean(record.get("company") or record.get("name")) or infer_company_from_url(base_url)
    last_error = _clean(record.get("last_error") or record.get("error"))
    enabled = status in VALID_ENABLED_STATUSES or status not in DISABLED_STATUSES

    return {
        "valid": True,
        "name": company,
        "company": company,
        "source_type": ats_type,
        "ats_type": ats_type,
        "base_url": base_url,
        "normalized_url": normalized,
        "enabled": enabled,
        "status": status or None,
        "jobs_found": _int_or_none(record.get("jobs_found") or record.get("job_count")),
        "last_error": last_error or None,
        "discovery_method": _clean(record.get("discovery_method") or record.get("method")) or None,
        "warnings": _list_warnings(record.get("warnings")),
        "raw_record": record,
    }


def _empty_summary(total_read: int) -> dict[str, Any]:
    return {
        "total_read": total_read,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "invalid": 0,
        "deleted": 0,
        "by_ats_type": {},
    }


def _count_ats(summary: dict[str, Any], ats_type: str) -> None:
    by_ats_type = summary.setdefault("by_ats_type", {})
    by_ats_type[ats_type] = int(by_ats_type.get(ats_type, 0)) + 1


def import_sources_to_db(records: list[dict], db: Session, skip_existing: bool = True, replace_existing: bool = False) -> dict:
    summary = _empty_summary(len(records))
    now = _now()
    seen_urls: set[str] = set()

    for record in records:
        normalized = normalize_source_record(record)
        if not normalized.get("valid"):
            summary["invalid"] += 1
            continue

        normalized_url = str(normalized["normalized_url"])
        if normalized_url in seen_urls:
            summary["skipped"] += 1
            continue
        seen_urls.add(normalized_url)
        _count_ats(summary, str(normalized["ats_type"]))

        existing = (
            db.query(JobSource)
            .filter(or_(JobSource.normalized_url == normalized_url, JobSource.base_url == normalized["base_url"]))
            .first()
        )
        enabled = bool(normalized["enabled"])
        if existing:
            existing.name = normalized["name"] if not skip_existing else existing.name or normalized["name"]
            existing.source_type = str(normalized["source_type"])
            existing.ats_type = str(normalized["ats_type"])
            existing.base_url = str(normalized["base_url"]) if not skip_existing else existing.base_url or str(normalized["base_url"])
            existing.normalized_url = normalized_url
            existing.status = normalized["status"]
            existing.jobs_found = normalized["jobs_found"]
            existing.last_error = normalized["last_error"]
            existing.discovery_method = normalized["discovery_method"]
            existing.warnings = normalized["warnings"]
            existing.imported_at = now
            if enabled or existing.enabled is None:
                existing.enabled = enabled
            elif not existing.enabled:
                existing.enabled = False
            summary["updated"] += 1
            continue

        db.add(
            JobSource(
                name=str(normalized["name"]),
                source_type=str(normalized["source_type"]),
                ats_type=str(normalized["ats_type"]),
                base_url=str(normalized["base_url"]),
                normalized_url=normalized_url,
                enabled=enabled,
                status=normalized["status"],
                jobs_found=normalized["jobs_found"],
                last_error=normalized["last_error"],
                discovery_method=normalized["discovery_method"],
                warnings=normalized["warnings"],
                imported_at=now,
            )
        )
        summary["created"] += 1

    if replace_existing and seen_urls:
        missing_sources = db.query(JobSource).filter(~JobSource.normalized_url.in_(seen_urls)).all()
        for source in missing_sources:
            db.delete(source)
        summary["deleted"] = len(missing_sources)

    db.commit()
    return summary
