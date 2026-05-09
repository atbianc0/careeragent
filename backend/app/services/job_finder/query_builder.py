from __future__ import annotations

import re
from typing import Any

from app.services.ai import get_ai_provider
from app.services.profile.profile_store import load_profile_document
from app.services.resume import load_resume_document
from app.utils.text import normalize_whitespace

DEFAULT_TARGET_ROLES = [
    "Data Scientist",
    "Data Engineer",
    "ML Engineer",
    "Analytics Engineer",
    "Data Analyst",
    "Software Engineer - Data/ML",
    "Early Career Research Engineer",
]
DEFAULT_LOCATIONS = [
    "San Francisco",
    "South San Francisco",
    "Oakland",
    "Berkeley",
    "Emeryville",
    "San Mateo",
    "Foster City",
    "Palo Alto",
    "Menlo Park",
    "Mountain View",
    "Sunnyvale",
    "Santa Clara",
    "San Jose",
    "Redwood City",
    "Fremont",
]
DEFAULT_TEST_QUERIES = [
    "new grad data scientist bay area",
    "entry level data scientist san francisco",
    "new college grad machine learning engineer bay area",
    "data engineer new grad bay area",
    "analytics engineer entry level san francisco",
    "data analyst new grad bay area",
    "software engineer machine learning new grad bay area",
    "early career research engineer machine learning bay area",
]
EARLY_CAREER_TERMS = ["new grad", "entry level", "early career", "associate", "0-2 years"]
EXCLUDED_TERMS = ["senior", "staff", "principal", "lead", "manager", "master's required", "phd required", "5+ years"]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = normalize_whitespace(str(value)).strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _extract_resume_skills(resume_text: str) -> list[str]:
    candidates = []
    for skill in ["Python", "SQL", "Pandas", "NumPy", "scikit-learn", "PyTorch", "TensorFlow", "Spark", "dbt", "Tableau", "R"]:
        if re.search(rf"\b{re.escape(skill)}\b", resume_text, flags=re.IGNORECASE):
            candidates.append(skill)
    return candidates


def get_default_test_queries() -> list[str]:
    return list(DEFAULT_TEST_QUERIES)


def load_search_inputs() -> tuple[dict[str, Any], str, list[str]]:
    warnings: list[str] = []
    try:
        profile_document = load_profile_document()
        profile = dict(profile_document.get("profile") or {})
        if profile_document.get("source") == "example":
            warnings.append("Using the safe example profile for query generation.")
    except Exception as exc:
        profile = {}
        warnings.append(f"Profile could not be loaded for query generation: {exc}")

    try:
        resume_document = load_resume_document()
        resume_text = str(resume_document.get("content") or "")
        if resume_document.get("source") == "example":
            warnings.append("Using the safe example resume for query generation.")
    except Exception as exc:
        resume_text = ""
        warnings.append(f"Resume could not be loaded for query generation: {exc}")

    return profile, resume_text, warnings


def build_search_profile(profile: dict[str, Any], resume_text: str) -> dict[str, Any]:
    target_roles = _unique([str(role) for role in profile.get("target_roles") or []]) or DEFAULT_TARGET_ROLES
    preferred_locations = _unique([str(location) for location in profile.get("preferred_locations") or []]) or DEFAULT_LOCATIONS
    skills = _unique([str(skill) for skill in profile.get("skills") or []] + _extract_resume_skills(resume_text))
    return {
        "target_roles": target_roles,
        "preferred_locations": preferred_locations,
        "location_group": "Bay Area",
        "remote_ok": True,
        "experience_levels": ["New Grad", "University Grad", "Entry Level", "Early Career", "Associate", "0-2 years"],
        "excluded_terms": EXCLUDED_TERMS,
        "skills": skills[:20],
    }


def generate_rule_based_queries(profile: dict[str, Any], resume_text: str) -> list[str]:
    search_profile = build_search_profile(profile, resume_text)
    queries = list(DEFAULT_TEST_QUERIES)
    role_terms = [role.lower().replace(" - ", " ") for role in search_profile["target_roles"]]
    for role in role_terms[:8]:
        queries.append(f"new grad {role} bay area")
        queries.append(f"entry level {role} san francisco")
    for skill in search_profile.get("skills", [])[:4]:
        queries.append(f"entry level {skill} data jobs bay area")
    return _unique(queries)[:24]


def generate_ai_queries(profile: dict[str, Any], resume_text: str, provider: str = "mock") -> list[str]:
    fallback_queries = generate_rule_based_queries(profile, resume_text)
    ai_provider = get_ai_provider(provider)
    if not ai_provider.is_available():
        return fallback_queries
    result = ai_provider.parse_json(
        task="job_finder_queries",
        prompt=(
            "Generate conservative job search queries for new-grad Bay Area data, analytics, ML, and data/software roles. "
            "Avoid senior, staff, principal, manager, PhD-required, and 5+ year roles."
        ),
        context={"fallback_json": {"queries": fallback_queries[:12]}, "profile": profile},
    )
    parsed = result.get("parsed_json")
    if isinstance(parsed, dict) and isinstance(parsed.get("queries"), list):
        return _unique([str(query) for query in parsed["queries"]] + fallback_queries)[:30]
    return fallback_queries

