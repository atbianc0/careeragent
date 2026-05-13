from __future__ import annotations

import re
from typing import Any

from app.services.ai import get_ai_provider, require_ai_allowed
from app.services.profile.profile_store import load_profile_document
from app.services.resume import load_resume_document
from app.utils.text import normalize_whitespace

DEFAULT_TARGET_ROLES = [
    "Data Scientist",
    "Data Engineer",
    "Machine Learning Engineer",
    "ML Engineer",
    "AI Engineer",
    "Analytics Engineer",
    "Data Analyst",
    "Product Analyst",
    "Business Intelligence Analyst",
    "Software Engineer Data",
    "Software Engineer Machine Learning",
    "Software Engineer AI",
    "Research Engineer",
    "Applied Scientist",
    "Applied AI Engineer",
]
DEFAULT_LOCATIONS = [
    "Bay Area",
    "San Francisco",
    "Palo Alto",
    "Mountain View",
    "Sunnyvale",
    "Santa Clara",
    "San Jose",
    "Foster City",
    "Redwood City",
    "Remote US",
]
DEFAULT_TEST_QUERIES = [
    "data scientist",
    "data engineer",
    "machine learning engineer",
    "ml engineer",
    "ai engineer",
    "analytics engineer",
    "data analyst",
    "product analyst",
    "business intelligence analyst",
    "software engineer data",
    "software engineer machine learning",
    "software engineer ai",
    "research engineer",
    "applied scientist",
    "applied ai engineer",
    "new grad",
    "new college grad",
    "university grad",
    "entry level",
    "early career",
    "associate",
    "junior",
    "software engineer i",
    "data engineer i",
    "data analyst i",
    "0-2 years",
    "bay area",
    "san francisco",
    "palo alto",
    "mountain view",
    "sunnyvale",
    "santa clara",
    "san jose",
    "foster city",
    "redwood city",
    "remote us",
]
EARLY_CAREER_TERMS = ["new grad", "new college grad", "university grad", "entry level", "early career", "associate", "junior", "0-2 years"]
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
    for role in role_terms[:12]:
        queries.append(role)
    for skill in search_profile.get("skills", [])[:4]:
        queries.append(str(skill).lower())
    return _unique(queries)[:40]


def generate_ai_queries(
    profile: dict[str, Any],
    resume_text: str,
    *,
    user_enabled: bool = False,
    user_triggered: bool = False,
) -> dict[str, Any]:
    fallback_queries = generate_rule_based_queries(profile, resume_text)
    guard = require_ai_allowed(
        action="generate_job_search_queries",
        user_enabled=user_enabled,
        user_triggered=user_triggered,
    )
    if not guard.get("allowed"):
        return {
            "queries": fallback_queries,
            "warnings": [str(guard.get("message") or "External AI query generation blocked by policy.")],
            "api_used": False,
            "provider": guard.get("provider"),
            "api_action": "generate_job_search_queries",
            "blocked_reason": guard.get("reason"),
        }
    ai_provider = get_ai_provider()
    if not ai_provider.is_available():
        return {
            "queries": fallback_queries,
            "warnings": [ai_provider.unavailable_reason or f"{ai_provider.name} provider is unavailable."],
            "api_used": False,
            "provider": ai_provider.name,
            "api_action": "generate_job_search_queries",
            "blocked_reason": "provider_unavailable",
        }
    result = ai_provider.parse_json(
        task="job_finder_queries",
        prompt=(
            "Generate conservative job search queries for new-grad Bay Area data, analytics, ML, and data/software roles. "
            "Avoid senior, staff, principal, manager, PhD-required, and 5+ year roles."
        ),
        context={
            "fallback_json": {"queries": fallback_queries[:12]},
            "profile": profile,
            "api_action": "generate_job_search_queries",
            "user_enabled": user_enabled,
            "user_triggered": user_triggered,
        },
    )
    parsed = result.get("parsed_json")
    if isinstance(parsed, dict) and isinstance(parsed.get("queries"), list):
        return {
            "queries": _unique([str(query) for query in parsed["queries"]] + fallback_queries)[:30],
            "warnings": list(result.get("warnings") or []),
            "api_used": bool((result.get("raw") or {}).get("api_used")),
            "provider": ai_provider.name,
            "api_action": "generate_job_search_queries",
            "model": (result.get("raw") or {}).get("model"),
        }
    return {
        "queries": fallback_queries,
        "warnings": list(result.get("warnings") or ["AI query generation returned no usable keywords."]),
        "api_used": False,
        "provider": ai_provider.name,
        "api_action": "generate_job_search_queries",
        "blocked_reason": (result.get("raw") or {}).get("blocked_reason"),
    }
