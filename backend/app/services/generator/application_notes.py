from __future__ import annotations

from typing import Any

from .common import collect_missing_skills


def _recommendation_sentence(job: Any) -> str:
    priority_score = float(getattr(job, "overall_priority_score", 0.0) or 0.0)
    verification_status = str(getattr(job, "verification_status", "unknown") or "unknown")

    if verification_status in {"closed", "likely_closed"}:
        return "This job is a lower-priority target right now because the verification signals suggest it may no longer be active."
    if priority_score >= 75:
        return "This job looks like a strong next application target based on the current match, freshness, and verification signals."
    if priority_score >= 55:
        return "This job looks worth reviewing, but the final decision should depend on manual review of the posting and the generated packet."
    return "This job is likely a backup option unless manual review reveals a stronger fit than the current scoring suggests."


def generate_application_notes(job: Any, profile: dict, scoring_evidence: dict | None = None) -> str:
    del profile, scoring_evidence

    missing_skills = collect_missing_skills(job)
    verification_evidence = list(getattr(job, "verification_evidence", None) or [])
    recommendation_reasons = list((dict(getattr(job, "scoring_raw_data", None) or {})).get("recommendation_reasons") or [])

    lines = [
        "# Application Notes",
        "",
        "## Job Snapshot",
        f"- Title: {getattr(job, 'title', 'Unknown Title') or 'Unknown Title'}",
        f"- Company: {getattr(job, 'company', 'Unknown Company') or 'Unknown Company'}",
        f"- Location: {getattr(job, 'location', 'Unknown') or 'Unknown'}",
        f"- URL: {getattr(job, 'url', '') or 'No URL stored'}",
        "",
        "## Verification Summary",
        f"- Status: {getattr(job, 'verification_status', 'unknown') or 'unknown'}",
        f"- Verification score: {float(getattr(job, 'verification_score', 0.0) or 0.0):.2f}",
        f"- Likely closed score: {float(getattr(job, 'likely_closed_score', 0.0) or 0.0):.2f}",
    ]

    if verification_evidence:
        lines.append("- Evidence summary:")
        lines.extend(f"  - {item}" for item in verification_evidence[:5])
    else:
        lines.append("- Evidence summary: No verification evidence has been saved yet.")

    lines.extend(
        [
            "",
            "## Match Summary",
            f"- Resume match score: {float(getattr(job, 'resume_match_score', 0.0) or 0.0):.2f}",
            f"- Overall priority score: {float(getattr(job, 'overall_priority_score', 0.0) or 0.0):.2f}",
            f"- Role category: {getattr(job, 'role_category', '') or 'Unknown'}",
        ]
    )

    if recommendation_reasons:
        lines.append("- Current recommendation reasons:")
        lines.extend(f"  - {item}" for item in recommendation_reasons[:5])

    if missing_skills:
        lines.append(f"- Missing skills to consider: {', '.join(missing_skills[:6])}")
    else:
        lines.append("- Missing skills to consider: none surfaced by the current scoring output.")

    lines.extend(
        [
            "",
            "## Recommendation",
            _recommendation_sentence(job),
            "",
            "## Suggested Next Action",
            "Review the generated resume, cover letter, and draft answers together, then decide whether to apply manually.",
            "",
            "## Manual Review Checklist",
            "- [ ] Review resume",
            "- [ ] Review cover letter",
            "- [ ] Review work authorization answers",
            "- [ ] Review salary answer",
            "- [ ] Review demographic questions",
            "- [ ] Manually submit application",
            "- [ ] Mark applied in CareerAgent later",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"
