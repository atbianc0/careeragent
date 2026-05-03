from __future__ import annotations

from typing import Any

from .common import collect_relevant_skills, profile_name


def generate_recruiter_message(job: Any, profile: dict, scoring_evidence: dict | None = None) -> str:
    company = str(getattr(job, "company", "") or "your team").strip()
    title = str(getattr(job, "title", "") or "the role").strip()
    relevant_skills = collect_relevant_skills(job, profile, scoring_evidence)[:2]
    signer_name = profile_name(profile) or "[Your Name]"

    skill_sentence = ""
    if relevant_skills:
        skill_sentence = f" The strongest overlap in my current background is {', '.join(relevant_skills)}."

    return "\n".join(
        [
            "# Recruiter Message Draft",
            "",
            f"Hi {company} team,",
            "",
            f"I'm planning to apply for the {title} role and wanted to reach out briefly.{skill_sentence}",
            "If the position is still active, I'd appreciate any guidance on what the team is prioritizing in candidates.",
            "",
            f"Thanks,",
            signer_name,
            "",
            "Safety note: this is a reviewable draft and does not claim that the user has already applied.",
        ]
    )
