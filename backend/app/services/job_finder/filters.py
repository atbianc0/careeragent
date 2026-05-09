from __future__ import annotations

import re
from typing import Any

from app.utils.text import normalize_whitespace

TARGET_ROLE_CATEGORIES = {
    "Data Scientist",
    "Data Engineer",
    "ML Engineer",
    "Analytics Engineer",
    "Data Analyst",
    "Software Engineer - Data/ML",
    "Research Engineer",
}
ADJACENT_ROLE_CATEGORIES = {
    "Software Engineer",
    "Backend Engineer",
    "Platform Engineer",
    "Infrastructure Engineer",
    "Solutions Engineer - Data/AI",
    "Technical Analyst",
    "Quantitative Analyst",
}
ADVANCED_LEVELS = {"advanced_senior", "senior"}
ENTRY_LEVELS = {"intern", "internship", "new_grad_entry", "early_career"}
LOCATION_MATCHES = {"bay_area", "remote_us", "hybrid_bay_area"}
MATCH_MODES = {"strict", "balanced", "broad"}
DEFAULT_TARGET_EXPERIENCE_LEVELS = {"new_grad_entry", "early_career", "unknown"}
DEFAULT_DEGREE_FILTER = {
    "allow_no_degree": True,
    "allow_bachelors": True,
    "allow_masters_preferred": True,
    "allow_masters_required": False,
    "allow_phd_preferred": True,
    "allow_phd_required": False,
    "allow_unknown": True,
}
KNOWN_SKILLS = {
    "python",
    "sql",
    "pandas",
    "numpy",
    "scikit-learn",
    "sklearn",
    "pytorch",
    "tensorflow",
    "spark",
    "dbt",
    "tableau",
    "r",
    "java",
    "javascript",
    "typescript",
    "c++",
    "machine learning",
    "data science",
    "data engineering",
    "analytics",
    "statistics",
    "etl",
}
IRRELEVANT_TITLE_RE = re.compile(
    r"\b(?:account executive|sales|customer success|recruiter|human resources|hr\b|legal|counsel|"
    r"finance|accounting|marketing|designer|office|admin|administrative|operations|product manager)\b",
    flags=re.IGNORECASE,
)
TECHNICAL_RESCUE_RE = re.compile(r"\b(?:data|analytics|analyst|ai|ml|machine learning|business intelligence|bi)\b", flags=re.IGNORECASE)


def _norm(value: Any) -> str:
    return normalize_whitespace(str(value or "")).lower()


def _haystack(candidate: dict[str, Any]) -> str:
    return _norm(
        " ".join(
            [
                str(candidate.get("title") or ""),
                str(candidate.get("location") or ""),
                str(candidate.get("description_snippet") or ""),
                str(candidate.get("job_description") or ""),
                " ".join(candidate.get("requirements") or []),
            ]
        )
    )


def _normalizer(candidate: dict[str, Any]) -> dict[str, Any]:
    raw_data = dict(candidate.get("raw_data") or {})
    normalizer = raw_data.get("normalizer")
    return normalizer if isinstance(normalizer, dict) else {}


def _level_details(candidate: dict[str, Any]) -> dict[str, Any]:
    level = dict(_normalizer(candidate).get("level") or {})
    if not level:
        level = {}
    level.setdefault("experience_level", candidate.get("experience_level") or "unknown")
    level.setdefault("years_min", candidate.get("years_experience_min"))
    level.setdefault("years_max", candidate.get("years_experience_max"))
    level.setdefault("requirement_strength", level.get("requirement_strength") or "unknown")
    return level


def _degree_details(candidate: dict[str, Any]) -> dict[str, Any]:
    degree = dict(_normalizer(candidate).get("degree") or {})
    education = _norm(candidate.get("education_requirement"))
    if not degree:
        degree = {
            "degree_level": "unknown",
            "degree_requirement_strength": "unknown",
            "masters_required": False,
            "phd_required": False,
            "bachelors_required": False,
            "degree_text": "",
        }
    if "phd required" in education:
        degree["degree_level"] = "phd"
        degree["degree_requirement_strength"] = "required"
        degree["phd_required"] = True
    elif "master" in education and "required" in education:
        degree["degree_level"] = "masters"
        degree["degree_requirement_strength"] = "required"
        degree["masters_required"] = True
    return degree


def _allowed_experience_levels(search_profile: dict[str, Any]) -> set[str]:
    configured = {str(item).strip() for item in search_profile.get("target_experience_levels") or [] if str(item).strip()}
    return configured or set(DEFAULT_TARGET_EXPERIENCE_LEVELS)


def _excluded_experience_levels(search_profile: dict[str, Any]) -> set[str]:
    return {str(item).strip() for item in search_profile.get("excluded_experience_levels") or [] if str(item).strip()}


def _degree_filter(search_profile: dict[str, Any]) -> dict[str, bool]:
    configured = dict(search_profile.get("degree_filter") or {})
    return {**DEFAULT_DEGREE_FILTER, **{key: bool(value) for key, value in configured.items()}}


def _role_confidence(candidate: dict[str, Any]) -> float:
    role = dict(_normalizer(candidate).get("role") or {})
    try:
        return float(role.get("confidence") or 0)
    except (TypeError, ValueError):
        return 0.0


def _strong_role_match(candidate: dict[str, Any]) -> bool:
    return (candidate.get("role_category") or "Other") in TARGET_ROLE_CATEGORIES and _role_confidence(candidate) >= 70


def _adjacent_role_match(candidate: dict[str, Any]) -> bool:
    return (candidate.get("role_category") or "Other") in ADJACENT_ROLE_CATEGORIES


def _related_role_match(candidate: dict[str, Any], matched_skills: list[str]) -> bool:
    if _strong_role_match(candidate):
        return True
    if _adjacent_role_match(candidate):
        return True
    title = _norm(candidate.get("title"))
    related_terms = [
        "data",
        "analytics",
        "analyst",
        "machine learning",
        "ml",
        "ai",
        "research",
        "platform",
        "etl",
        "database",
        "business intelligence",
    ]
    return any(term in title for term in related_terms) or len(matched_skills) >= 2


def _clearly_irrelevant_role(candidate: dict[str, Any]) -> bool:
    title = _norm(candidate.get("title"))
    if not title:
        return False
    return bool(IRRELEVANT_TITLE_RE.search(title) and not TECHNICAL_RESCUE_RE.search(title))


def _mode_label(match_mode: str) -> str:
    return {"strict": "Strict Match", "balanced": "Balanced Match", "broad": "Broad Match"}.get(match_mode, "Balanced Match")


def _clean_skills(skills: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for skill in skills:
        cleaned = normalize_whitespace(str(skill or "")).strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        if len(key) < 2 and key not in KNOWN_SKILLS:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _skill_overlap(candidate: dict[str, Any], search_profile: dict[str, Any]) -> list[str]:
    text = _haystack(candidate)
    skills = _clean_skills(list(search_profile.get("skills") or []))
    matched = []
    for skill in skills:
        key = skill.lower()
        if key == "r":
            patterns = [r"\br programming\b", r"\br language\b", r"\busing r\b"]
            if any(re.search(pattern, text) for pattern in patterns):
                matched.append(skill)
            continue
        if len(key) >= 2 and key in text:
            matched.append(skill)
    return matched[:4]


def _education_exclusion(candidate: dict[str, Any]) -> str:
    education = _norm(candidate.get("education_requirement"))
    if "phd required" in education:
        return "Excluded: PhD required."
    if "master" in education and "required" in education:
        return "Excluded: Master's degree required."
    return ""


def _years_exclusion(candidate: dict[str, Any]) -> str:
    level = _level_details(candidate)
    years = level.get("years_min") if level.get("years_min") is not None else candidate.get("years_experience_min")
    strength = str(level.get("requirement_strength") or "unknown")
    if isinstance(years, int | float) and years >= 6 and strength in {"required", "minimum", "unknown"}:
        return f"Excluded: requires {years:g}+ years of experience."
    return ""


def _degree_disqualification(candidate: dict[str, Any], search_profile: dict[str, Any]) -> str:
    degree = _degree_details(candidate)
    config = _degree_filter(search_profile)
    level = str(degree.get("degree_level") or "unknown")
    strength = str(degree.get("degree_requirement_strength") or "unknown")
    masters_required = bool(degree.get("masters_required"))
    phd_required = bool(degree.get("phd_required"))

    if phd_required and not config["allow_phd_required"]:
        return "Excluded: PhD required."
    if masters_required and not config["allow_masters_required"]:
        return "Excluded: Master's degree required."
    return ""


def _experience_disqualification(candidate: dict[str, Any], search_profile: dict[str, Any], match_mode: str) -> tuple[str, bool]:
    allowed = _allowed_experience_levels(search_profile)
    explicitly_excluded = _excluded_experience_levels(search_profile)
    level = str(_level_details(candidate).get("experience_level") or "unknown")
    if level == "intern":
        level = "internship"
    if level == "advanced_senior":
        level = "senior"
    years_min = _level_details(candidate).get("years_min")
    strength = str(_level_details(candidate).get("requirement_strength") or "unknown")
    required_like = strength in {"required", "minimum", "unknown"}

    if level in explicitly_excluded:
        if level == "senior":
            return "Excluded: requires senior/advanced level.", False
        return f"Excluded: {level.replace('_', ' ')} level is disabled.", False
    if level == "senior" and "senior" not in allowed:
        return "Excluded: Senior title or senior/advanced experience requirement.", False
    if isinstance(years_min, int | float) and years_min >= 8 and strength in {"required", "minimum"} and "senior" not in allowed:
        return f"Excluded: requires {years_min:g}+ years of experience.", False
    if isinstance(years_min, int | float) and years_min >= 6 and strength in {"required", "minimum"} and "senior" not in allowed:
        return f"Excluded: requires {years_min:g}+ years of experience.", False
    if level == "unknown":
        if "unknown" not in allowed:
            return "Excluded: experience level is unknown.", False
        return "", True

    early_targets = bool(allowed.intersection({"new_grad_entry", "early_career"})) and not allowed.intersection({"mid_level", "senior"})
    if level not in allowed:
        if match_mode == "broad" and level == "mid_level" and "mid_level" not in explicitly_excluded:
            return "", True
        if match_mode == "balanced" and early_targets and level == "mid_level":
            if strength in {"preferred", "nice_to_have"} or (isinstance(years_min, int | float) and years_min <= 5):
                return "", True
        return f"Excluded: {level.replace('_', ' ')} level is outside selected experience filters.", False

    if early_targets and isinstance(years_min, int | float) and years_min >= 3 and required_like:
        if match_mode == "strict":
            return f"Excluded: requires {years_min:g}+ years of experience.", False
        if match_mode == "balanced" and years_min <= 5:
            return "", True
        if match_mode != "broad":
            return f"Excluded: requires {years_min:g}+ years of experience.", False

    return "", False


def _result(
    status: str,
    score: float,
    reasons: list[str],
    *,
    primary_exclusion_category: str | None = None,
    hard_excluded: bool = False,
    would_show_in_broad: bool = False,
) -> dict[str, Any]:
    return {
        "filter_status": status,
        "relevance_score": round(max(0.0, min(score, 100.0)), 2),
        "filter_reasons": reasons,
        "primary_exclusion_category": primary_exclusion_category,
        "hard_excluded": hard_excluded,
        "would_show_in_broad": would_show_in_broad,
        "all_reasons": reasons,
    }


def build_candidate_match_reasons(candidate: dict[str, Any], search_profile: dict[str, Any], match_mode: str = "balanced") -> list[str]:
    normalizer = _normalizer(candidate)
    role = dict(normalizer.get("role") or {})
    level = _level_details(candidate)
    location = dict(normalizer.get("location") or {})
    degree = _degree_details(candidate)
    reasons: list[str] = []

    role_category = candidate.get("role_category") or role.get("role_category") or "Other"
    if role_category in TARGET_ROLE_CATEGORIES:
        reasons.append(f"Title matches target role: {role_category}.")
    else:
        reasons.append("Title is related but does not directly match a target role.")

    location_fit = candidate.get("location_fit") or location.get("location_fit") or "unknown"
    location_reasons = list(location.get("reasons") or [])
    if location_reasons:
        reasons.append(str(location_reasons[0]))
    elif location_fit == "unknown":
        reasons.append("Location is missing, so CareerAgent cannot confirm Bay Area fit.")
    elif location_fit == "outside_target":
        reasons.append("Location is outside the target area.")

    experience_level = candidate.get("experience_level") or level.get("experience_level") or "unknown"
    level_reasons = list(level.get("reasons") or [])
    label = {
        "intern": "internship",
        "internship": "internship",
        "new_grad_entry": "entry/new-grad",
        "early_career": "early career",
        "mid_level": "mid-level",
        "advanced_senior": "senior",
        "senior": "senior",
        "unknown": "unknown",
    }.get(str(experience_level), str(experience_level))
    if level_reasons:
        reasons.append(str(level_reasons[0]))
    elif experience_level == "unknown":
        reasons.append(f"Experience level is unknown, kept for review because the title matches {role_category}.")
    else:
        years_min = level.get("years_min")
        years_max = level.get("years_max")
        strength = str(level.get("requirement_strength") or "unknown").replace("_", " ")
        if years_min is not None and years_max is not None:
            reasons.append(f"Experience requirement appears {label}: {years_min}-{years_max} years {strength}.")
        elif years_min is not None:
            reasons.append(f"Experience requirement appears {label}: {years_min}+ years {strength}.")
        else:
            reasons.append(f"Experience fits target: {label}.")

    degree_level = str(degree.get("degree_level") or "unknown")
    degree_strength = str(degree.get("degree_requirement_strength") or "unknown")
    if degree.get("phd_required"):
        reasons.append("PhD required.")
    elif degree.get("masters_required"):
        reasons.append("Master's degree required.")
    elif degree_level == "bachelors" and degree_strength == "equivalent_experience":
        reasons.append("Degree requirement is Bachelor's or equivalent experience.")
    elif degree_level == "masters" and degree_strength == "preferred":
        reasons.append("Master's is preferred, not required.")
    elif degree_level == "phd" and degree_strength == "preferred":
        reasons.append("PhD is preferred, not required.")
    elif degree_level == "none_mentioned":
        reasons.append("No strict degree requirement found.")
    elif degree_level == "unknown":
        reasons.append("Degree requirement is unknown.")
    elif degree_level == "bachelors":
        reasons.append("Bachelor's degree is required or accepted.")

    matched_skills = _skill_overlap(candidate, search_profile)
    if matched_skills:
        reasons.append(f"Skills overlap: {', '.join(matched_skills)}.")

    missing_fields = list(candidate.get("missing_fields") or [])
    if "title" in missing_fields:
        reasons.append("Missing title lowered confidence.")
    if "location" in missing_fields:
        reasons.append("Missing location lowered confidence.")
    if "job_description" in missing_fields:
        reasons.append("Missing description lowered confidence.")

    if match_mode in MATCH_MODES:
        reasons.append(f"Evaluated with {_mode_label(match_mode)}.")

    seen: set[str] = set()
    unique = []
    for reason in reasons:
        clean = normalize_whitespace(str(reason))
        if clean and clean not in seen:
            seen.add(clean)
            unique.append(clean)
    return unique or ["Candidate retained for review."]


def filter_candidate(candidate: dict[str, Any], search_profile: dict[str, Any], match_mode: str = "balanced") -> dict[str, Any]:
    match_mode = match_mode if match_mode in MATCH_MODES else "balanced"
    missing_fields = set(candidate.get("missing_fields") or [])
    source_type = _norm(candidate.get("source_type"))
    if source_type == "workday" and ("url" in missing_fields or "title" in missing_fields):
        return _result(
            "incomplete",
            0.0,
            ["Incomplete: Workday result is missing a real job title or URL."],
            primary_exclusion_category="incomplete",
            hard_excluded=True,
        )
    if "url" in missing_fields:
        return _result(
            "incomplete",
            0.0,
            ["Incomplete: missing job URL."],
            primary_exclusion_category="incomplete",
            hard_excluded=True,
        )
    if "title" in missing_fields and "job_description" in missing_fields:
        return _result(
            "incomplete",
            0.0,
            ["Incomplete: missing both title and description."],
            primary_exclusion_category="incomplete",
            hard_excluded=True,
        )

    degree_exclusion = _degree_disqualification(candidate, search_profile) or _education_exclusion(candidate)
    if degree_exclusion:
        return _result(
            "excluded",
            0.0,
            build_candidate_match_reasons(candidate, search_profile, match_mode) + [degree_exclusion],
            primary_exclusion_category="degree",
            hard_excluded=True,
        )

    role_category = candidate.get("role_category") or "Other"
    level = _level_details(candidate)
    degree = _degree_details(candidate)
    experience_level = str(level.get("experience_level") or candidate.get("experience_level") or "unknown")
    if experience_level == "intern":
        experience_level = "internship"
    if experience_level == "advanced_senior":
        experience_level = "senior"
    location_fit = candidate.get("location_fit") or "unknown"
    metadata_confidence = float(candidate.get("metadata_confidence") or 0)
    matched_skills = _skill_overlap(candidate, search_profile)
    strong_role = _strong_role_match(candidate)
    adjacent_role = _adjacent_role_match(candidate)
    related_role = _related_role_match(candidate, matched_skills)
    reasons = build_candidate_match_reasons(candidate, search_profile, match_mode)
    experience_exclusion, experience_near_miss = _experience_disqualification(candidate, search_profile, match_mode)
    years_exclusion = _years_exclusion(candidate)
    if years_exclusion and "senior" not in _allowed_experience_levels(search_profile):
        experience_exclusion = years_exclusion
        experience_near_miss = False

    score = 10.0
    if role_category in TARGET_ROLE_CATEGORIES:
        score += 35
    elif adjacent_role:
        score += 20
    elif related_role:
        score += 18
    if location_fit in LOCATION_MATCHES:
        score += 25
    elif location_fit == "outside_target":
        score -= 8 if match_mode in {"balanced", "broad"} else 25
    elif location_fit == "unknown":
        score += 3 if match_mode == "broad" else -2 if match_mode == "balanced" else -10
    if experience_level in ENTRY_LEVELS:
        score += 20
    elif experience_level == "mid_level":
        score += 8 if match_mode == "broad" else 2 if experience_near_miss else 5
    elif experience_level == "unknown":
        score += 3 if match_mode in {"balanced", "broad"} else -5
    if experience_near_miss:
        score -= 8 if match_mode == "balanced" else 3
    degree_level = str(degree.get("degree_level") or "unknown")
    degree_strength = str(degree.get("degree_requirement_strength") or "unknown")
    if degree_level in {"none_mentioned", "bachelors"}:
        score += 6
    elif degree_strength in {"preferred", "equivalent_experience", "accepted"}:
        score += 2
    elif degree_level == "unknown":
        score -= 2
    if matched_skills:
        score += min(18, 8 + len(matched_skills) * 3)
    if metadata_confidence < 70:
        score -= 5 if match_mode in {"balanced", "broad"} else 10
    if "job_description" in missing_fields:
        score -= 4 if match_mode == "broad" else 8
    if "location" in missing_fields:
        score -= 3 if match_mode in {"balanced", "broad"} else 8

    if experience_exclusion:
        hard_experience = any(term in experience_exclusion.lower() for term in ["senior", "6+", "7+", "8+", "9+", "10+"])
        return _result(
            "excluded",
            score,
            reasons + [experience_exclusion],
            primary_exclusion_category="experience",
            hard_excluded=hard_experience,
            would_show_in_broad=not hard_experience,
        )

    if _clearly_irrelevant_role(candidate):
        return _result(
            "excluded",
            score,
            reasons + ["Excluded: clearly irrelevant role family."],
            primary_exclusion_category="role",
            hard_excluded=True,
        )

    if match_mode == "strict" and not strong_role:
        return _result(
            "excluded",
            score,
            reasons + ["Excluded: strict mode requires a clear target-role title match."],
            primary_exclusion_category="role",
            hard_excluded=False,
            would_show_in_broad=related_role or adjacent_role,
        )

    if match_mode == "strict" and location_fit == "unknown" and not strong_role:
        return _result(
            "excluded",
            score,
            reasons + ["Excluded: strict mode requires Bay Area or US Remote location unless the title is a strong match."],
            primary_exclusion_category="location",
            hard_excluded=False,
            would_show_in_broad=True,
        )

    if location_fit == "outside_target":
        if match_mode == "strict":
            return _result(
                "excluded",
                score,
                reasons + ["Excluded: location is outside target area."],
                primary_exclusion_category="location",
                hard_excluded=False,
                would_show_in_broad=related_role or adjacent_role,
            )
        reasons.append("Location is outside the target area, shown as a near match for review.")

    if match_mode == "balanced" and not related_role:
        return _result(
            "excluded",
            score,
            reasons + ["Excluded: balanced mode needs a target role, adjacent technical title, or meaningful skill overlap."],
            primary_exclusion_category="role",
            hard_excluded=False,
            would_show_in_broad=not _clearly_irrelevant_role(candidate),
        )

    if match_mode == "broad" and not related_role and role_category not in TARGET_ROLE_CATEGORIES:
        return _result(
            "excluded",
            score,
            reasons + ["Excluded: broad mode still needs some data, ML, analytics, platform, or technical signal."],
            primary_exclusion_category="role",
            hard_excluded=False,
            would_show_in_broad=False,
        )

    if strong_role and location_fit in LOCATION_MATCHES and experience_level in ENTRY_LEVELS and not experience_near_miss and score >= 75:
        status = "good_match"
    elif experience_near_miss:
        status = "weak_match"
        if experience_level == "unknown":
            reasons.append("Experience level is unknown, kept for review because unknown experience is allowed.")
        else:
            reasons.append("Requires 3-5 years, shown as a stretch role.")
    elif match_mode == "strict" and location_fit == "unknown":
        status = "weak_match"
        reasons.append("Location is unknown, so strict mode kept this only as a weak match because the title is strong.")
    elif score >= (25 if match_mode == "broad" else 30):
        status = "weak_match"
    else:
        status = "excluded"
        reasons.append("Excluded: low confidence match after role, location, level, and metadata checks.")
        return _result(
            status,
            score,
            reasons,
            primary_exclusion_category="low_confidence",
            hard_excluded=False,
            would_show_in_broad=True,
        )

    return _result(status, score, reasons)
