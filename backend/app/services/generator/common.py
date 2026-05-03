from __future__ import annotations

from typing import Any


def unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(cleaned)
    return unique


def collect_relevant_skills(job: Any, profile: dict[str, Any], scoring_evidence: dict[str, Any] | None = None) -> list[str]:
    scoring_raw_data = dict(getattr(job, "scoring_raw_data", None) or {})
    scoring_skill_match = dict((scoring_evidence or {}).get("skill_match") or {})
    matched = (
        list(scoring_raw_data.get("matched_required_skills") or [])
        + list(scoring_raw_data.get("matched_preferred_skills") or [])
        + list(scoring_skill_match.get("matched_required_skills") or [])
        + list(scoring_skill_match.get("matched_preferred_skills") or [])
    )

    if matched:
        return unique_preserve_order(matched)

    profile_skills = [str(skill) for skill in (profile.get("skills") or [])]
    job_skills = [str(skill) for skill in ((getattr(job, "required_skills", None) or []) + (getattr(job, "preferred_skills", None) or []))]
    profile_lookup = {skill.casefold() for skill in profile_skills}
    overlapping = [skill for skill in job_skills if skill.casefold() in profile_lookup]
    return unique_preserve_order(overlapping or profile_skills[:5])


def collect_missing_skills(job: Any) -> list[str]:
    scoring_raw_data = dict(getattr(job, "scoring_raw_data", None) or {})
    missing = list(scoring_raw_data.get("missing_required_skills") or []) + list(scoring_raw_data.get("missing_preferred_skills") or [])
    return unique_preserve_order(missing)


def build_role_company_label(job: Any) -> str:
    title = str(getattr(job, "title", "") or "this role")
    company = str(getattr(job, "company", "") or "the company")
    if company.lower() == "unknown company":
        return title
    return f"{title} at {company}"


def profile_name(profile: dict[str, Any]) -> str:
    personal = profile.get("personal") or {}
    return str(personal.get("name") or "").strip()


def profile_links(profile: dict[str, Any]) -> dict[str, str]:
    raw_links = profile.get("links") or {}
    return {
        "linkedin": str(raw_links.get("linkedin") or "").strip(),
        "github": str(raw_links.get("github") or "").strip(),
        "portfolio": str(raw_links.get("portfolio") or "").strip(),
    }


def profile_education_summary(profile: dict[str, Any]) -> str:
    education = profile.get("education") or {}
    parts = [
        str(education.get("degree") or "").strip(),
        str(education.get("school") or "").strip(),
        str(education.get("graduation") or "").strip(),
    ]
    parts = [part for part in parts if part]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} at {parts[1]}"
    return f"{parts[0]} at {parts[1]} ({parts[2]})"


def writing_tone(profile: dict[str, Any]) -> str:
    writing_style = profile.get("writing_style") or {}
    return str(writing_style.get("tone") or "direct and specific").strip()
