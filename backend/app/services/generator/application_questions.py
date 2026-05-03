from __future__ import annotations

from typing import Any

from .common import collect_relevant_skills, profile_education_summary, profile_links, unique_preserve_order


def _bool_answer(value: bool | None) -> str:
    if value is None:
        return "REVIEW MANUALLY."
    return "Yes." if value else "No."


def _salary_answer(profile: dict[str, Any]) -> str:
    question_policy = profile.get("question_policy") or {}
    application_defaults = profile.get("application_defaults") or {}
    salary_policy = str(question_policy.get("answer_salary_expectation") or "").strip().lower()
    explicit_salary = (
        application_defaults.get("expected_salary")
        or application_defaults.get("salary_expectation")
        or application_defaults.get("salary_range")
    )

    if explicit_salary and salary_policy not in {"draft_only", "review_required"}:
        return f"{explicit_salary}"

    return (
        "REVIEW MANUALLY. Draft: I'm open to discussing compensation based on the scope of the role, level, and location."
    )


def _portfolio_answer(profile: dict[str, Any]) -> str:
    links = profile_links(profile)
    available = [value for value in [links["portfolio"], links["github"], links["linkedin"]] if value]
    if not available:
        return "REVIEW MANUALLY. Add the most relevant portfolio, GitHub, or LinkedIn link."
    return "\n".join(f"- {value}" for value in available)


def _about_answer(job: Any, profile: dict[str, Any], scoring_evidence: dict[str, Any] | None) -> str:
    education_summary = profile_education_summary(profile)
    relevant_skills = collect_relevant_skills(job, profile, scoring_evidence)[:4]
    parts: list[str] = []
    if education_summary:
        parts.append(f"I'm currently focused on {education_summary}.")
    if relevant_skills:
        parts.append(
            f"The parts of my existing background that line up most closely with this role are {', '.join(relevant_skills)}."
        )
    parts.append("I would review this draft and make it more specific before submitting it anywhere.")
    return " ".join(parts)


def _company_interest_answer(job: Any, profile: dict[str, Any], scoring_evidence: dict[str, Any] | None) -> str:
    company = str(getattr(job, "company", "") or "your company").strip()
    title = str(getattr(job, "title", "") or "this role").strip()
    relevant_skills = collect_relevant_skills(job, profile, scoring_evidence)[:3]

    reasons = [f"I'm interested in {company} because the {title} role overlaps with the work I want to keep doing."]
    if relevant_skills:
        reasons.append(f"My current materials show overlap in {', '.join(relevant_skills)}.")
    reasons.append("I would still review the company mission and team context manually before using this answer.")
    return " ".join(reasons)


def _demographic_answer(profile: dict[str, Any]) -> str:
    question_policy = profile.get("question_policy") or {}
    policy = str(question_policy.get("answer_demographic_questions") or "prefer_not_to_answer").strip()
    if policy:
        return policy.replace("_", " ").capitalize() + "."
    return "Prefer not to answer."


def _answer_question(question: str, job: Any, profile: dict[str, Any], scoring_evidence: dict[str, Any] | None) -> str:
    normalized = question.strip().lower()
    question_policy = profile.get("question_policy") or {}
    application_defaults = profile.get("application_defaults") or {}

    if "authorized" in normalized and "work" in normalized and "u.s" in normalized:
        if not question_policy.get("answer_work_authorization", True):
            return "REVIEW MANUALLY."
        return _bool_answer(application_defaults.get("work_authorized_us"))

    if "sponsorship" in normalized or "sponsor" in normalized or "visa" in normalized:
        if not question_policy.get("answer_sponsorship", True):
            return "REVIEW MANUALLY."
        if "future" in normalized:
            return _bool_answer(application_defaults.get("need_sponsorship_future"))
        if "now" in normalized or "currently" in normalized:
            return _bool_answer(application_defaults.get("need_sponsorship_now"))
        now_value = application_defaults.get("need_sponsorship_now")
        future_value = application_defaults.get("need_sponsorship_future")
        if now_value is None or future_value is None:
            return "REVIEW MANUALLY."
        if now_value or future_value:
            return "Yes. REVIEW MANUALLY to make sure the exact timing is described correctly."
        return "No."

    if "relocate" in normalized:
        if not question_policy.get("answer_relocation", True):
            return "REVIEW MANUALLY."
        return _bool_answer(application_defaults.get("willing_to_relocate"))

    if "salary" in normalized or "compensation" in normalized or "pay range" in normalized:
        return _salary_answer(profile)

    if "portfolio" in normalized or "github" in normalized or "linkedin" in normalized or "website" in normalized:
        return _portfolio_answer(profile)

    if "tell us about yourself" in normalized or "introduce yourself" in normalized:
        return _about_answer(job, profile, scoring_evidence)

    if "why are you interested" in normalized or "why do you want" in normalized:
        return _company_interest_answer(job, profile, scoring_evidence)

    if "gender" in normalized or "race" in normalized or "ethnicity" in normalized or "veteran" in normalized or "disability" in normalized:
        return _demographic_answer(profile)

    return "REVIEW MANUALLY. Draft a truthful answer that stays within your real experience and the materials already in CareerAgent."


def generate_application_question_answers(job: Any, profile: dict, scoring_evidence: dict | None = None) -> str:
    parsed_questions = list(getattr(job, "application_questions", None) or [])
    common_questions = [
        "Why are you interested in this company?",
        "Tell us about yourself.",
        "Are you authorized to work in the U.S.?",
        "Do you need sponsorship now or in the future?",
        "Are you willing to relocate?",
        "Expected salary?",
        "Portfolio/GitHub/LinkedIn?",
        "EEO or demographic questions",
    ]
    questions = unique_preserve_order(parsed_questions + common_questions)

    lines = [
        "# Application Question Drafts",
        "",
        "CareerAgent Stage 6 draft answers. Sensitive or uncertain answers are marked REVIEW MANUALLY.",
        "",
    ]

    for index, question in enumerate(questions, start=1):
        lines.extend(
            [
                f"## Question {index}",
                f"Prompt: {question}",
                "",
                _answer_question(question, job, profile, scoring_evidence),
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"
