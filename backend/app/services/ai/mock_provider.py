from __future__ import annotations

from typing import Any

from .base import AIProvider


def _context_job(context: dict[str, Any] | None) -> dict[str, Any]:
    return dict((context or {}).get("job") or {})


def _context_profile(context: dict[str, Any] | None) -> dict[str, Any]:
    return dict((context or {}).get("profile") or {})


def _profile_name(profile: dict[str, Any]) -> str:
    personal = dict(profile.get("personal") or {})
    return str(personal.get("name") or "[Your Name]").strip()


def _relevant_skills(job: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    job_skills = [str(skill).strip() for skill in list(job.get("required_skills") or []) + list(job.get("preferred_skills") or [])]
    profile_skills = [str(skill).strip() for skill in list(profile.get("skills") or [])]
    matches: list[str] = []
    profile_lookup = {skill.casefold() for skill in profile_skills if skill}
    for skill in job_skills:
        if skill and skill.casefold() in profile_lookup and skill not in matches:
            matches.append(skill)
    if matches:
        return matches[:4]
    return [skill for skill in profile_skills if skill][:4]


def _build_mock_text(task: str, context: dict[str, Any] | None) -> str:
    job = _context_job(context)
    profile = _context_profile(context)
    company = str(job.get("company") or "the company").strip()
    title = str(job.get("title") or "the role").strip()
    signer_name = _profile_name(profile)
    skills = _relevant_skills(job, profile)
    skill_sentence = f" Existing materials show overlap in {', '.join(skills[:3])}." if skills else ""

    if task == "cover_letter":
        return "\n".join(
            [
                "# AI Draft Cover Letter",
                "",
                "MockProvider draft. Review manually before using.",
                "",
                f"Dear {company} team,",
                "",
                f"I'm interested in the {title}.{skill_sentence}",
                "This AI-assisted draft stays conservative and should only reflect experience already present in your profile and resume.",
                "Please review and edit this before using it in any application.",
                "",
                "Thank you,",
                signer_name,
            ]
        )
    if task == "recruiter_message":
        return "\n".join(
            [
                "# AI Draft Recruiter Message",
                "",
                f"Hi {company} team,",
                "",
                f"I'm preparing an application for the {title}.{skill_sentence} I'd appreciate any guidance on what the team is prioritizing.",
                "",
                f"Thanks,",
                signer_name,
            ]
        )
    if task == "application_questions":
        return "\n".join(
            [
                "# AI Draft Application Answers",
                "",
                "MockProvider draft. Review manually before using.",
                "",
                "Why are you interested in this company?",
                f"- I'm interested in {company} because the {title} aligns with the work I want to keep doing.{skill_sentence}",
                "",
                "Tell us about yourself.",
                "- REVIEW MANUALLY. Keep this grounded in your real resume and profile.",
            ]
        )
    if task == "market_insights":
        dashboard = dict((context or {}).get("market_data") or {})
        pipeline = dict(dashboard.get("pipeline_summary") or {})
        total_jobs = int(pipeline.get("total_jobs") or 0)
        applied_jobs = int(pipeline.get("applied_jobs") or 0)
        return "\n".join(
            [
                "MockProvider market insight draft:",
                f"- You currently have {total_jobs} saved jobs in CareerAgent.",
                f"- You have marked {applied_jobs} jobs as applied so far.",
                "- Treat this as a draft summary of stored data, not a prediction.",
            ]
        )
    if task == "resume_tailor":
        return "\n".join(
            [
                "MockProvider resume tailoring suggestions:",
                "- Emphasize already-supported skills that overlap with the job requirements.",
                "- Preserve the current LaTeX structure and only make content-only edits.",
                "- Mark any uncertain wording for manual review instead of inventing details.",
            ]
        )
    return f"MockProvider draft for task '{task}'. Review manually before using."


class MockProvider(AIProvider):
    name = "mock"

    def is_available(self) -> bool:
        return True

    def generate_text(self, task: str, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        del prompt
        return self.build_result(
            success=True,
            task=task,
            content=_build_mock_text(task, context),
            warnings=["MockProvider is active. This is a deterministic placeholder, not a live external AI response."],
            safety_notes=["Review manually before using any AI-assisted output."],
            raw=None,
        )

    def parse_json(self, task: str, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        del prompt
        fallback_json = (context or {}).get("fallback_json")
        if isinstance(fallback_json, dict):
            parsed_json = dict(fallback_json)
        elif isinstance(fallback_json, list):
            parsed_json = list(fallback_json)
        else:
            parsed_json = {
                "status": "mock_placeholder",
                "note": "MockProvider returned a deterministic placeholder JSON payload.",
            }
        return self.build_result(
            success=True,
            task=task,
            content="",
            parsed_json=parsed_json,
            warnings=["MockProvider returned deterministic structured output. No external AI request was made."],
            safety_notes=["Review structured AI output before trusting it."],
            raw=None,
        )
