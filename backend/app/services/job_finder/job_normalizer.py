from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.services.job_finder.level_classifier import classify_degree_requirements, classify_experience_requirements
from app.services.job_finder.location_classifier import classify_location_fit
from app.services.job_finder.role_classifier import classify_role_category
from app.services.job_finder.sources.common import clean_text, infer_company_from_url


def _source_value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _first(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value if str(item).strip())
        if isinstance(value, dict):
            continue
        cleaned = clean_text(str(value))
        if cleaned and cleaned.lower() not in {"unknown", "unknown title", "unknown workday job", "n/a", "none", "null"}:
            return cleaned
    return ""


def _html_to_text(value: Any) -> str:
    text = str(value or "")
    if "<" not in text or ">" not in text:
        return clean_text(text)
    soup = BeautifulSoup(text, "html.parser")
    return clean_text(soup.get_text("\n", strip=True))


def _company_from_source(raw_job: dict, source: Any, url: str) -> str:
    source_company = _first(_source_value(source, "company"), _source_value(source, "name"), _source_value(source, "source_name"))
    raw_company = _first(raw_job.get("company"), raw_job.get("companyName"), raw_job.get("hiringOrganization"))
    if raw_company:
        return raw_company
    if source_company:
        return source_company
    return infer_company_from_url(url)


def _int_year(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _education_requirement_label(degree: dict[str, Any]) -> str:
    level = str(degree.get("degree_level") or "")
    strength = str(degree.get("degree_requirement_strength") or "")
    if degree.get("phd_required"):
        return "PhD required"
    if degree.get("masters_required"):
        return "Master's required"
    if level == "phd" and strength == "preferred":
        return "PhD preferred"
    if level == "masters" and strength == "preferred":
        return "Master's preferred"
    if level == "bachelors" and strength == "equivalent_experience":
        return "Bachelor's or equivalent experience"
    if level == "bachelors":
        return "Bachelor's required/accepted"
    if level == "none_mentioned":
        return "No degree mentioned"
    return ""


def _metadata_confidence(missing_fields: list[str], title: str, description: str, url: str, location: str) -> int:
    score = 100
    penalties = {"title": 40, "url": 35, "location": 15, "job_description": 20, "company": 10}
    for field in missing_fields:
        score -= penalties.get(field, 5)
    if title and description:
        score += 5
    if location:
        score += 5
    if url and urlparse(url).scheme in {"http", "https"}:
        score += 5
    return max(0, min(score, 100))


def normalize_raw_job(raw_job: dict, source: Any) -> dict:
    url = _first(raw_job.get("url"), raw_job.get("absolute_url"), raw_job.get("hostedUrl"), raw_job.get("applyUrl"), raw_job.get("jobUrl"))
    description = _html_to_text(
        raw_job.get("job_description")
        or raw_job.get("description")
        or raw_job.get("descriptionPlain")
        or raw_job.get("descriptionHtml")
        or raw_job.get("content")
    )
    title = _first(raw_job.get("title"), raw_job.get("text"), raw_job.get("jobTitle"))
    location = _first(raw_job.get("location"), raw_job.get("locationsText"), raw_job.get("locationName"), raw_job.get("locationNames"))
    company = _company_from_source(raw_job, source, url)

    level = classify_experience_requirements(title, description)
    years_min = raw_job.get("years_experience_min")
    years_max = raw_job.get("years_experience_max")
    if years_min is None:
        years_min = level.get("years_min")
    if years_max is None:
        years_max = level.get("years_max")
    years_min = _int_year(years_min)
    years_max = _int_year(years_max)
    location_fit = classify_location_fit(location, description)
    role = classify_role_category(title, description)
    degree = classify_degree_requirements(title, description)
    education = _education_requirement_label(degree)

    missing_fields = []
    if not company:
        missing_fields.append("company")
    if not title:
        missing_fields.append("title")
    if not location_fit["location"]:
        missing_fields.append("location")
    if not url:
        missing_fields.append("url")
    if not description:
        missing_fields.append("job_description")

    normalized = {
        "source_type": raw_job.get("source_type"),
        "company": company or "Unknown Company",
        "title": title,
        "location": location_fit["location"],
        "url": url,
        "description_snippet": description[:500] if description else "",
        "job_description": description,
        "role_category": role["role_category"],
        "experience_level": level["experience_level"],
        "seniority_level": level["experience_level"],
        "level_confidence": level["confidence"],
        "location_fit": location_fit["location_fit"],
        "remote_status": location_fit["remote_status"],
        "required_skills": list(raw_job.get("required_skills") or []),
        "preferred_skills": list(raw_job.get("preferred_skills") or []),
        "years_experience_min": years_min,
        "years_experience_max": years_max,
        "salary_min": raw_job.get("salary_min"),
        "salary_max": raw_job.get("salary_max"),
        "salary_currency": raw_job.get("salary_currency"),
        "posted_date": raw_job.get("posted_date"),
        "education_requirement": education,
        "metadata_confidence": 0,
        "missing_fields": missing_fields,
        "raw_data": {
            **dict(raw_job.get("raw_data") or {}),
            "normalizer": {
                "level": level,
                "location": location_fit,
                "role": role,
                "degree": degree,
                "education_requirement": education,
            },
        },
    }
    normalized["metadata_confidence"] = _metadata_confidence(missing_fields, title, description, url, location_fit["location"])
    return normalized
