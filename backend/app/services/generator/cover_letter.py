from __future__ import annotations

from typing import Any

from .common import build_role_company_label, collect_relevant_skills, profile_education_summary, profile_name, writing_tone


def generate_cover_letter(
    job: Any,
    profile: dict,
    resume_text: str,
    scoring_evidence: dict | None = None,
) -> str:
    del resume_text

    role_company = build_role_company_label(job)
    company = str(getattr(job, "company", "") or "").strip()
    title = str(getattr(job, "title", "") or "").strip()
    relevant_skills = collect_relevant_skills(job, profile, scoring_evidence)[:4]
    tone = writing_tone(profile)
    education_summary = profile_education_summary(profile)
    signer_name = profile_name(profile) or "[Your Name]"

    opener = "Dear Hiring Team,"
    if company and company.lower() != "unknown company":
        opener = f"Dear {company} team,"

    intro_parts = [f"I'm interested in the {title or 'role'}"]
    if company and company.lower() != "unknown company":
        intro_parts.append(f"at {company}")
    intro_sentence = " ".join(intro_parts) + "."

    background_bits: list[str] = []
    if education_summary:
        background_bits.append(f"My current background includes {education_summary}.")
    if relevant_skills:
        background_bits.append(
            f"The parts of my existing resume that line up most closely with this job are {', '.join(relevant_skills)}."
        )
    else:
        background_bits.append("I would review the attached resume closely and tailor the final wording before applying.")

    fit_sentence = (
        "This draft stays conservative on purpose: it only emphasizes skills and experience already reflected in my existing profile and resume."
    )
    close_sentence = (
        "If the role is still open, I'd be glad to discuss whether my current background could be a good fit."
    )

    return "\n".join(
        [
            "# Cover Letter Draft",
            "",
            f"CareerAgent Stage 6 draft. Tone target from profile: {tone}. Review and edit manually before using.",
            "",
            opener,
            "",
            intro_sentence,
            " ".join(background_bits),
            fit_sentence,
            close_sentence,
            "",
            "Thank you for your time,",
            signer_name,
            "",
            f"Target job: {role_company}",
            "Safety note: no experience, skills, dates, titles, companies, or metrics were invented in this draft.",
        ]
    )
