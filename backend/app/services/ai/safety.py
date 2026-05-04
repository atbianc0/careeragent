from __future__ import annotations

import json
import re
from typing import Any


REVIEW_REQUIRED_NOTICE = "AI draft. Review manually before using."

RISKY_PATTERNS = [
    (re.compile(r"\b\d+\+?\s+years? of experience\b", re.IGNORECASE), "Contains a years-of-experience claim that may not be supported."),
    (re.compile(r"\b(improved|increased|reduced|grew|saved)\b[^.\n]{0,40}\b\d+%|\b\d+%\b", re.IGNORECASE), "Contains a metric or percentage claim that may not be supported."),
    (re.compile(r"\bexpert in\b|\bworld[- ]class\b|\bleading expert\b", re.IGNORECASE), "Contains exaggerated expertise language that may not be supported."),
    (re.compile(r"\bauthorized to work\b|\bsponsorship\b|\bvisa\b", re.IGNORECASE), "Contains work authorization or sponsorship language that must come from profile settings."),
    (re.compile(r"\b(ssn|social security|date of birth)\b", re.IGNORECASE), "Contains sensitive identity content that should not be generated automatically."),
]


def sanitize_ai_output(output: str) -> str:
    cleaned = str(output or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()


def add_review_required_notice(output: str) -> str:
    cleaned = sanitize_ai_output(output)
    if REVIEW_REQUIRED_NOTICE.lower() in cleaned.lower():
        return cleaned
    if not cleaned:
        return REVIEW_REQUIRED_NOTICE
    return f"{REVIEW_REQUIRED_NOTICE}\n\n{cleaned}"


def detect_risky_claims(output: str) -> list[str]:
    cleaned = sanitize_ai_output(output)
    warnings: list[str] = []
    for pattern, message in RISKY_PATTERNS:
        if pattern.search(cleaned):
            warnings.append(message)
    return warnings


def check_no_unsupported_claims(output: str, profile: dict[str, Any], resume_text: str) -> dict[str, Any]:
    cleaned = sanitize_ai_output(output)
    support_haystack = " ".join(
        [
            json.dumps(profile or {}, sort_keys=True, default=str),
            str(resume_text or ""),
        ]
    ).lower()

    warnings = detect_risky_claims(cleaned)

    for years_match in re.findall(r"\b\d+\+?\s+years?\b", cleaned, flags=re.IGNORECASE):
        if years_match.lower() not in support_haystack:
            warnings.append(f"Potential unsupported experience-duration claim detected: '{years_match}'.")

    for metric_match in re.findall(r"\b\d+%\b", cleaned):
        if metric_match.lower() not in support_haystack:
            warnings.append(f"Potential unsupported metric claim detected: '{metric_match}'.")

    normalized_cleaned = cleaned.lower()
    if ("authorized to work" in normalized_cleaned or "sponsorship" in normalized_cleaned) and "application_defaults" not in support_haystack:
        warnings.append("Work authorization or sponsorship language was generated without clear profile support.")

    unique_warnings: list[str] = []
    seen: set[str] = set()
    for warning in warnings:
        if warning not in seen:
            seen.add(warning)
            unique_warnings.append(warning)

    return {
        "safe": not unique_warnings,
        "warnings": unique_warnings,
        "safety_notes": [
            "AI output is a draft and requires manual review.",
            "CareerAgent should not invent experience, skills, credentials, companies, dates, metrics, or authorization facts.",
        ],
        "content": add_review_required_notice(cleaned),
    }
