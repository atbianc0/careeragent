from __future__ import annotations

import json
from typing import Any


def _safe_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=str)


def _shared_safety_rules() -> str:
    return "\n".join(
        [
            "Safety rules:",
            "- Do not invent facts, experience, skills, credentials, companies, dates, titles, metrics, or work authorization details.",
            "- Use only the provided profile, resume, job, and scoring data.",
            "- If something is uncertain, say REVIEW MANUALLY or leave it unknown.",
            "- Keep outputs direct, reviewable, and easy for a human to edit.",
        ]
    )


def build_job_parse_prompt(job_text: str) -> str:
    return "\n\n".join(
        [
            "Parse the following job description into structured JSON.",
            _shared_safety_rules(),
            "Return keys: company, title, location, employment_type, remote_status, role_category, seniority_level, years_experience_min, years_experience_max, salary_min, salary_max, salary_currency, required_skills, preferred_skills, responsibilities, requirements, education_requirements, application_questions.",
            "Use null, empty strings, or empty arrays when the data is not clearly present.",
            "Job text:",
            job_text,
        ]
    )


def build_resume_tailor_prompt(
    base_resume_tex: str,
    job: Any,
    profile: dict[str, Any],
    scoring_evidence: dict[str, Any] | None,
) -> str:
    return "\n\n".join(
        [
            "Suggest conservative content-only resume tailoring ideas for the provided job.",
            _shared_safety_rules(),
            "Do not redesign the resume. Preserve the LaTeX structure, commands, spacing, fonts, margins, and section order.",
            "Return short bullet suggestions only. Focus on truthful emphasis and skill ordering, not template replacement.",
            "Job:",
            _safe_json(
                {
                    "company": getattr(job, "company", None),
                    "title": getattr(job, "title", None),
                    "location": getattr(job, "location", None),
                    "required_skills": getattr(job, "required_skills", None),
                    "preferred_skills": getattr(job, "preferred_skills", None),
                }
            ),
            "Profile:",
            _safe_json(profile),
            "Scoring evidence:",
            _safe_json(scoring_evidence or {}),
            "Base resume source:",
            base_resume_tex,
        ]
    )


def build_cover_letter_prompt(job: Any, profile: dict[str, Any], resume_text: str, scoring_evidence: dict[str, Any] | None) -> str:
    return "\n\n".join(
        [
            "Draft a short, direct cover letter for the user.",
            _shared_safety_rules(),
            "Use the user's writing style when available. Keep the tone simple, honest, and specific to the job when possible.",
            "Mark uncertain content as REVIEW MANUALLY.",
            "Job:",
            _safe_json(
                {
                    "company": getattr(job, "company", None),
                    "title": getattr(job, "title", None),
                    "location": getattr(job, "location", None),
                    "required_skills": getattr(job, "required_skills", None),
                    "preferred_skills": getattr(job, "preferred_skills", None),
                }
            ),
            "Profile:",
            _safe_json(profile),
            "Scoring evidence:",
            _safe_json(scoring_evidence or {}),
            "Resume text:",
            resume_text,
        ]
    )


def build_recruiter_message_prompt(job: Any, profile: dict[str, Any], scoring_evidence: dict[str, Any] | None) -> str:
    return "\n\n".join(
        [
            "Draft a short recruiter outreach message.",
            _shared_safety_rules(),
            "Keep it concise and reviewable. Do not claim the user has already applied unless that fact is explicitly provided.",
            "Job:",
            _safe_json(
                {
                    "company": getattr(job, "company", None),
                    "title": getattr(job, "title", None),
                    "required_skills": getattr(job, "required_skills", None),
                }
            ),
            "Profile:",
            _safe_json(profile),
            "Scoring evidence:",
            _safe_json(scoring_evidence or {}),
        ]
    )


def build_application_questions_prompt(job: Any, profile: dict[str, Any], scoring_evidence: dict[str, Any] | None) -> str:
    return "\n\n".join(
        [
            "Draft truthful answers to common job-application questions.",
            _shared_safety_rules(),
            "Work authorization and sponsorship answers must come only from profile.application_defaults.",
            "Sensitive or uncertain answers should say REVIEW MANUALLY.",
            "Job:",
            _safe_json(
                {
                    "company": getattr(job, "company", None),
                    "title": getattr(job, "title", None),
                    "application_questions": getattr(job, "application_questions", None),
                }
            ),
            "Profile:",
            _safe_json(profile),
            "Scoring evidence:",
            _safe_json(scoring_evidence or {}),
        ]
    )


def build_market_insights_prompt(market_data: dict[str, Any]) -> str:
    return "\n\n".join(
        [
            "Summarize the user's observed job-market and application trends.",
            _shared_safety_rules(),
            "Do not claim prediction, causation, or 'best time to apply'. Use only observed historical data.",
            "If the sample size is small, say so explicitly.",
            "Return 3 to 6 short actionable insights.",
            "Market dashboard data:",
            _safe_json(market_data),
        ]
    )
