from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

from app.services.jobs.parser import SKILL_PATTERNS
from app.services.profile.profile_store import load_profile_document
from app.services.resume.latex_resume import load_resume_document
from app.utils.text import normalize_whitespace

SKILL_ALIAS_MAP: dict[str, set[str]] = {
    "JavaScript": {"javascript", "js"},
    "TypeScript": {"typescript", "ts"},
    "scikit-learn": {"scikit-learn", "sklearn"},
    "PostgreSQL": {"postgresql", "postgres"},
    "machine learning": {"machine learning", "ml"},
    "artificial intelligence": {"artificial intelligence", "ai"},
    "GCP": {"gcp", "google cloud", "google cloud platform"},
    "AWS": {"aws", "amazon web services"},
    "Azure": {"azure", "microsoft azure"},
}
ROLE_KEYWORDS: dict[str, list[str]] = {
    "Data Scientist": ["data scientist", "applied scientist"],
    "Data Engineer": ["data engineer", "etl engineer", "analytics pipeline"],
    "ML Engineer": ["ml engineer", "machine learning engineer", "ai engineer"],
    "Analytics Engineer": ["analytics engineer", "dbt developer"],
    "Data Analyst": ["data analyst", "business analyst", "analytics analyst"],
    "Software Engineer": ["software engineer", "backend engineer", "frontend engineer", "full stack engineer"],
}
ROLE_FAMILIES: dict[str, set[str]] = {
    "data": {"Data Scientist", "Data Engineer", "ML Engineer", "Analytics Engineer", "Data Analyst"},
    "software": {"Software Engineer"},
}
STOPWORDS = {
    "and",
    "are",
    "for",
    "from",
    "have",
    "into",
    "our",
    "that",
    "the",
    "this",
    "with",
    "your",
    "will",
    "you",
    "job",
    "role",
    "team",
    "work",
    "experience",
    "using",
}
KEYWORD_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9+#./-]{2,}")
BAY_AREA_CITIES = {
    "san francisco",
    "oakland",
    "berkeley",
    "san jose",
    "mountain view",
    "palo alto",
    "redwood city",
    "south san francisco",
    "fremont",
    "sunnyvale",
}


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _today() -> date:
    return date.today()


def _days_since(reference_date: date | None) -> int | None:
    if reference_date is None:
        return None
    return max((_today() - reference_date).days, 0)


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = normalize_whitespace(str(value)).strip()
        if not normalized:
            continue
        seen_key = normalized.casefold()
        if seen_key in seen:
            continue
        seen.add(seen_key)
        unique.append(normalized)
    return unique


def _normalize_compare(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#./-]", " ", value.lower())).strip()


def _matches_alias(value: str, alias_values: set[str]) -> bool:
    normalized = _normalize_compare(value)
    for alias in alias_values:
        if normalized == alias:
            return True
        if f" {alias} " in f" {normalized} ":
            return True
    return False


def _canonicalize_skill(skill: str) -> str:
    normalized = _normalize_compare(skill)
    if not normalized:
        return ""
    for canonical, alias_values in SKILL_ALIAS_MAP.items():
        if _matches_alias(normalized, alias_values):
            return canonical
    for canonical, patterns in SKILL_PATTERNS:
        if any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in patterns):
            return canonical
    return normalize_whitespace(skill).strip()


def _canonicalize_role(role_text: str) -> str:
    normalized = _normalize_compare(role_text)
    if not normalized:
        return "Other"
    for canonical, keywords in ROLE_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return canonical
    return normalize_whitespace(role_text).strip().title()


def _find_role_family(role: str) -> str | None:
    canonical = _canonicalize_role(role)
    for family_name, roles in ROLE_FAMILIES.items():
        if canonical in roles:
            return family_name
    return None


def _extract_skills_from_text(text: str) -> list[str]:
    matches: list[str] = []
    for canonical, patterns in SKILL_PATTERNS:
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            matches.append(canonical)
    return _unique_preserve_order(matches)


def _clean_resume_text(resume_text: str) -> str:
    without_comments = re.sub(r"(?m)%.*$", " ", resume_text)
    without_commands = re.sub(r"\\[a-zA-Z*]+(?:\[[^\]]*\])?(?:\{([^}]*)\})?", r" \1 ", without_comments)
    without_braces = without_commands.replace("{", " ").replace("}", " ")
    without_math = re.sub(r"[$&_#^~]", " ", without_braces)
    return normalize_whitespace(without_math)


def _keyword_tokens(text: str) -> list[str]:
    tokens = [token.lower() for token in KEYWORD_PATTERN.findall(text)]
    filtered = [token for token in tokens if token not in STOPWORDS]
    return _unique_preserve_order(filtered)


def _extract_keywords_from_strings(values: list[str]) -> list[str]:
    text = "\n".join(value for value in values if value)
    return _keyword_tokens(text)


def _parse_year_from_text(value: str) -> int | None:
    match = re.search(r"(20\d{2}|19\d{2})", value)
    if match:
        return int(match.group(1))
    return None


def load_user_profile_for_scoring() -> dict[str, Any]:
    return load_profile_document()["profile"]


def load_resume_text_for_scoring() -> str:
    return load_resume_document()["content"]


def extract_resume_keywords(resume_text: str) -> dict[str, Any]:
    cleaned_text = _clean_resume_text(resume_text)
    skills = _extract_skills_from_text(cleaned_text)
    roles = [
        canonical
        for canonical, keywords in ROLE_KEYWORDS.items()
        if any(keyword in cleaned_text.lower() for keyword in keywords)
    ]
    education_keywords = _unique_preserve_order(
        match.group(0)
        for match in re.finditer(
            r"(bachelor|master|ph\.?d|data science|computer science|statistics|mathematics)",
            cleaned_text,
            flags=re.IGNORECASE,
        )
    )
    keywords = _unique_preserve_order(skills + roles + education_keywords + _keyword_tokens(cleaned_text))
    return {
        "skills": skills,
        "roles": roles,
        "education_keywords": education_keywords,
        "keywords": keywords[:60],
        "word_count": len(cleaned_text.split()),
    }


def extract_profile_keywords(profile: dict[str, Any]) -> dict[str, Any]:
    personal = profile.get("personal") or {}
    education = profile.get("education") or {}
    links = profile.get("links") or {}
    skills = _unique_preserve_order(_canonicalize_skill(skill) for skill in profile.get("skills") or [])
    target_roles = _unique_preserve_order(_canonicalize_role(role) for role in profile.get("target_roles") or [])
    education_parts = [
        str(education.get("school") or ""),
        str(education.get("degree") or ""),
        str(education.get("graduation") or ""),
    ]
    keyword_values = (
        skills
        + target_roles
        + education_parts
        + [str(personal.get("location") or "")]
        + [str(links.get("portfolio") or "")]
    )
    keywords = _unique_preserve_order(skills + target_roles + _extract_keywords_from_strings(keyword_values))
    return {
        "skills": skills,
        "target_roles": target_roles,
        "education_keywords": _extract_keywords_from_strings(education_parts),
        "keywords": keywords[:60],
    }


def calculate_skill_match_score(
    job_skills: list[str],
    user_skills: list[str],
    *,
    preferred_job_skills: list[str] | None = None,
) -> dict[str, Any]:
    required_skills = _unique_preserve_order(_canonicalize_skill(skill) for skill in job_skills)
    preferred_skills = _unique_preserve_order(_canonicalize_skill(skill) for skill in (preferred_job_skills or []))
    user_skill_set = _unique_preserve_order(_canonicalize_skill(skill) for skill in user_skills)

    if not required_skills and not preferred_skills:
        return {
            "score": 55.0,
            "evidence": ["No structured job skills were parsed, so CareerAgent used a neutral skill score."],
            "matched_required_skills": [],
            "matched_preferred_skills": [],
            "missing_required_skills": [],
            "missing_preferred_skills": [],
            "user_skills_detected": user_skill_set,
            "job_skills_detected": [],
        }

    user_lookup = {skill.casefold() for skill in user_skill_set}
    matched_required = [skill for skill in required_skills if skill.casefold() in user_lookup]
    matched_preferred = [skill for skill in preferred_skills if skill.casefold() in user_lookup]
    missing_required = [skill for skill in required_skills if skill.casefold() not in user_lookup]
    missing_preferred = [skill for skill in preferred_skills if skill.casefold() not in user_lookup]

    if required_skills and preferred_skills:
        score = (len(matched_required) / len(required_skills)) * 80 + (len(matched_preferred) / len(preferred_skills)) * 20
    elif required_skills:
        score = (len(matched_required) / len(required_skills)) * 100
    else:
        score = (len(matched_preferred) / len(preferred_skills)) * 100 if preferred_skills else 55

    evidence = [
        f"Matched {len(matched_required)} of {len(required_skills)} required skills and {len(matched_preferred)} of {len(preferred_skills)} preferred skills."
        if preferred_skills
        else f"Matched {len(matched_required)} of {len(required_skills)} parsed job skills."
    ]
    if matched_required:
        evidence.append(f"Matched required skills: {', '.join(matched_required[:8])}.")
    if matched_preferred:
        evidence.append(f"Matched preferred skills: {', '.join(matched_preferred[:8])}.")
    if missing_required:
        evidence.append(f"Missing required skills: {', '.join(missing_required[:8])}.")
    if missing_preferred:
        evidence.append(f"Missing preferred skills: {', '.join(missing_preferred[:8])}.")

    return {
        "score": _clamp_score(score),
        "evidence": evidence,
        "matched_required_skills": matched_required,
        "matched_preferred_skills": matched_preferred,
        "missing_required_skills": missing_required,
        "missing_preferred_skills": missing_preferred,
        "user_skills_detected": user_skill_set,
        "job_skills_detected": _unique_preserve_order(required_skills + preferred_skills),
    }


def calculate_role_match_score(
    job_role: str,
    target_roles: list[str],
    job_title: str,
    *,
    job_description: str = "",
) -> dict[str, Any]:
    canonical_job_role = _canonicalize_role(job_role or job_title)
    canonical_targets = _unique_preserve_order(_canonicalize_role(role) for role in target_roles)
    title_lower = (job_title or "").lower()
    description_lower = (job_description or "").lower()

    if not canonical_targets:
        return {
            "score": 60.0,
            "evidence": ["No target roles were set in the profile, so CareerAgent used a neutral role score."],
        }

    if canonical_job_role in canonical_targets:
        return {
            "score": 95.0,
            "evidence": [f"Job role {canonical_job_role} matches one of the user’s target roles directly."],
        }

    if any(target.lower() in title_lower for target in canonical_targets):
        return {
            "score": 90.0,
            "evidence": [f"Job title lines up closely with target role keywords: {', '.join(canonical_targets[:4])}."],
        }

    job_family = _find_role_family(canonical_job_role)
    target_families = {_find_role_family(role) for role in canonical_targets}
    target_families.discard(None)
    if job_family and job_family in target_families:
        return {
            "score": 80.0,
            "evidence": [f"Job role {canonical_job_role} is in the same role family as the user’s targets."],
        }

    if canonical_job_role == "Software Engineer" and any(
        family == "data" for family in target_families
    ) and any(keyword in f"{title_lower} {description_lower}" for keyword in ["data", "machine learning", "ml", "analytics"]):
        return {
            "score": 65.0,
            "evidence": [
                "The job is labeled Software Engineer, but the title/description still includes data or ML keywords."
            ],
        }

    return {
        "score": 40.0,
        "evidence": [f"Job role {canonical_job_role} is outside the user’s main target roles."],
    }


def calculate_location_score(job_location: str, remote_status: str, preferred_locations: list[str]) -> dict[str, Any]:
    normalized_location = _normalize_compare(job_location)
    normalized_remote = _normalize_compare(remote_status or "")
    normalized_preferences = [_normalize_compare(location) for location in preferred_locations if location]

    if not normalized_preferences:
        return {
            "score": 50.0,
            "evidence": ["No preferred locations were set in the profile, so CareerAgent used a neutral location score."],
        }

    if normalized_remote == "remote" and any("remote" == preference for preference in normalized_preferences):
        return {
            "score": 100.0,
            "evidence": ["The job is remote and Remote is in the user’s preferred locations."],
        }

    if not normalized_location or normalized_location == "unknown":
        return {
            "score": 50.0,
            "evidence": ["Job location is unknown, so CareerAgent used a neutral location score."],
        }

    for preference in normalized_preferences:
        if preference and (preference == normalized_location or preference in normalized_location or normalized_location in preference):
            return {
                "score": 100.0,
                "evidence": [f"Job location matches the preferred location {preference.title()} exactly or very closely."],
            }

        if preference == "bay area" and any(city in normalized_location for city in BAY_AREA_CITIES):
            score = 75.0 if normalized_remote == "hybrid" else 80.0
            evidence = "Hybrid role in the preferred Bay Area." if normalized_remote == "hybrid" else "Job location falls within the preferred Bay Area."
            return {"score": score, "evidence": [evidence]}

        if preference == "california" and (" california " in f" {normalized_location} " or re.search(r"\bca\b", normalized_location)):
            score = 75.0 if normalized_remote == "hybrid" else 80.0
            evidence = "Hybrid role in the preferred California region." if normalized_remote == "hybrid" else "Job location is in preferred California."
            return {"score": score, "evidence": [evidence]}

    return {
        "score": 40.0,
        "evidence": ["Job location does not appear in the user’s preferred locations, but it is still technically possible."],
    }


def calculate_experience_fit_score(job: Any, profile: dict[str, Any], resume_text: str) -> dict[str, Any]:
    seniority = _normalize_compare(str(getattr(job, "seniority_level", "") or ""))
    min_years = getattr(job, "years_experience_min", None)
    max_years = getattr(job, "years_experience_max", None)
    graduation_text = str((profile.get("education") or {}).get("graduation") or "")
    graduation_year = _parse_year_from_text(graduation_text)
    appears_new_grad = graduation_year is None or graduation_year >= _today().year - 1

    if seniority in {"internship", "new grad", "entry level"}:
        label = "Job appears entry level or internship aligned."
        score = 96.0 if appears_new_grad else 90.0
        return {"score": score, "evidence": [label]}

    if max_years is not None and max_years <= 2:
        return {
            "score": 90.0 if appears_new_grad else 85.0,
            "evidence": [f"Job asks for up to {max_years} years of experience, which fits an entry-level profile."],
        }

    if min_years is not None and min_years <= 2:
        return {
            "score": 88.0 if appears_new_grad else 82.0,
            "evidence": [f"Job asks for {min_years}+ years, which is still close to an entry-level target."],
        }

    if seniority == "senior" or (min_years is not None and min_years >= 5):
        return {
            "score": 30.0,
            "evidence": ["Job asks for senior-level experience that is likely above a new-grad or entry-level target."],
        }

    if (min_years is not None and min_years >= 3) or (max_years is not None and max_years >= 3):
        return {
            "score": 55.0,
            "evidence": ["Job asks for 3+ years of experience, which may be above the current target level."],
        }

    resume_indicates_experience = bool(re.search(r"\bexperience\b", resume_text, flags=re.IGNORECASE))
    if resume_indicates_experience:
        return {
            "score": 65.0,
            "evidence": ["Seniority is unclear, so CareerAgent used a moderate experience-fit score."],
        }

    return {
        "score": 60.0,
        "evidence": ["Seniority and years of experience were unclear, so CareerAgent used a neutral experience-fit score."],
    }


def calculate_profile_keyword_score(job: Any, profile_keywords: dict[str, Any], resume_keywords: dict[str, Any]) -> dict[str, Any]:
    job_strings = [
        str(getattr(job, "title", "") or ""),
        str(getattr(job, "role_category", "") or ""),
        str(getattr(job, "job_description", "") or ""),
        *list(getattr(job, "required_skills", []) or []),
        *list(getattr(job, "preferred_skills", []) or []),
    ]
    job_keywords = _unique_preserve_order(
        _extract_skills_from_text("\n".join(job_strings))
        + _extract_keywords_from_strings(job_strings)
    )[:20]
    user_keywords = _unique_preserve_order(
        list(profile_keywords.get("keywords") or [])
        + list(profile_keywords.get("skills") or [])
        + list(profile_keywords.get("target_roles") or [])
        + list(resume_keywords.get("keywords") or [])
        + list(resume_keywords.get("skills") or [])
        + list(resume_keywords.get("roles") or [])
    )

    if not job_keywords:
        return {
            "score": 50.0,
            "evidence": ["No strong parsed job keywords were available, so CareerAgent used a neutral keyword score."],
            "matched_keywords": [],
            "job_keywords": [],
            "user_keywords": user_keywords[:40],
        }

    user_lookup = {keyword.casefold() for keyword in user_keywords}
    matched_keywords = [keyword for keyword in job_keywords if keyword.casefold() in user_lookup]
    denominator = min(max(len(job_keywords), 1), 10)
    score = (len(matched_keywords) / denominator) * 100

    evidence = [f"Matched {len(matched_keywords)} of {denominator} tracked job keywords from the profile and resume."]
    if matched_keywords:
        evidence.append(f"Matched keywords: {', '.join(matched_keywords[:10])}.")
    else:
        evidence.append("No strong keyword overlap was found beyond general role signals.")

    return {
        "score": _clamp_score(score),
        "evidence": evidence,
        "matched_keywords": matched_keywords,
        "job_keywords": job_keywords,
        "user_keywords": user_keywords[:40],
    }


def freshness_score_value(posted_date: date | None, first_seen_date: date | None = None) -> float:
    reference_date = posted_date or first_seen_date
    age_days = _days_since(reference_date)
    if age_days is None:
        return 50.0
    if age_days <= 7:
        return 100.0
    if age_days <= 14:
        return 90.0
    if age_days <= 30:
        return 75.0
    if age_days <= 60:
        return 55.0
    if age_days <= 90:
        return 35.0
    return 20.0


def calculate_freshness_score(posted_date: date | None, first_seen_date: date | None = None) -> dict[str, Any]:
    reference_date = posted_date or first_seen_date
    age_days = _days_since(reference_date)
    source = "posted_date" if posted_date else "first_seen_date" if first_seen_date else "unknown"
    score = freshness_score_value(posted_date, first_seen_date)

    if age_days is None:
        evidence = ["Job age is unknown, so CareerAgent used a neutral freshness score."]
    elif age_days <= 7:
        evidence = [f"Job looks very fresh at about {age_days} days old."]
    elif age_days <= 14:
        evidence = [f"Job is still fairly recent at about {age_days} days old."]
    elif age_days <= 30:
        evidence = [f"Job is a few weeks old at about {age_days} days old."]
    elif age_days <= 60:
        evidence = [f"Job is getting older at about {age_days} days old."]
    elif age_days <= 90:
        evidence = [f"Job may be stale at about {age_days} days old."]
    else:
        evidence = [f"Job appears quite old at about {age_days} days old."]

    return {
        "score": score,
        "evidence": evidence,
        "days_old": age_days,
        "age_source": source,
    }


def calculate_application_ease_score(job: Any) -> dict[str, Any]:
    url = str(getattr(job, "url", "") or "").strip()
    verification_status = str(getattr(job, "verification_status", "unknown") or "unknown")

    if not url:
        return {
            "score": 35.0,
            "evidence": ["No job URL is stored, so the application path may be harder to reopen later."],
        }

    if verification_status in {"closed", "likely_closed"}:
        return {
            "score": 20.0,
            "evidence": ["Job looks closed or likely closed, so application ease is very low."],
        }

    if verification_status == "possibly_closed":
        return {
            "score": 40.0,
            "evidence": ["Job URL exists, but verification suggests the posting may be unstable or partially closed."],
        }

    if verification_status == "unknown":
        return {
            "score": 55.0,
            "evidence": ["Job URL exists, but the posting has not been confidently verified yet."],
        }

    return {
        "score": 70.0,
        "evidence": ["Job URL exists and the posting does not currently look closed, so applying should be straightforward."],
    }


def calculate_resume_match_score(component_scores: dict[str, float]) -> float:
    score = (
        0.45 * float(component_scores.get("skill_match_score", 0.0))
        + 0.25 * float(component_scores.get("role_match_score", 0.0))
        + 0.15 * float(component_scores.get("experience_fit_score", 0.0))
        + 0.15 * float(component_scores.get("profile_keyword_score", 0.0))
    )
    return _clamp_score(score)


def calculate_priority_score(
    *,
    resume_match_score: float,
    verification_score: float,
    freshness_score: float,
    location_score: float,
    application_ease_score: float,
) -> float:
    score = (
        0.40 * float(resume_match_score)
        + 0.25 * float(verification_score)
        + 0.20 * float(freshness_score)
        + 0.10 * float(location_score)
        + 0.05 * float(application_ease_score)
    )
    return _clamp_score(score)


def calculate_overall_priority_score(component_scores: dict[str, float]) -> float:
    return calculate_priority_score(
        resume_match_score=float(component_scores.get("resume_match_score", 0.0)),
        verification_score=float(component_scores.get("verification_score", 0.0)),
        freshness_score=float(component_scores.get("freshness_score", 50.0)),
        location_score=float(component_scores.get("location_score", 50.0)),
        application_ease_score=float(component_scores.get("application_ease_score", 50.0)),
    )


def score_job_against_profile(job: Any, profile: dict[str, Any], resume_text: str) -> dict[str, Any]:
    profile_keywords = extract_profile_keywords(profile)
    resume_keywords = extract_resume_keywords(resume_text)
    user_skills = _unique_preserve_order(list(profile_keywords.get("skills") or []) + list(resume_keywords.get("skills") or []))

    required_skills = list(getattr(job, "required_skills", []) or [])
    preferred_skills = list(getattr(job, "preferred_skills", []) or [])
    if not required_skills and getattr(job, "job_description", ""):
        fallback_skills = _extract_skills_from_text(str(getattr(job, "job_description", "")))
        required_skills = fallback_skills

    skill_result = calculate_skill_match_score(required_skills, user_skills, preferred_job_skills=preferred_skills)
    role_result = calculate_role_match_score(
        str(getattr(job, "role_category", "") or ""),
        list(profile.get("target_roles") or []),
        str(getattr(job, "title", "") or ""),
        job_description=str(getattr(job, "job_description", "") or ""),
    )
    location_result = calculate_location_score(
        str(getattr(job, "location", "") or ""),
        str(getattr(job, "remote_status", "") or ""),
        list(((profile.get("application_defaults") or {}).get("preferred_locations") or [])),
    )
    experience_result = calculate_experience_fit_score(job, profile, resume_text)
    keyword_result = calculate_profile_keyword_score(job, profile_keywords, resume_keywords)
    freshness_result = calculate_freshness_score(getattr(job, "posted_date", None), getattr(job, "first_seen_date", None))
    application_ease_result = calculate_application_ease_score(job)

    component_scores = {
        "skill_match_score": skill_result["score"],
        "role_match_score": role_result["score"],
        "experience_fit_score": experience_result["score"],
        "profile_keyword_score": keyword_result["score"],
    }
    resume_match_score = calculate_resume_match_score(component_scores)
    overall_priority_score = calculate_overall_priority_score(
        {
            "resume_match_score": resume_match_score,
            "verification_score": float(getattr(job, "verification_score", 0.0) or 0.0),
            "freshness_score": freshness_result["score"],
            "location_score": location_result["score"],
            "application_ease_score": application_ease_result["score"],
        }
    )

    summary = [
        f"Resume match scored {resume_match_score}/100 based on skills, role fit, experience fit, and profile keywords.",
        f"Overall priority scored {overall_priority_score}/100 after blending fit, verification, freshness, location fit, and application ease.",
    ]
    if skill_result["matched_required_skills"] or skill_result["matched_preferred_skills"]:
        matched = skill_result["matched_required_skills"] + skill_result["matched_preferred_skills"]
        summary.append(f"Top matched skills: {', '.join(_unique_preserve_order(matched)[:6])}.")
    if skill_result["missing_required_skills"]:
        summary.append(f"Main missing required skills: {', '.join(skill_result['missing_required_skills'][:4])}.")
    summary.append(role_result["evidence"][0])
    summary.append(location_result["evidence"][0])
    summary.append(experience_result["evidence"][0])
    summary.append(freshness_result["evidence"][0])

    return {
        "skill_match_score": skill_result["score"],
        "role_match_score": role_result["score"],
        "experience_fit_score": experience_result["score"],
        "profile_keyword_score": keyword_result["score"],
        "resume_match_score": resume_match_score,
        "freshness_score": freshness_result["score"],
        "location_score": location_result["score"],
        "application_ease_score": application_ease_result["score"],
        "verification_score": float(getattr(job, "verification_score", 0.0) or 0.0),
        "overall_priority_score": overall_priority_score,
        "scoring_status": "scored",
        "scored_at": datetime.now(timezone.utc),
        "evidence": _unique_preserve_order(summary),
        "scoring_evidence": {
            "summary": _unique_preserve_order(summary),
            "skill_match": skill_result,
            "role_match": role_result,
            "experience_fit": experience_result,
            "profile_keyword": keyword_result,
            "freshness": freshness_result,
            "location": location_result,
            "application_ease": application_ease_result,
        },
        "scoring_raw_data": {
            "user_skills_detected": user_skills,
            "job_skills_detected": skill_result["job_skills_detected"],
            "profile_keywords_used": list(profile_keywords.get("keywords") or []),
            "resume_keywords_used": list(resume_keywords.get("keywords") or []),
            "matched_required_skills": skill_result["matched_required_skills"],
            "matched_preferred_skills": skill_result["matched_preferred_skills"],
            "missing_required_skills": skill_result["missing_required_skills"],
            "missing_preferred_skills": skill_result["missing_preferred_skills"],
            "matched_keywords": keyword_result.get("matched_keywords", []),
            "job_keywords": keyword_result.get("job_keywords", []),
            "recommendation_reasons": _unique_preserve_order(summary)[:6],
        },
    }


def score_saved_job(job: Any) -> dict[str, Any]:
    profile_document = load_profile_document()
    resume_document = load_resume_document()
    result = score_job_against_profile(job, profile_document["profile"], resume_document["content"])
    scoring_raw_data = dict(result.get("scoring_raw_data") or {})
    scoring_raw_data.update(
        {
            "profile_source": profile_document["source"],
            "profile_path": profile_document["path"],
            "resume_source": resume_document["source"],
            "resume_path": resume_document["path"],
        }
    )
    result["scoring_raw_data"] = scoring_raw_data
    return result


def build_job_scoring_updates(scoring_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "skill_match_score": float(scoring_result.get("skill_match_score", 0.0)),
        "role_match_score": float(scoring_result.get("role_match_score", 0.0)),
        "experience_fit_score": float(scoring_result.get("experience_fit_score", 0.0)),
        "profile_keyword_score": float(scoring_result.get("profile_keyword_score", 0.0)),
        "resume_match_score": float(scoring_result.get("resume_match_score", 0.0)),
        "freshness_score": float(scoring_result.get("freshness_score", 50.0)),
        "location_score": float(scoring_result.get("location_score", 50.0)),
        "application_ease_score": float(scoring_result.get("application_ease_score", 50.0)),
        "overall_priority_score": float(scoring_result.get("overall_priority_score", 0.0)),
        "scoring_status": str(scoring_result.get("scoring_status") or "unscored"),
        "scoring_evidence": dict(scoring_result.get("scoring_evidence") or {}),
        "scoring_raw_data": dict(scoring_result.get("scoring_raw_data") or {}),
        "scored_at": scoring_result.get("scored_at"),
    }
