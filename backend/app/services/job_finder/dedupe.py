from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.job_finder import JobCandidate


def normalize_url(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=False)
            if not key.lower().startswith(("utm_", "gh_src"))
        ]
    )
    path = re.sub(r"/+$", "", parsed.path)
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", query, ""))


def duplicate_key_for_candidate(candidate: dict) -> str:
    url_key = normalize_url(str(candidate.get("url") or ""))
    if url_key:
        return f"url:{url_key}"
    company = re.sub(r"[^a-z0-9]+", " ", str(candidate.get("company") or "").lower()).strip()
    title = re.sub(r"[^a-z0-9]+", " ", str(candidate.get("title") or "").lower()).strip()
    location = re.sub(r"[^a-z0-9]+", " ", str(candidate.get("location") or "").lower()).strip()
    return f"job:{company}|{title}|{location}"


def find_duplicate_job(db: Session, candidate: dict, duplicate_key: str) -> Job | None:
    url = normalize_url(str(candidate.get("url") or ""))
    if url:
        jobs = db.query(Job).filter(Job.url.isnot(None), Job.url != "").all()
        for job in jobs:
            if normalize_url(job.url) == url:
                return job

    company = str(candidate.get("company") or "").strip()
    title = str(candidate.get("title") or "").strip()
    location = str(candidate.get("location") or "").strip()
    if company and title:
        query = db.query(Job).filter(Job.company.ilike(company), Job.title.ilike(title))
        if location:
            query = query.filter(Job.location.ilike(location))
        return query.first()
    return None


def find_duplicate_candidate(db: Session, duplicate_key: str) -> JobCandidate | None:
    if not duplicate_key:
        return None
    return db.query(JobCandidate).filter(JobCandidate.duplicate_key == duplicate_key).order_by(JobCandidate.id.desc()).first()
