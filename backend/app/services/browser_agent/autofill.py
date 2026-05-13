from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import re
from urllib.parse import urlparse, urlunparse
from typing import Any, Iterator

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_packet import ApplicationPacket
from app.models.job import Job
from app.services.ai import get_ai_provider, require_ai_allowed
from app.services.profile.profile_store import load_profile_document
from app.services.resume import compile_latex_file, load_resume_document
from app.services.tracker import log_event, promote_job_status_if_needed

from .field_detector import LONG_ANSWER_FIELD_KEYS, SENSITIVE_FIELD_KEYS, detect_form_fields
from .safe_actions import BLOCKED_FINAL_SUBMIT_WORDS, should_block_element
from .session_store import (
    cleanup_closed_sessions,
    cleanup_expired_sessions,
    create_session,
    get_recent_session_summaries,
    list_sessions,
    save_session_summary,
)

HIGH_CONFIDENCE_THRESHOLD = 0.8
SENSITIVE_OPTIONAL_FIELD_KEYS = {"race_ethnicity", "gender", "disability", "veteran_status"}
SKIPPED_ALWAYS_FIELD_KEYS = {"ssn", "date_of_birth", "unknown_sensitive"}
DEFAULT_REVIEW_MESSAGE = "Browser opened and filled. Finish missing fields and submit manually."
VISIBLE_SESSION_MESSAGE = (
    "Visible browser is open. CareerAgent filled safe fields and stopped before submit. "
    "Finish missing fields manually and submit yourself."
)
HEADLESS_REVIEW_MESSAGE = (
    "CareerAgent filled fields in a headless browser. Because this browser is not visible, you cannot continue from "
    "this session. Use visible browser mode for real applications, or open the job in your default browser and manually apply."
)
HEADED_REVIEW_MESSAGE = (
    "Visible browser autofill is running in a headed Chromium window. CareerAgent will stop before final actions so you can "
    "continue reviewing manually."
)
VISIBLE_UNAVAILABLE_MESSAGE = (
    "Fill Application requires Playwright headed mode on the host machine. Docker on macOS cannot open a normal "
    "Chromium window you can continue from."
)
VISIBLE_UNAVAILABLE_FIX = "Run the backend locally with PLAYWRIGHT_HEADLESS=false for native Chromium review."
NO_FIELDS_MESSAGE = "CareerAgent opened the page, but no application form fields were detected."
NO_FIELDS_REASON = (
    "This may be a job detail page, a JavaScript-heavy page, a page requiring login, or not the actual application form."
)
NO_FIELDS_NEXT_ACTION = "Use Open in Browser or navigate to the actual application form manually."
DISPLAY_UNAVAILABLE_MESSAGE = (
    "Headed Chromium cannot launch because no browser display is available. "
    "Run the backend locally with PLAYWRIGHT_HEADLESS=false to open a normal Chromium window."
)
DISPLAY_UNAVAILABLE_FIX = "Stop the Docker backend and run the backend locally with PLAYWRIGHT_HEADLESS=false."
WORKDAY_MANUAL_MESSAGE = (
    "CareerAgent could not open this Workday page with Playwright. Workday often blocks or redirects automation and may "
    "require manual browser navigation."
)
WORKDAY_MANUAL_NEXT_ACTION = "Use Open in Browser and complete this application manually, or paste a direct application form URL after you reach it."
INVALID_TRUNCATED_URL_MESSAGE = "This job URL appears truncated. Open the original posting and save the full URL before using autofill."
NAVIGATION_FAILED_MESSAGE = "CareerAgent could not open this page in Chromium."
BROWSER_CLOSED_MESSAGE = "The browser was closed. Start a new Fill Application session if needed."
PLAYWRIGHT_CHROMIUM_MISSING_MESSAGE = "Chromium is not installed for Playwright in the current backend environment."
PLAYWRIGHT_CHROMIUM_INSTALL_COMMAND = "cd backend && source .venv/bin/activate && python -m playwright install chromium"
PLAYWRIGHT_CHROMIUM_MISSING_DETAILS = (
    "Make sure you run the command in the same virtualenv used to start uvicorn."
)
XSERVER_ERROR_MARKERS = (
    "without having a xserver running",
    "missing x server",
    "$display",
    "platform failed to initialize",
    "no display",
    "cannot open display",
)
CHROMIUM_MISSING_ERROR_MARKERS = (
    "executable doesn't exist",
    "browser executable doesn't exist",
    "please run the following command to download new browsers",
    "browsertype.launch: executable",
    "looks like playwright was just installed or updated",
)
NON_CHROMIUM_MISSING_ERROR_MARKERS = (
    "page.goto",
    "net::err_",
    "target page",
    "target closed",
    "has been closed",
    "context closed",
    "browser closed",
    "timeout",
    "navigation",
    "http_response_code_failure",
    "missing x server",
    "without having a xserver",
)
AUTOFILL_MODES = {"headless_test", "visible_review"}


class AutofillError(ValueError):
    status_code = 400


class AutofillNotFoundError(AutofillError):
    status_code = 404


class AutofillUnavailableError(AutofillError):
    status_code = 503


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(settings.project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _screenshot_url(path_value: str | None) -> str | None:
    if not path_value:
        return None
    filename = Path(path_value).name
    if not filename:
        return None
    return f"/api/autofill/screenshots/{filename}"


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def _normalize_key_text(value: Any) -> str:
    return _normalize_text(value).lower()


def _first_non_empty(*values: Any) -> str | None:
    for value in values:
        normalized = _normalize_text(value)
        if normalized:
            return normalized
    return None


MANUAL_VALUE_LABELS = {
    "full_name": "Full name",
    "first_name": "First name",
    "last_name": "Last name",
    "email": "Email",
    "phone": "Phone",
    "current_location": "Current location",
    "current_company": "Current company",
    "pronouns": "Pronouns",
    "future_job_opportunities_consent": "Future job opportunities consent",
    "linkedin": "LinkedIn",
    "github": "GitHub",
    "portfolio": "Portfolio",
    "school": "School",
    "degree": "Degree",
    "graduation_date": "Graduation date",
    "work_authorized_us": "Authorized to work in the United States",
    "need_sponsorship_now": "Requires sponsorship now",
    "need_sponsorship_future": "Requires sponsorship in the future",
    "willing_to_relocate": "Willing to relocate",
    "why_company": "Why are you interested in this company?",
    "tell_us_about_yourself": "Tell us about yourself",
    "salary_expectation": "Expected salary",
}


def _manual_values(values: dict[str, Any]) -> list[dict[str, str]]:
    manual_values: list[dict[str, str]] = []
    for key, label in MANUAL_VALUE_LABELS.items():
        value = values.get(key)
        if value in (None, "", []):
            continue
        if isinstance(value, bool):
            display_value = "Yes" if value else "No"
        else:
            display_value = str(value)
        manual_values.append({"key": key, "label": label, "value": display_value})
    return manual_values


def _job_or_raise(db: Session, job_id: int) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise AutofillNotFoundError(f"Job {job_id} was not found.")
    return job


def _packet_or_latest_for_job(db: Session, job_id: int, packet_id: int | None) -> ApplicationPacket | None:
    query = db.query(ApplicationPacket)
    if packet_id is not None:
        packet = query.filter(ApplicationPacket.id == packet_id, ApplicationPacket.job_id == job_id).first()
        if packet is None:
            raise AutofillNotFoundError(f"Packet {packet_id} was not found for job {job_id}.")
        return packet

    return (
        query.filter(ApplicationPacket.job_id == job_id)
        .order_by(ApplicationPacket.generated_at.desc().nullslast(), ApplicationPacket.id.desc())
        .first()
    )


def _resolve_project_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    raw_path = Path(path_value)
    path = raw_path.resolve() if raw_path.is_absolute() else (settings.project_root / raw_path).resolve()
    return path


def _resolve_packet_private_path(path_value: str | None) -> Path | None:
    path = _resolve_project_path(path_value)
    if path is None:
        return None
    try:
        path.relative_to(settings.application_packets_dir.resolve())
    except ValueError as exc:
        raise AutofillError("Packet file paths must stay inside outputs/application_packets.") from exc
    return path


def _strip_markdown(content: str) -> str:
    cleaned_lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue
        if stripped.startswith("#"):
            continue
        cleaned_lines.append(re.sub(r"[*_`>#-]", "", line).strip())
    cleaned = "\n".join(cleaned_lines).strip()
    return re.sub(r"\n{3,}", "\n\n", cleaned)


def _prompt_to_field_key(prompt: str) -> str | None:
    normalized = _normalize_key_text(prompt)
    if "why are you interested" in normalized or "why this company" in normalized:
        return "why_company"
    if "tell us about yourself" in normalized or "about yourself" in normalized:
        return "tell_us_about_yourself"
    if "authorized to work" in normalized:
        return "work_authorized_us"
    if "sponsorship" in normalized and "future" in normalized:
        return "need_sponsorship_future"
    if "sponsorship" in normalized:
        return "need_sponsorship_now"
    if "relocat" in normalized:
        return "willing_to_relocate"
    if "salary" in normalized or "compensation" in normalized:
        return "salary_expectation"
    if "demographic" in normalized or "eeo" in normalized:
        return "race_ethnicity"
    return None


def _parse_yes_no_answer(answer: str) -> bool | None:
    normalized = _normalize_key_text(answer).strip(".")
    if normalized.startswith("yes"):
        return True
    if normalized.startswith("no"):
        return False
    return None


def _normalize_public_url(value: Any, host_hint: str) -> str | None:
    raw_value = _first_non_empty(value)
    if not raw_value:
        return None
    normalized = raw_value.strip()
    if normalized.startswith("@"):
        normalized = normalized[1:]
    if normalized.startswith("http://") or normalized.startswith("https://"):
        return normalized
    if "." in normalized and "/" in normalized:
        return f"https://{normalized}"
    if not host_hint:
        return normalized
    if host_hint in normalized:
        return f"https://{normalized}"
    return f"https://{host_hint}/{normalized.strip('/')}"


def _profile_current_company(profile: dict[str, Any]) -> str | None:
    personal = dict(profile.get("personal") or {})
    employment = dict(profile.get("employment") or {})
    work = dict(profile.get("work") or {})
    experience = profile.get("experience") or profile.get("work_experience") or []
    direct_value = _first_non_empty(
        personal.get("current_company"),
        personal.get("current_employer"),
        employment.get("current_company"),
        employment.get("current_employer"),
        work.get("current_company"),
        work.get("current_employer"),
    )
    if direct_value:
        return direct_value
    if isinstance(experience, list):
        for item in experience:
            if not isinstance(item, dict):
                continue
            if item.get("current") is True or _normalize_key_text(item.get("end_date")) in {"present", "current", "now"}:
                return _first_non_empty(item.get("company"), item.get("organization"), item.get("employer"))
    return None


def _email_domain_warnings(email: str | None) -> list[str]:
    if not email or "@" not in email:
        return []
    domain = email.rsplit("@", 1)[-1].strip().lower()
    suspicious_domains = {
        "berkely.edu": "berkeley.edu",
        "gmai.com": "gmail.com",
        "gmial.com": "gmail.com",
        "hotmial.com": "hotmail.com",
    }
    if domain in suspicious_domains:
        return [f"{domain} looks like a possible typo for {suspicious_domains[domain]}. Review manually."]
    return []


def _field_label(field: dict[str, Any]) -> str:
    return _first_non_empty(
        field.get("question_text"),
        field.get("label_text"),
        field.get("placeholder"),
        field.get("name"),
        field.get("id"),
        field.get("field_key"),
    ) or "Detected field"


def _preview_value(value: Any) -> str | None:
    if value in (None, "", []):
        return None
    if isinstance(value, bool):
        return "Yes" if value else "No"
    preview = _normalize_text(value)
    return preview[:117] + "..." if len(preview) > 120 else preview


def _load_packet_question_answers(packet: ApplicationPacket | None) -> dict[str, Any]:
    if packet is None:
        return {}

    path = _resolve_packet_private_path(packet.application_questions_path)
    if path is None or not path.exists():
        return {}

    content = path.read_text(encoding="utf-8")
    answers: dict[str, str] = {}
    pattern = re.compile(
        r"^## Question \d+\nPrompt: (?P<prompt>.+?)\n\n(?P<answer>.*?)(?=^## Question \d+\nPrompt: |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    for match in pattern.finditer(content):
        prompt = match.group("prompt").strip()
        answer = match.group("answer").strip()
        normalized_prompt = _normalize_key_text(prompt)
        yes_no_value = _parse_yes_no_answer(answer)

        if yes_no_value is not None and "authorized to work" in normalized_prompt:
            answers["work_authorized_us"] = yes_no_value
            continue
        if yes_no_value is not None and "sponsorship now or in the future" in normalized_prompt:
            answers["need_sponsorship_now"] = yes_no_value
            answers["need_sponsorship_future"] = yes_no_value
            continue
        if yes_no_value is not None and "future sponsorship" in normalized_prompt:
            answers["need_sponsorship_future"] = yes_no_value
            continue
        if yes_no_value is not None and "sponsorship" in normalized_prompt:
            answers["need_sponsorship_now"] = yes_no_value
            continue
        if yes_no_value is not None and "relocat" in normalized_prompt:
            answers["willing_to_relocate"] = yes_no_value
            continue

        field_key = _prompt_to_field_key(prompt)
        if field_key:
            answers[field_key] = answer
    return answers


def _load_cover_letter_text(packet: ApplicationPacket | None) -> str | None:
    if packet is None:
        return None

    path = _resolve_packet_private_path(packet.cover_letter_path)
    if path is None or not path.exists():
        return None
    return _strip_markdown(path.read_text(encoding="utf-8"))


def _resolve_resume_upload_from_packet(packet: ApplicationPacket | None) -> str | None:
    if packet is None:
        return None
    path = _resolve_packet_private_path(packet.tailored_resume_pdf_path)
    if path and path.exists():
        return _relative_path(path)
    return None


def _resolve_cover_letter_upload_from_packet(packet: ApplicationPacket | None) -> str | None:
    if packet is None:
        return None
    path = _resolve_packet_private_path(packet.cover_letter_pdf_path)
    if path and path.exists():
        return _relative_path(path)
    return None


def _summarize_relevant_skills(job: Job, profile: dict[str, Any]) -> str:
    job_skills = [str(item).strip() for item in (job.required_skills or []) if str(item).strip()]
    profile_skills = {str(item).strip() for item in (profile.get("skills") or []) if str(item).strip()}
    overlap = [skill for skill in job_skills if skill in profile_skills]
    if overlap:
        return ", ".join(overlap[:3])
    if profile_skills:
        return ", ".join(sorted(profile_skills)[:3])
    return "my existing background"


def build_autofill_values(
    profile: dict[str, Any],
    packet: ApplicationPacket | None,
    job: Job,
    *,
    include_application_drafts: bool = False,
) -> dict[str, Any]:
    personal = dict(profile.get("personal") or {})
    education = dict(profile.get("education") or {})
    links = dict(profile.get("links") or {})
    application_defaults = dict(profile.get("application_defaults") or {})
    question_policy = dict(profile.get("question_policy") or {})

    values: dict[str, Any] = {}
    full_name = _first_non_empty(personal.get("name"), personal.get("full_name"))
    if full_name:
        values["full_name"] = full_name
        name_parts = full_name.split()
        values["first_name"] = name_parts[0]
        if len(name_parts) > 1:
            values["last_name"] = " ".join(name_parts[1:])

    current_location = _first_non_empty(personal.get("location"), application_defaults.get("current_location"))
    current_company = _profile_current_company(profile)
    linkedin_url = _normalize_public_url(links.get("linkedin"), "www.linkedin.com/in")
    github_url = _normalize_public_url(links.get("github"), "github.com")

    for field_key, source_value in {
        "email": personal.get("email"),
        "phone": personal.get("phone"),
        "current_location": current_location,
        "current_company": current_company,
        "pronouns": _first_non_empty(personal.get("pronouns"), application_defaults.get("pronouns")),
        "address": _first_non_empty(personal.get("address"), personal.get("street_address")),
        "city": _first_non_empty(personal.get("city"), str(personal.get("location") or "").split(",")[0]),
        "state": _first_non_empty(
            personal.get("state"),
            personal.get("province"),
            personal.get("region"),
            str(personal.get("location") or "").split(",")[1] if "," in str(personal.get("location") or "") else None,
        ),
        "zip": _first_non_empty(personal.get("zip"), personal.get("postal_code")),
        "country": _first_non_empty(
            personal.get("country"),
            str(personal.get("location") or "").split(",")[2] if str(personal.get("location") or "").count(",") >= 2 else None,
        ),
        "linkedin": linkedin_url,
        "github": github_url,
        "portfolio": _normalize_public_url(_first_non_empty(links.get("portfolio"), links.get("website")), ""),
        "website": _normalize_public_url(_first_non_empty(links.get("website"), links.get("portfolio")), ""),
        "school": education.get("school"),
        "degree": education.get("degree"),
        "graduation_date": _first_non_empty(education.get("graduation"), education.get("graduation_date")),
    }.items():
        normalized = _first_non_empty(source_value)
        if normalized:
            values[field_key] = normalized

    if question_policy.get("answer_work_authorization", True):
        if "work_authorized_us" in application_defaults:
            values["work_authorized_us"] = bool(application_defaults.get("work_authorized_us"))

    if question_policy.get("answer_sponsorship", True):
        if "need_sponsorship_now" in application_defaults:
            values["need_sponsorship_now"] = bool(application_defaults.get("need_sponsorship_now"))
        if "need_sponsorship_future" in application_defaults:
            values["need_sponsorship_future"] = bool(application_defaults.get("need_sponsorship_future"))

    if question_policy.get("answer_relocation", True) and "willing_to_relocate" in application_defaults:
        values["willing_to_relocate"] = bool(application_defaults.get("willing_to_relocate"))

    if "future_job_opportunities_consent" in application_defaults:
        values["future_job_opportunities_consent"] = bool(application_defaults.get("future_job_opportunities_consent"))

    profile_only_answer_keys = {
        "work_authorized_us",
        "need_sponsorship_now",
        "need_sponsorship_future",
        "willing_to_relocate",
    }
    if include_application_drafts:
        prompt_answers = {
            key: value
            for key, value in _load_packet_question_answers(packet).items()
            if key not in profile_only_answer_keys
        }
        values.update({key: value for key, value in prompt_answers.items() if _first_non_empty(value)})

        if not values.get("why_company"):
            relevant_skills = _summarize_relevant_skills(job, profile)
            values["why_company"] = (
                f"AI draft. Review manually before using.\n\n"
                f"I'm interested in {job.company} because the {job.title} role overlaps with work I'm already pursuing, "
                f"especially around {relevant_skills}. I would still review the company mission and team context manually before submitting."
            )

        if not values.get("tell_us_about_yourself"):
            current_focus = _first_non_empty(education.get("degree"), ", ".join(profile.get("target_roles") or []), "the work in my resume")
            relevant_skills = _summarize_relevant_skills(job, profile)
            values["tell_us_about_yourself"] = (
                "AI draft. Review manually before using.\n\n"
                f"I'm currently focused on {current_focus}. The parts of my existing background that line up most closely with this role are "
                f"{relevant_skills}. I would still review and personalize this draft before submitting it."
            )

    salary_policy = _normalize_key_text(question_policy.get("answer_salary_expectation"))
    if salary_policy == "draft_only" and not values.get("salary_expectation"):
        values["salary_expectation"] = (
            "REVIEW MANUALLY. Draft: I'm open to discussing compensation based on the scope of the role, level, and location."
        )

    if not values.get("general_cover_letter"):
        cover_letter_text = _load_cover_letter_text(packet)
        if cover_letter_text:
            values["general_cover_letter"] = cover_letter_text

    demographic_policy = _normalize_key_text(question_policy.get("answer_demographic_questions"))
    if demographic_policy == "prefer_not_to_answer":
        for field_key in SENSITIVE_OPTIONAL_FIELD_KEYS:
            values[field_key] = "Prefer not to answer"

    resume_upload_path = _resolve_resume_upload_from_packet(packet)
    if resume_upload_path:
        values["resume_upload"] = resume_upload_path

    cover_letter_upload_path = _resolve_cover_letter_upload_from_packet(packet)
    if cover_letter_upload_path:
        values["cover_letter_upload"] = cover_letter_upload_path

    return {key: value for key, value in values.items() if value not in (None, "")}


def _compile_base_resume_for_upload() -> tuple[str | None, list[str]]:
    warnings: list[str] = []
    resume_document = load_resume_document()
    if resume_document.get("source") != "private":
        warnings.append("Base resume upload was requested, but only the public example resume is available, so no base resume file will be uploaded.")
        return None, warnings

    input_path = settings.resume_path.resolve()
    output_dir = (settings.outputs_dir / "resume").resolve()
    compile_result = compile_latex_file(input_path, output_dir, "base_resume_autofill")
    if not compile_result.get("success"):
        warnings.append(str(compile_result.get("message") or "Base resume PDF compilation was unavailable."))
        return None, warnings

    output_path = _resolve_project_path(str(compile_result.get("output_path") or ""))
    if output_path is None or not output_path.exists():
        warnings.append("Base resume PDF compilation did not produce an uploadable file.")
        return None, warnings

    return _relative_path(output_path), warnings


def _prepare_autofill_context(
    db: Session,
    job_id: int,
    packet_id: int | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_options = dict(options or {})
    job = _job_or_raise(db, job_id)
    if not _normalize_text(job.url):
        raise AutofillError(f"Job {job_id} does not have an application URL.")

    packet = _packet_or_latest_for_job(db, job_id, packet_id)
    profile_document = load_profile_document()
    profile = dict(profile_document.get("profile") or {})
    ai_assisted_apply = bool(resolved_options.get("ai_assisted_apply"))
    include_application_drafts = False
    ai_drafting_warning: str | None = None
    if ai_assisted_apply:
        guard = require_ai_allowed(
            action="draft_application_answer",
            user_enabled=True,
            user_triggered=bool(resolved_options.get("user_triggered", True)),
        )
        provider = get_ai_provider()
        include_application_drafts = bool(guard.get("allowed") and provider.is_available())
        if not include_application_drafts:
            ai_drafting_warning = str(guard.get("message") or provider.unavailable_reason or "AI drafting is disabled.")
    values = build_autofill_values(
        profile,
        packet,
        job,
        include_application_drafts=include_application_drafts,
    )
    if resolved_options.get("fill_sensitive_optional_fields"):
        for field_key in SENSITIVE_OPTIONAL_FIELD_KEYS:
            values[field_key] = "Prefer not to answer"
    warnings: list[str] = []
    if ai_drafting_warning:
        warnings.append(f"AI disabled - detected long-answer questions will be shown for manual drafting. {ai_drafting_warning}")

    if profile_document.get("source") == "example":
        warnings.append("CareerAgent is using the safe example profile. Review every autofill value before using it on a real application.")

    warnings.extend(_email_domain_warnings(values.get("email")))

    if packet is None:
        warnings.append("No application packet exists. Generate a packet first to upload tailored resume/cover letter.")

    files_available: list[str] = []
    if values.get("resume_upload"):
        files_available.append(str(values["resume_upload"]))
    elif resolved_options.get("allow_base_resume_upload"):
        if packet is not None:
            packet_resume_path = _resolve_project_path(packet.tailored_resume_pdf_path)
        else:
            packet_resume_path = None
        if packet is not None and (not packet_resume_path or not packet_resume_path.exists()):
            warnings.append("Packet exists but resume PDF is missing. Review packet or compile resume before upload.")
        base_resume_upload, compile_warnings = _compile_base_resume_for_upload()
        warnings.extend(compile_warnings)
        if base_resume_upload:
            values["resume_upload"] = base_resume_upload
            files_available.append(base_resume_upload)
        elif packet is not None and (not packet_resume_path or not packet_resume_path.exists()):
            values["_resume_upload_status"] = "skipped_packet_pdf_missing"
        else:
            values["_resume_upload_status"] = "skipped_no_resume_pdf"
    else:
        warnings.append("No tailored_resume.pdf available. Compile PDF or use manual upload.")
        values["_resume_upload_status"] = "skipped_no_resume_pdf"

    if values.get("cover_letter_upload"):
        files_available.append(str(values["cover_letter_upload"]))
    elif packet and packet.cover_letter_path and not packet.cover_letter_pdf_path:
        warnings.append("A cover letter draft exists as markdown, but there is no uploadable cover letter PDF yet.")
    elif packet is None:
        warnings.append("No packet-based cover letter is available to upload yet.")

    if resolved_options.get("fill_sensitive_optional_fields"):
        warnings.append("Sensitive optional fields are limited to 'Prefer not to answer' style responses when the profile policy supports them.")

    return {
        "job": job,
        "packet": packet,
        "profile_document": profile_document,
        "profile": profile,
        "values": values,
        "files_available": files_available,
        "warnings": warnings,
    }


def preview_autofill_plan(
    db: Session,
    job_id: int,
    packet_id: int | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = _prepare_autofill_context(db, job_id, packet_id=packet_id, options=options)
    values = dict(context["values"])
    proposed_values = {
        key: (
            str(value)
            if isinstance(value, Path)
            else value
        )
        for key, value in values.items()
    }

    return {
        "job_id": context["job"].id,
        "packet_id": context["packet"].id if context["packet"] else None,
        "proposed_values": proposed_values,
        "manual_values": _manual_values(values),
        "files_available": context["files_available"],
        "warnings": context["warnings"],
        "manual_review_required": True,
        "message": "Preview ready. CareerAgent will only fill safe, high-confidence fields and will never submit the application.",
    }


def _configured_browser_mode() -> str:
    return "headless" if settings.playwright_headless else "headed"


def _running_in_docker() -> bool:
    return Path("/.dockerenv").exists()


def _backend_runtime() -> str:
    if _running_in_docker():
        return "docker"
    if settings.backend_runtime in {"local", "docker"}:
        return settings.backend_runtime
    return "unknown"


def _xvfb_available() -> bool:
    return shutil.which("Xvfb") is not None


def _headed_display_available() -> bool:
    if not _running_in_docker() and sys.platform in {"darwin", "win32"}:
        return True
    return bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY") or (settings.playwright_use_xvfb and _xvfb_available()))


def _is_browser_display_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in XSERVER_ERROR_MARKERS)


def _is_chromium_missing_error(exc: Exception) -> bool:
    message = str(exc).lower()
    if any(marker in message for marker in NON_CHROMIUM_MISSING_ERROR_MARKERS):
        return False
    if any(marker in message for marker in CHROMIUM_MISSING_ERROR_MARKERS):
        return True
    return "playwright install" in message and any(token in message for token in ("chromium", "browser", "executable"))


def _is_browser_closed_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in ("target page", "target closed", "has been closed", "context closed", "browser closed"))


def _chromium_cache_installed() -> bool:
    cache_roots = [
        Path.home() / "Library" / "Caches" / "ms-playwright",
        Path.home() / ".cache" / "ms-playwright",
    ]
    executable_patterns = (
        "chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium",
        "chromium-*/chrome-linux/chrome",
        "chromium-*/chrome-win/chrome.exe",
    )
    for root in cache_roots:
        if not root.exists():
            continue
        for pattern in executable_patterns:
            if any(path.exists() for path in root.glob(pattern)):
                return True
    return False


def _url_appears_truncated(url: str | None) -> bool:
    normalized = _normalize_text(url)
    return not normalized or "..." in normalized or "…" in normalized


def _concise_playwright_error(exc: Exception) -> str:
    first_line = next((line.strip() for line in str(exc).splitlines() if line.strip()), "")
    if not first_line:
        first_line = exc.__class__.__name__
    if len(first_line) > 260:
        first_line = f"{first_line[:257]}..."
    return f"Playwright could not complete the autofill session: {first_line}"


def _is_workday_url(url: str | None) -> bool:
    normalized = _normalize_key_text(url)
    return any(token in normalized for token in ("myworkdayjobs.com", "workdayjobs.com", "wd1.", "wd3.", "wd5."))


def _browser_navigation_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname not in {"localhost", "127.0.0.1"}:
        return url
    if not Path("/.dockerenv").exists():
        return url
    if parsed.port and parsed.port != settings.frontend_port:
        return url
    netloc = f"frontend:{settings.frontend_port}"
    return urlunparse(parsed._replace(netloc=netloc))


def _screenshot_path(job_id: int, label: str) -> Path:
    safe_label = re.sub(r"[^a-z0-9_-]+", "-", label.lower()).strip("-") or "page"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return settings.outputs_dir / "autofill_screenshots" / f"job_{job_id}_{timestamp}_{safe_label}.png"


def _capture_screenshot(page: Any, job_id: int, label: str, warnings: list[str]) -> str | None:
    try:
        path = _screenshot_path(job_id, label)
        path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(path), full_page=True)
        return _relative_path(path)
    except Exception as exc:
        warnings.append(f"Could not capture autofill screenshot: {_concise_playwright_error(exc)}")
        return None


@contextmanager
def _xvfb_session_if_needed(headless: bool | None = None) -> Iterator[None]:
    process, previous_display = _start_xvfb_if_needed(headless)
    try:
        yield
    finally:
        _stop_xvfb_if_needed(process, previous_display)


def _start_xvfb_if_needed(headless: bool | None = None) -> tuple[subprocess.Popen[bytes] | None, str | None]:
    previous_display = os.getenv("DISPLAY")
    launch_is_headless = settings.playwright_headless if headless is None else headless
    if launch_is_headless or not settings.playwright_use_xvfb or previous_display:
        return None, previous_display

    xvfb_path = shutil.which("Xvfb")
    if not xvfb_path:
        raise AutofillUnavailableError("PLAYWRIGHT_USE_XVFB=true, but Xvfb is not installed in this environment.")

    display = ":99"
    process = subprocess.Popen(
        [xvfb_path, display, "-screen", "0", "1280x720x24", "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.3)
    if process.poll() is not None:
        raise AutofillUnavailableError("Xvfb could not start, so headed Chromium has no display available.")

    os.environ["DISPLAY"] = display
    return process, previous_display


def _stop_xvfb_if_needed(process: subprocess.Popen[bytes] | None, previous_display: str | None) -> None:
    if previous_display is None:
        os.environ.pop("DISPLAY", None)
    else:
        os.environ["DISPLAY"] = previous_display
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()


def _get_playwright_support_status() -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return {
            "playwright_installed": False,
            "chromium_installed": False,
            "headed_browser_supported": False,
            "headed_display_available": False,
            "configured_browser_mode": _configured_browser_mode(),
            "playwright_headless": settings.playwright_headless,
            "playwright_use_xvfb": settings.playwright_use_xvfb,
            "playwright_slow_mo_ms": settings.playwright_slow_mo_ms,
            "python_executable": sys.executable,
            "backend_runtime": _backend_runtime(),
            "database_host_hint": settings.database_host_hint,
            "env_file_loaded": getattr(settings, "env_file_loaded", False),
            "env_path": str(getattr(settings, "env_path", "")),
            "playwright_install_hint": "python -m playwright install chromium",
        }

    chromium_installed = False
    chromium_executable_path = ""
    try:
        with sync_playwright() as playwright:
            chromium_executable_path = str(playwright.chromium.executable_path)
            executable_path = Path(chromium_executable_path)
            chromium_installed = executable_path.exists()
    except Exception:
        chromium_installed = _chromium_cache_installed()

    return {
        "playwright_installed": True,
        "chromium_installed": chromium_installed,
        "headed_browser_supported": chromium_installed and _headed_display_available(),
        "headed_display_available": _headed_display_available(),
        "configured_browser_mode": _configured_browser_mode(),
        "playwright_headless": settings.playwright_headless,
        "playwright_use_xvfb": settings.playwright_use_xvfb,
        "playwright_slow_mo_ms": settings.playwright_slow_mo_ms,
        "python_executable": sys.executable,
        "backend_runtime": _backend_runtime(),
        "database_host_hint": settings.database_host_hint,
        "env_file_loaded": getattr(settings, "env_file_loaded", False),
        "env_path": str(getattr(settings, "env_path", "")),
        "playwright_install_hint": "python -m playwright install chromium",
        "chromium_executable_path": chromium_executable_path,
    }


def _resolve_session_mode(options: dict[str, Any]) -> str:
    requested_mode = _normalize_text(options.get("mode"))
    if not requested_mode:
        return "visible_review"
    if requested_mode not in AUTOFILL_MODES:
        raise AutofillError("Autofill mode must be headless_test or visible_review.")
    return requested_mode


def _visible_review_available(support_status: dict[str, Any]) -> bool:
    if _backend_runtime() == "docker" and settings.playwright_use_xvfb:
        return False
    return bool(
        not settings.playwright_headless
        and support_status.get("playwright_installed")
        and support_status.get("chromium_installed")
        and support_status.get("headed_display_available")
    )


def _keep_open_seconds_for_visible_mode(options: dict[str, Any]) -> int:
    if options.get("keep_browser_open") is False and options.get("keep_open_seconds") == 0:
        return 0
    raw_seconds = options.get("keep_open_seconds")
    if raw_seconds is None:
        return max(0, min(settings.playwright_keep_open_seconds, 1800))
    try:
        return max(0, min(int(raw_seconds), 1800))
    except (TypeError, ValueError):
        return max(0, min(settings.playwright_keep_open_seconds, 1800))


def _chromium_missing_summary(
    *,
    job: Job,
    packet: ApplicationPacket | None,
    session_mode: str,
    browser_mode: str,
    warnings: list[str],
    manual_values: list[dict[str, str]],
    fields_detected: int = 0,
    fields_filled: int = 0,
    fields_skipped: int = 0,
    files_uploaded: list[str] | None = None,
    blocked_actions: list[str] | None = None,
    field_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "autofill_effective": False,
        "can_continue_in_browser": False,
        "job_id": job.id,
        "packet_id": packet.id if packet else None,
        "status": "playwright_chromium_missing",
        "mode": session_mode,
        "session_mode": session_mode,
        "session_id": None,
        "browser_mode": browser_mode,
        "opened_url": job.url,
        "fields_detected": fields_detected,
        "fields_filled": fields_filled,
        "fields_skipped": fields_skipped,
        "files_uploaded": files_uploaded or [],
        "blocked_actions": blocked_actions or [],
        "warnings": warnings,
        "manual_review_required": True,
        "message": PLAYWRIGHT_CHROMIUM_MISSING_MESSAGE,
        "suggested_fix": PLAYWRIGHT_CHROMIUM_MISSING_DETAILS,
        "fix_command": PLAYWRIGHT_CHROMIUM_INSTALL_COMMAND,
        "details": PLAYWRIGHT_CHROMIUM_MISSING_DETAILS,
        "recommended_next_action": "install_playwright_chromium_in_active_backend_venv",
        "manual_values": manual_values,
        "field_results": field_results or [],
    }


def _non_detection_failure_summary(
    *,
    job: Job,
    packet: ApplicationPacket | None,
    status: str,
    message: str,
    recommended_next_action: str,
    warnings: list[str],
    manual_values: list[dict[str, str]],
    browser_mode: str = "headed",
    details: str | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "autofill_effective": False,
        "can_continue_in_browser": False,
        "job_id": job.id,
        "packet_id": packet.id if packet else None,
        "status": status,
        "mode": "visible_review",
        "session_mode": "visible_review",
        "session_id": None,
        "browser_mode": browser_mode,
        "opened_url": job.url,
        "fields_detected": 0,
        "fields_filled": 0,
        "fields_skipped": 0,
        "files_uploaded": [],
        "blocked_actions": [],
        "warnings": warnings,
        "manual_review_required": True,
        "message": message,
        "details": details,
        "recommended_next_action": recommended_next_action,
        "manual_values": manual_values,
        "field_results": [],
    }


def _invalid_truncated_url_summary(
    *,
    job: Job,
    packet: ApplicationPacket | None,
    warnings: list[str],
    manual_values: list[dict[str, str]],
    browser_mode: str = "headed",
) -> dict[str, Any]:
    warnings = [*warnings, "The saved URL contains literal ellipsis characters, so CareerAgent cannot know the full destination."]
    return _non_detection_failure_summary(
        job=job,
        packet=packet,
        status="invalid_or_truncated_url",
        message=INVALID_TRUNCATED_URL_MESSAGE,
        recommended_next_action="Open the original posting and re-save or re-import the full application URL.",
        warnings=warnings,
        manual_values=manual_values,
        browser_mode=browser_mode,
    )


def _classify_navigation_failure_summary(
    *,
    job: Job,
    packet: ApplicationPacket | None,
    warnings: list[str],
    manual_values: list[dict[str, str]],
    error_text: str,
    response_status: int | None = None,
) -> dict[str, Any]:
    concise_detail = error_text.strip().splitlines()[0][:260] if error_text.strip() else None
    if _is_workday_url(job.url):
        warnings = [
            *warnings,
            "Workday pages are often JavaScript-heavy or protected.",
            "CareerAgent did not submit anything.",
        ]
        if response_status is not None:
            warnings.append(f"Workday returned HTTP {response_status}.")
        return _non_detection_failure_summary(
            job=job,
            packet=packet,
            status="workday_manual_required",
            message=WORKDAY_MANUAL_MESSAGE,
            recommended_next_action=WORKDAY_MANUAL_NEXT_ACTION,
            warnings=warnings,
            manual_values=manual_values,
            details=concise_detail,
        )

    status = "page_blocked_or_unavailable" if response_status and response_status >= 400 else "navigation_failed"
    warnings = [*warnings, "CareerAgent did not submit anything."]
    if response_status is not None:
        warnings.append(f"The page returned HTTP {response_status}.")
    return _non_detection_failure_summary(
        job=job,
        packet=packet,
        status=status,
        message=NAVIGATION_FAILED_MESSAGE,
        recommended_next_action="Use Open in Browser and complete this application manually, or save a direct application form URL.",
        warnings=warnings,
        manual_values=manual_values,
        details=concise_detail,
    )


def _browser_closed_summary(
    *,
    job: Job,
    packet: ApplicationPacket | None,
    warnings: list[str],
    manual_values: list[dict[str, str]],
    fields_detected: int = 0,
    fields_filled: int = 0,
    fields_skipped: int = 0,
    files_uploaded: list[str] | None = None,
    blocked_actions: list[str] | None = None,
    field_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "autofill_effective": False,
        "can_continue_in_browser": False,
        "job_id": job.id,
        "packet_id": packet.id if packet else None,
        "status": "browser_closed",
        "mode": "visible_review",
        "session_mode": "visible_review",
        "session_id": None,
        "browser_mode": "headed",
        "opened_url": job.url,
        "fields_detected": fields_detected,
        "fields_filled": fields_filled,
        "fields_skipped": fields_skipped,
        "files_uploaded": files_uploaded or [],
        "blocked_actions": blocked_actions or [],
        "warnings": warnings,
        "manual_review_required": True,
        "message": BROWSER_CLOSED_MESSAGE,
        "recommended_next_action": "Start a new Fill Application session if you still want visible autofill.",
        "manual_values": manual_values,
        "field_results": field_results or [],
    }


def _status_recent_session_summaries() -> list[dict[str, Any]]:
    redacted_keys = {"manual_values", "field_results", "proposed_values"}
    summaries: list[dict[str, Any]] = []
    for summary in get_recent_session_summaries():
        summaries.append({key: value for key, value in summary.items() if key not in redacted_keys})
    return summaries


def _hold_visible_browser_for_review(page: Any, keep_open_seconds: int, warnings: list[str]) -> None:
    if keep_open_seconds <= 0:
        return
    warnings.append(
        f"Visible browser review mode kept Chromium open for up to {keep_open_seconds} seconds so the user could continue manually."
    )
    try:
        page.wait_for_timeout(keep_open_seconds * 1000)
    except Exception:
        warnings.append("The visible browser closed before the review hold completed.")


def get_autofill_status() -> dict[str, Any]:
    support_status = _get_playwright_support_status()
    browser_mode = _configured_browser_mode()
    visible_autofill_available = _visible_review_available(support_status)
    headless_diagnostic_available = bool(support_status["playwright_installed"] and support_status["chromium_installed"])
    can_continue_from_autofill = visible_autofill_available
    recommended_user_action = "fill_application" if visible_autofill_available else "open_in_browser"

    if not support_status["playwright_installed"]:
        status = "environment_warning"
    elif visible_autofill_available:
        status = "ready"
    elif support_status.get("backend_runtime") == "docker" and settings.playwright_use_xvfb:
        status = "manual_fallback_ready"
    elif browser_mode == "headless":
        status = "manual_fallback_ready"
    else:
        status = "environment_warning"

    if support_status.get("backend_runtime") == "docker" and settings.playwright_use_xvfb:
        message = (
            "Docker is running Chromium inside Xvfb, which is not a normal macOS Chromium window. "
            "For a real Chromium window you can continue from, stop the Docker backend and run the backend locally."
        )
        environment_note = (
            "Docker containers cannot directly open native macOS browser windows. Use local backend mode for visible autofill."
        )
    elif browser_mode == "headless":
        message = (
            "CareerAgent is configured for headless diagnostics. Run the backend locally with PLAYWRIGHT_HEADLESS=false "
            "to enable a real Chromium review window."
        )
        environment_note = (
            "Headless mode is useful for diagnostics, but it cannot be continued manually."
        )
    elif support_status.get("backend_runtime") == "docker" and not support_status.get("headed_display_available"):
        message = (
            "PLAYWRIGHT_HEADLESS=false was read, but Docker does not have a browser display. "
            "Set PLAYWRIGHT_USE_XVFB=true and rebuild with docker compose up --build."
        )
        environment_note = (
            "The backend image includes Xvfb. Enable it with PLAYWRIGHT_USE_XVFB=true for Docker autofill."
        )
    else:
        message = (
            "CareerAgent is configured for visible browser autofill. It fills safe high-confidence fields and always stops before final submit."
        )
        if support_status.get("backend_runtime") == "local":
            environment_note = "The local backend can open a normal Chromium window for manual review."
        else:
            environment_note = "Docker uses Xvfb as a virtual display for Chromium when PLAYWRIGHT_USE_XVFB=true."

    return {
        "status": status,
        "stage": "Stage 8 - Browser Autofill with Playwright",
        "message": message,
        "manual_review_required": True,
        "browser_mode": browser_mode,
        "visible_autofill_available": visible_autofill_available,
        "headless_diagnostic_available": headless_diagnostic_available,
        "can_continue_from_autofill": can_continue_from_autofill,
        "recommended_user_action": recommended_user_action,
        "active_sessions": list_sessions(),
        "install_command": "python -m playwright install chromium",
        "playwright_install_hint": "python -m playwright install chromium",
        "environment_note": environment_note,
        "recent_sessions": _status_recent_session_summaries(),
        **support_status,
    }


def get_autofill_safety() -> dict[str, Any]:
    return {
        "blocked_final_action_words": BLOCKED_FINAL_SUBMIT_WORDS,
        "safety_rules": [
            "CareerAgent never clicks final submit, apply, confirm, finish, send, or similar final-action buttons.",
            "CareerAgent never bypasses login walls, CAPTCHAs, or anti-bot protections.",
            "CareerAgent only fills high-confidence factual fields and skips low-confidence or sensitive fields.",
            "CareerAgent never marks a job applied automatically. The user must manually review and submit.",
        ],
    }


def _load_playwright() -> tuple[Any, Any, Any]:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise AutofillUnavailableError(
            "Playwright is not installed in this environment. Install it with 'python -m playwright install chromium' after adding the backend dependency."
        ) from exc
    return sync_playwright, PlaywrightError, PlaywrightTimeoutError


def _detect_page_warnings(page: Any) -> list[str]:
    warnings: list[str] = []
    try:
        body_text = _normalize_key_text(page.locator("body").inner_text(timeout=3000))
    except Exception:
        return warnings

    if any(token in body_text for token in ("captcha", "hcaptcha", "recaptcha", "i am not a robot")):
        warnings.append("A CAPTCHA or anti-bot challenge appears to be present. CareerAgent will not bypass it.")
    if any(token in body_text for token in ("sign in", "log in", "login")) and "password" in body_text:
        warnings.append("This page appears to require a login before the application form is available.")
    if any(token in body_text for token in ("workday", "greenhouse", "lever")):
        warnings.append("This appears to be a hosted application workflow. Some fields may load dynamically after additional user interaction.")
    return warnings


def _detect_apply_actions(page: Any) -> list[str]:
    try:
        raw_actions = page.evaluate(
            """
            () => Array.from(document.querySelectorAll("button, input[type=submit], input[type=button], a, [role='button'], [role='link']")).map((element) => ({
              text: (element.innerText || element.textContent || element.getAttribute("value") || element.getAttribute("aria-label") || element.getAttribute("title") || "").trim(),
              href: element.getAttribute("href") || "",
            }))
            """
        )
    except Exception:
        return []

    apply_actions: list[str] = []
    for action in raw_actions:
        label = _normalize_text(action.get("text")) or _normalize_text(action.get("href")) or "apply action"
        normalized = _normalize_key_text(label)
        if normalized in {"apply", "apply now"} or "apply now" in normalized or normalized.startswith("apply "):
            apply_actions.append(f"{label} action detected and not clicked.")
    return list(dict.fromkeys(apply_actions))


ACTION_SELECTOR = "button, input[type=submit], input[type=button], a, [role='button'], [role='link']"
SAFE_START_APPLICATION_EXACT_LABELS = {
    "apply",
    "apply now",
    "apply today",
    "start application",
    "begin application",
}
SAFE_START_APPLICATION_PHRASES = (
    "apply for this job",
    "apply for this position",
    "apply to this job",
    "apply to this position",
    "start your application",
    "begin your application",
)


def _is_safe_start_application_action(label: str, href: str) -> bool:
    normalized = _normalize_key_text(label)
    normalized_href = _normalize_key_text(href)
    if not normalized and not normalized_href:
        return False
    if any(token in normalized for token in ("submit", "confirm", "finish", "send", "complete", "final")):
        return False
    if normalized in SAFE_START_APPLICATION_EXACT_LABELS:
        return True
    if any(phrase in normalized for phrase in SAFE_START_APPLICATION_PHRASES):
        return True
    if normalized == "apply" and any(token in normalized_href for token in ("job", "application", "gh_jid", "lever.co", "greenhouse")):
        return True
    return False


def _click_safe_start_application_action(page: Any, warnings: list[str]) -> tuple[Any, str | None]:
    try:
        raw_actions = page.evaluate(
            f"""
            () => Array.from(document.querySelectorAll("{ACTION_SELECTOR}")).map((element, index) => {{
              const style = window.getComputedStyle(element);
              const rect = element.getBoundingClientRect();
              return {{
                index,
                text: (element.innerText || element.textContent || element.getAttribute("value") || element.getAttribute("aria-label") || element.getAttribute("title") || "").trim(),
                href: element.getAttribute("href") || "",
                type: (element.getAttribute("type") || element.tagName || "").toLowerCase(),
                disabled: Boolean(element.disabled || element.getAttribute("aria-disabled") === "true"),
                visible: style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0,
              }};
            }})
            """
        )
    except Exception:
        return page, None

    candidate = None
    for action in raw_actions:
        label = _normalize_text(action.get("text")) or _normalize_text(action.get("href")) or "Apply"
        if not action.get("visible") or action.get("disabled"):
            continue
        if action.get("type") == "submit":
            continue
        if _is_safe_start_application_action(label, str(action.get("href") or "")):
            candidate = action
            break
    if candidate is None:
        return page, None

    label = _normalize_text(candidate.get("text")) or _normalize_text(candidate.get("href")) or "Apply"
    existing_pages = list(page.context.pages)
    try:
        page.locator(ACTION_SELECTOR).nth(int(candidate["index"])).click(timeout=5000)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        page.wait_for_timeout(1500)
    except Exception as exc:
        warnings.append(f"Could not click initial application start action '{label}': {_concise_playwright_error(exc)}")
        return page, None

    new_pages = [candidate_page for candidate_page in page.context.pages if candidate_page not in existing_pages]
    next_page = new_pages[-1] if new_pages else page
    try:
        next_page.wait_for_load_state("domcontentloaded", timeout=5000)
    except Exception:
        pass
    return next_page, f"Clicked initial application start action '{label}' to reach the form. CareerAgent still did not click final submit."


def _detect_form_fields_in_page_or_frame(page: Any, warnings: list[str]) -> tuple[Any, list[dict[str, Any]]]:
    try:
        fields = detect_form_fields(page)
    except Exception:
        fields = []
    if fields:
        return page, fields

    for frame in page.frames:
        if frame == page.main_frame:
            continue
        try:
            frame_fields = detect_form_fields(frame)
        except Exception:
            continue
        if frame_fields:
            warnings.append(f"Detected application form fields inside embedded frame: {frame.url}")
            return frame, frame_fields
    return page, []


def _combined_detected_actions(page: Any, form_context: Any, detector: Any) -> list[str]:
    actions: list[str] = []
    for context in (page, form_context):
        if context is None:
            continue
        try:
            for action in detector(context):
                if action not in actions:
                    actions.append(action)
        except Exception:
            continue
    return actions


def _detect_blocked_actions(page: Any) -> list[str]:
    raw_actions = page.evaluate(
        """
        () => Array.from(document.querySelectorAll("button, input[type=submit], input[type=button], a, [role='button'], [role='link']")).map((element) => ({
          text: (element.innerText || element.textContent || element.getAttribute("value") || element.getAttribute("aria-label") || element.getAttribute("title") || "").trim(),
          type: (element.getAttribute("type") || element.tagName || "").toLowerCase(),
        }))
        """
    )
    blocked: list[str] = []
    for action in raw_actions:
        label = _normalize_text(action.get("text")) or _normalize_text(action.get("type")) or "unnamed action"
        if should_block_element(label, action.get("type")):
            blocked.append(f"{label} button detected and not clicked.")
    return list(dict.fromkeys(blocked))


def _choose_select_option(option_texts: list[str], desired_value: Any) -> str | None:
    normalized_options = [_normalize_key_text(option) for option in option_texts]

    if isinstance(desired_value, bool):
        preferred_tokens = ("yes", "authorized", "true", "willing") if desired_value else ("no", "not", "false")
        for option, normalized in zip(option_texts, normalized_options, strict=False):
            if any(token in normalized for token in preferred_tokens):
                return option
        return None

    normalized_value = _normalize_key_text(desired_value)
    if normalized_value in {"prefer not to answer", "prefer not", "decline", "decline to self-identify", "decline to self identify"}:
        decline_tokens = (
            "decline to self-identify",
            "decline to self identify",
            "prefer not to answer",
            "prefer not to say",
            "do not wish to answer",
            "choose not to answer",
        )
        for option, normalized in zip(option_texts, normalized_options, strict=False):
            if any(token in normalized for token in decline_tokens):
                return option
    for option, normalized in zip(option_texts, normalized_options, strict=False):
        if normalized == normalized_value:
            return option
    for option, normalized in zip(option_texts, normalized_options, strict=False):
        if normalized_value and normalized_value in normalized:
            return option
    return None


def _choice_matches_boolean(field: dict[str, Any], desired_value: bool) -> bool:
    choice_text = _normalize_key_text(field.get("choice_text"))
    value_attr = _normalize_key_text(field.get("value_attr"))
    combined = f"{choice_text} {value_attr}".strip()
    positive_tokens = ("yes", "true", "authorized", "willing", "able")
    negative_tokens = ("no", "false", "not", "decline")
    if desired_value:
        return any(token in combined for token in positive_tokens) and not any(token in combined for token in negative_tokens)
    return any(token in combined for token in negative_tokens)


def _apply_value_to_field(page: Any, field: dict[str, Any], desired_value: Any) -> tuple[bool, str]:
    locator = page.locator(field["selector"]).first
    tag = _normalize_key_text(field.get("tag"))
    input_type = _normalize_key_text(field.get("input_type"))
    field_key = str(field.get("field_key") or "")

    try:
        locator.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass

    if input_type == "file":
        upload_path = _resolve_project_path(str(desired_value))
        if upload_path is None or not upload_path.exists():
            return False, "Upload file was not found on disk."
        locator.set_input_files(str(upload_path))
        return True, f"Uploaded {upload_path.name}."

    if tag == "select":
        option_text = _choose_select_option(list(field.get("options") or []), desired_value)
        if not option_text:
            return False, "No matching select option was found."
        locator.select_option(label=option_text)
        return True, f"Selected '{option_text}'."

    if input_type in {"radio", "checkbox"}:
        if not isinstance(desired_value, bool):
            return False, "Boolean answer required for radio or checkbox fields."
        if field_key == "future_job_opportunities_consent":
            if not desired_value:
                return False, "Future opportunities consent is disabled in profile preferences."
            locator.check()
            return True, "Selected future opportunities consent."
        if not _choice_matches_boolean(field, desired_value):
            return False, "This option does not match the desired yes/no answer."
        locator.check()
        return True, "Selected the matching choice."

    if field_key == "phone":
        locator.fill(str(desired_value))
        return True, "Filled phone field."

    locator.fill(str(desired_value))
    return True, "Filled text field."


def _build_application_answer_prompt(*, field: dict[str, Any], job: Job, profile: dict[str, Any]) -> str:
    question_text = _field_label(field)
    profile_context = {
        "personal": dict(profile.get("personal") or {}),
        "education": dict(profile.get("education") or {}),
        "links": dict(profile.get("links") or {}),
        "skills": list(profile.get("skills") or []),
        "target_roles": list(profile.get("target_roles") or []),
        "application_defaults": dict(profile.get("application_defaults") or {}),
        "writing_style": dict(profile.get("writing_style") or {}),
    }
    return "\n\n".join(
        [
            "Draft one concise, truthful application-form answer for the exact question below.",
            "Return only the answer text. Do not include markdown headings.",
            "Mark the first line exactly: AI draft. Review manually before using.",
            "Do not give a blanket attestation such as 'my responses reflect my own understanding' as the whole answer.",
            "If the field contains several numbered subquestions, answer each numbered part directly in order.",
            "Do not invent personal experience, employers, credentials, baseball R&D experience, demographics, or work authorization facts.",
            "For technical, math, statistics, or baseball-domain questions, reason through the question directly and show work when useful.",
            "If the answer depends on missing personal facts, say REVIEW MANUALLY for that part instead of guessing.",
            "Never submit the application.",
            f"Question category: {field.get('question_category') or 'unknown_long_answer'}",
            f"Question: {question_text}",
            "Job:",
            (
                f"Company: {job.company}\n"
                f"Title: {job.title}\n"
                f"Location: {job.location}\n"
                f"Description: {_normalize_text(job.job_description)[:3500]}"
            ),
            f"Profile context: {profile_context}",
        ]
    )


def _mock_application_answer(field: dict[str, Any], job: Job) -> str:
    question = _normalize_key_text(_field_label(field))
    prefix = "AI draft. Review manually before using.\n\n"
    if "a-grade" in question and "exactly four possible values" in question and "312 pa" in question:
        return (
            prefix +
            "1. Let A be A-grade. Prior odds are 0.30 / 0.70 = 0.429. The game has 2 extra-base hits in 4 at-bats. With binomial xBH rates of 10% vs. 8%, "
            "LR = (0.10^2 * 0.90^2) / (0.08^2 * 0.92^2) ≈ 1.50, so posterior odds are 0.64 and posterior probability is about 39%. This is highly sensitive to the assumed xBH rates and the one-game sample.\n\n"
            "2a. Treat N + 0.1 as N and one out, or N + 1/3 true innings. ERA = 9E / (N + 1/3), and ERA between 3 and 4 means (N + 1/3)/3 < E < 4(N + 1/3)/9. "
            "Count integer E values in that open interval and choose the first N with exactly four. REVIEW MANUALLY: enumerate the boundary cases to confirm the final integer.\n\n"
            "2b. The interval length is (1/9)(M + 1/3). To guarantee at least four integer earned-run totals for every M >= N, check the finite set of M modulo 9 around the first width threshold and then use monotonicity. REVIEW MANUALLY: confirm the exact threshold by enumeration.\n\n"
            "3a. A .286 average with .350 BABIP, only 3 HR, and a 55% groundball rate suggests the line is driven by balls in play more than game power. I would be more confident in contact/speed traits than in power, and I would regress BABIP without quality-of-contact support.\n\n"
            "3b. With a 55% flyball rate instead, the same line is less groundball/speed driven and more dependent on airborne contact quality. Only 3 HR could be either under-realized power or weak fly-ball contact; sustainability depends heavily on exit velocity, pull rate, popups, and HR/FB."
        )
    if "a-grade" in question or ("30%" in question and "xbh" in question) or "xBH" in _field_label(field):
        return (
            prefix +
            "1. Let A be A-grade. Prior odds are 0.30 / 0.70 = 0.429. The observed game has 2 extra-base hits in 4 at-bats. "
            "Using a binomial likelihood with xBH rates 10% for A-grade and 8% otherwise, the likelihood ratio is "
            "(0.10^2 * 0.90^2) / (0.08^2 * 0.92^2) ≈ 1.50. Posterior odds are 0.429 * 1.50 = 0.64, so posterior probability is about 0.64 / 1.64 = 39%. "
            "This is very sensitive to the assumed xBH rates and ignores quality of contact, park, opponent, and tiny-sample noise; one game should move the estimate only modestly."
        )
    if "bayesian" in question or "xbh" in question or "draft" in question:
        return (
            prefix +
            "Mock technical draft: State the prior probability, define the observed first-game evidence, estimate the likelihood of that evidence under each player-quality hypothesis, then update with Bayes' rule. "
            "I would make the posterior explicit and note that one game is weak evidence unless the xBH-rate model assigns a much higher likelihood to the observed result for successful draftees."
        )
    if "n + 0.1" in question and "exactly four possible values" in question:
        return (
            prefix +
            "2a. Innings listed as N + 0.1 means N and one out, or N + 1/3 true innings. ERA = 9E / (N + 1/3). "
            "With ERA between 3 and 4, E must satisfy (N + 1/3)/3 < E < 4(N + 1/3)/9. The number of possible ERA values is the number of integers E in that open interval. "
            "I would enumerate the boundary values of N and choose the first N where exactly four integer earned-run totals fit. REVIEW MANUALLY: verify the boundary convention for 'between' and decimal baseball innings."
        )
    if "for all m" in question or ("smallest value n" in question and "at least four" in question):
        return (
            prefix +
            "2b. Use the same integer-count framing as 2a. The interval length is (4/9 - 1/3)(M + 1/3) = (1/9)(M + 1/3). "
            "To guarantee at least four integer E values for every M >= N, the interval must be wide enough and aligned so the worst-case endpoints still contain four integers. "
            "I would solve this by checking the finite set of M modulo 9 around the first width threshold, then prove monotonicity after that point. REVIEW MANUALLY: confirm the final numeric N by enumeration."
        )
    if "312 pa" in question and "55% groundball" in question:
        return (
            prefix +
            "3a. The .286 average with a .350 BABIP and only 3 HR suggests much of the line is being carried by balls in play rather than game power. "
            "With 312 PA, I would be fairly confident the hitter has shown some bat-to-ball ability or speed/contact traits, but less confident that the average is sustainable without batted-ball quality details. "
            "The 55% groundball rate reinforces limited over-the-fence power and caps slugging upside unless the hitter hits the ball extremely hard. I would regress BABIP and power projections toward scouting/trackman inputs."
        )
    if "55% flyball" in question or "55% fly ball" in question:
        return (
            prefix +
            "3b. A 55% flyball rate changes the interpretation: with the same .286 AVG, .350 BABIP, and only 3 HR, the hitter may be producing a lot of airborne contact that has not turned into home runs. "
            "That can be promising if exit velocity and pull-side contact are strong, but risky if the fly balls are weak or popups. I would be less comfortable projecting the batting average from BABIP alone and would focus on quality of contact, HR/FB, park, and strikeout trends."
        )
    if "minimum value of n" in question or "smallest n" in question or "era" in question:
        return (
            prefix +
            "Mock math draft: Treat ERA as 9 * earned runs / innings pitched. Enumerate the feasible earned-run and innings-pitched values implied by the prompt, then choose the smallest N that makes the displayed/rounded ERA condition true."
        )
    if "hitter" in question or "flyball" in question or "fly ball" in question:
        return (
            prefix +
            "Mock baseball-statistics draft: Separate rate stats from batted-ball profile. The same slash line can hide very different underlying skill signals; adding fly-ball rate changes the inference about power, contact quality, and sustainability."
        )
    return (
        prefix +
        f"MockProvider draft for {job.company} {job.title}. Replace this with a reviewed answer grounded in the exact question and your real background before submitting."
    )


def _is_unusable_application_draft(answer: str, field: dict[str, Any]) -> bool:
    normalized_answer = _normalize_key_text(answer)
    normalized_question = _normalize_key_text(_field_label(field))
    if len(normalized_answer) < 80:
        return True
    generic_phrases = (
        "my responses below reflect my own understanding",
        "prepared to discuss them in depth",
        "i agree",
        "review manually before using." ,
    )
    if any(phrase in normalized_answer for phrase in generic_phrases) and not any(
        token in normalized_answer
        for token in ("posterior", "prior", "era", "babip", "flyball", "groundball", "xbh", "bayes", "likelihood")
    ):
        return True
    technical_tokens = [token for token in ("xbh", "a-grade", "era", "babip", "groundball", "flyball", "posterior") if token in normalized_question]
    if technical_tokens and not any(token in normalized_answer for token in technical_tokens):
        return True
    return False


def _draft_application_answer_for_field(
    *,
    field: dict[str, Any],
    job: Job,
    profile: dict[str, Any],
    user_triggered: bool,
    warnings: list[str],
) -> tuple[str | None, str, str | None]:
    guard = require_ai_allowed(
        action="draft_application_answer",
        user_enabled=True,
        user_triggered=user_triggered,
    )
    provider_name = str(guard.get("provider") or "unknown")
    if not guard.get("allowed"):
        return None, str(guard.get("message") or "AI drafting is disabled."), provider_name

    provider = get_ai_provider()
    if not provider.is_available():
        return None, provider.unavailable_reason or f"{provider.name} provider is unavailable.", provider.name

    if provider.name == "mock":
        warnings.append("MockProvider is active. Long-answer application drafts are deterministic placeholders for testing.")
        return _mock_application_answer(field, job), "AI-assisted mock technical answer drafted.", provider.name

    result = provider.generate_text(
        "draft_application_answer",
        _build_application_answer_prompt(field=field, job=job, profile=profile),
        context={
            "job": {
                "id": job.id,
                "company": job.company,
                "title": job.title,
                "description": job.job_description,
            },
            "profile": profile,
            "question": _field_label(field),
            "question_category": field.get("question_category"),
            "api_action": "draft_application_answer",
            "user_enabled": True,
            "user_triggered": user_triggered,
        },
    )
    warnings.extend(str(warning) for warning in list(result.get("warnings") or []) if warning)
    if not result.get("success"):
        fallback = _mock_application_answer(field, job)
        warnings.append(f"{provider.name} could not draft this long answer, so CareerAgent inserted a review-required technical fallback.")
        return fallback, f"{provider.name} failed; review-required technical fallback drafted.", provider.name
    answer = str(result.get("content") or "").strip()
    if not answer:
        fallback = _mock_application_answer(field, job)
        warnings.append(f"{provider.name} returned an empty long-answer draft, so CareerAgent inserted a review-required technical fallback.")
        return fallback, f"{provider.name} returned empty content; review-required technical fallback drafted.", provider.name
    if "review manually before using" not in answer.lower():
        answer = f"AI draft. Review manually before using.\n\n{answer}"
    if _is_unusable_application_draft(answer, field):
        fallback = _mock_application_answer(field, job)
        warnings.append(f"{provider.name} returned a generic or incomplete long-answer draft, so CareerAgent inserted a review-required technical fallback.")
        return fallback, f"{provider.name} generic draft replaced with review-required technical fallback.", provider.name
    return answer, f"AI-assisted {field.get('question_category') or 'long-answer'} answer drafted.", provider.name


def _fill_safe_fields(
    *,
    page: Any,
    fields_detected: list[dict[str, Any]],
    values: dict[str, Any],
    job: Job,
    profile: dict[str, Any],
    warnings: list[str],
    allow_sensitive_optional: bool,
    ai_assisted_apply: bool,
    user_triggered: bool,
    headless: bool,
    playwright_error_type: Any,
) -> tuple[list[dict[str, Any]], int, int, list[str]]:
    field_results: list[dict[str, Any]] = []
    fields_filled = 0
    fields_attempted = 0
    files_uploaded: list[str] = []

    if headless and allow_sensitive_optional:
        warnings.append("Headless mode skips sensitive optional fields even when optional EEO autofill is requested.")
        allow_sensitive_optional = False

    for field in fields_detected:
        field_key = str(field.get("field_key") or "unknown_question")
        label = _field_label(field)
        confidence = float(field.get("confidence") or 0.0)
        value = values.get(field_key)
        safe_to_fill = bool(field.get("safe_to_fill"))
        category = str(field.get("question_category") or field.get("safe_category") or field_key)

        def append_result(
            *,
            filled: bool,
            action: str,
            reason: str,
            result_value: Any = None,
            provider: str | None = None,
        ) -> None:
            field_results.append(
                {
                    "field_key": field_key,
                    "label": label,
                    "question": field.get("question_text") or label,
                    "category": category,
                    "action": action,
                    "selector": field.get("selector"),
                    "filled": filled,
                    "confidence": confidence,
                    "value_preview": _preview_value(result_value),
                    "value": str(result_value) if action == "filled_ai_draft_review_required" and result_value not in (None, "", []) else None,
                    "reason": reason,
                    "provider": provider,
                    "review_required": action == "filled_ai_draft_review_required",
                }
            )

        if field_key in SKIPPED_ALWAYS_FIELD_KEYS:
            append_result(filled=False, action="skipped", reason="Sensitive field skipped by policy.")
            continue

        if field_key in SENSITIVE_OPTIONAL_FIELD_KEYS and not allow_sensitive_optional:
            append_result(filled=False, action="skipped", reason="Sensitive optional field skipped unless explicitly enabled.")
            continue

        if field_key in SENSITIVE_OPTIONAL_FIELD_KEYS and allow_sensitive_optional:
            safe_to_fill = True

        if field_key in LONG_ANSWER_FIELD_KEYS and ai_assisted_apply and field_key != "general_cover_letter":
            # Live application questions need answers grounded in the exact
            # detected prompt. Packet-level generic drafts are too broad for
            # technical forms such as Lever R&D questions.
            value = None

        if field_key in LONG_ANSWER_FIELD_KEYS and value in (None, "", []):
            if not ai_assisted_apply:
                append_result(
                    filled=False,
                    action="skipped",
                    reason="Skipped long-answer question: AI-assisted apply required.",
                )
                continue
            value, draft_reason, provider_name = _draft_application_answer_for_field(
                field=field,
                job=job,
                profile=profile,
                user_triggered=user_triggered,
                warnings=warnings,
            )
            if value in (None, "", []):
                append_result(
                    filled=False,
                    action="skipped",
                    reason=f"AI disabled or unavailable - draft manually or enable AI. {draft_reason}",
                    provider=provider_name,
                )
                continue

        if not safe_to_fill:
            append_result(filled=False, action="skipped", reason=str(field.get("reason") or "Field not considered safe to autofill."))
            continue

        if confidence < HIGH_CONFIDENCE_THRESHOLD and not (field_key in LONG_ANSWER_FIELD_KEYS and ai_assisted_apply):
            append_result(filled=False, action="skipped", reason="Confidence below the autofill threshold.")
            continue

        if value in (None, "", []):
            if field_key == "current_company":
                reason = "No current company in profile."
            elif field_key == "current_location":
                reason = "No profile location found."
            elif field_key == "pronouns":
                reason = "No pronouns configured in profile."
            elif field_key == "resume_upload":
                resume_status = str(values.get("_resume_upload_status") or "skipped_no_resume_pdf")
                reason = "skipped_packet_pdf_missing" if resume_status == "skipped_packet_pdf_missing" else "skipped_no_resume_pdf"
            else:
                reason = "No truthful value was available for this field."
            append_result(filled=False, action=reason if field_key == "resume_upload" else "skipped", reason=reason)
            continue

        try:
            fields_attempted += 1
            filled, reason = _apply_value_to_field(page, field, value)
        except playwright_error_type as exc:
            filled = False
            reason = f"Browser interaction failed: {exc}"

        if filled:
            fields_filled += 1
            if field_key in {"resume_upload", "cover_letter_upload"}:
                files_uploaded.append(Path(str(value)).name)

        if filled and field_key in LONG_ANSWER_FIELD_KEYS and ai_assisted_apply:
            action = "filled_ai_draft_review_required"
        elif filled and field_key in {"resume_upload", "cover_letter_upload"}:
            action = "uploaded"
            if field_key == "resume_upload":
                reason = "uploaded_resume_pdf"
        elif filled:
            action = "filled"
        else:
            action = "skipped"
            if field_key == "resume_upload" and "not found" in reason.lower():
                reason = "skipped_no_resume_pdf"
        append_result(filled=filled, action=action, reason=reason, result_value=value)

    return field_results, fields_filled, fields_attempted, files_uploaded


def _start_visible_review_session(
    *,
    db: Session,
    job: Job,
    packet: ApplicationPacket | None,
    values: dict[str, Any],
    profile: dict[str, Any],
    manual_values: list[dict[str, str]],
    warnings: list[str],
    resolved_options: dict[str, Any],
    sync_playwright: Any,
    playwright_error_type: Any,
    playwright_timeout_error_type: Any,
    initial_status: str,
) -> dict[str, Any]:
    playwright_manager: Any | None = None
    browser: Any | None = None
    context_manager: Any | None = None
    page: Any | None = None
    xvfb_process: subprocess.Popen[bytes] | None = None
    previous_display: str | None = None
    started_logged = False
    session_stored = False
    fields_detected: list[dict[str, Any]] = []
    field_results: list[dict[str, Any]] = []
    blocked_actions: list[str] = []
    files_uploaded: list[str] = []
    fields_filled = 0
    fields_attempted = 0

    warnings.append(HEADED_REVIEW_MESSAGE)
    cleanup_closed_sessions()
    cleanup_expired_sessions(settings.playwright_keep_open_seconds)

    if _url_appears_truncated(job.url):
        summary = _invalid_truncated_url_summary(
            job=job,
            packet=packet,
            warnings=warnings,
            manual_values=manual_values,
        )
        save_session_summary(summary)
        return summary

    try:
        xvfb_process, previous_display = _start_xvfb_if_needed(False)
        playwright_manager = sync_playwright()
        playwright = playwright_manager.start()
        browser = playwright.chromium.launch(
            headless=False,
            slow_mo=settings.playwright_slow_mo_ms,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context_manager = browser.new_context()
        page = context_manager.new_page()

        promote_job_status_if_needed(db, job.id, "autofill_started", notes="Started a visible browser autofill session.")
        db.refresh(job)
        log_event(
            db,
            job_id=job.id,
            packet_id=packet.id if packet else None,
            event_type="autofill_started",
            notes="Started a visible browser autofill session.",
            old_status=initial_status,
            new_status=job.application_status,
            metadata_json={"url": job.url, "packet_id": packet.id if packet else None, "session_mode": "visible_review"},
        )
        started_logged = True

        try:
            response = page.goto(_browser_navigation_url(job.url), wait_until="domcontentloaded", timeout=settings.autofill_navigation_timeout_ms)
        except playwright_timeout_error_type as exc:
            summary = _classify_navigation_failure_summary(
                job=job,
                packet=packet,
                warnings=warnings,
                manual_values=manual_values,
                error_text=str(exc),
            )
            log_event(
                db,
                job_id=job.id,
                packet_id=packet.id if packet else None,
                event_type="autofill_navigation_failed",
                notes=summary["message"],
                old_status=initial_status,
                new_status=job.application_status,
                metadata_json={"url": job.url, "status": summary["status"], "details": summary.get("details")},
            )
            save_session_summary(summary)
            return summary
        except playwright_error_type as exc:
            if _is_browser_closed_error(exc):
                summary = _browser_closed_summary(
                    job=job,
                    packet=packet,
                    warnings=warnings,
                    manual_values=manual_values,
                )
            else:
                summary = _classify_navigation_failure_summary(
                    job=job,
                    packet=packet,
                    warnings=warnings,
                    manual_values=manual_values,
                    error_text=str(exc),
                )
            log_event(
                db,
                job_id=job.id,
                packet_id=packet.id if packet else None,
                event_type="autofill_navigation_failed",
                notes=summary["message"],
                old_status=initial_status,
                new_status=job.application_status,
                metadata_json={"url": job.url, "status": summary["status"], "details": summary.get("details")},
            )
            save_session_summary(summary)
            return summary

        if response is not None and response.status >= 400:
            summary = _classify_navigation_failure_summary(
                job=job,
                packet=packet,
                warnings=warnings,
                manual_values=manual_values,
                error_text=f"HTTP {response.status} while loading {job.url}",
                response_status=response.status,
            )
            log_event(
                db,
                job_id=job.id,
                packet_id=packet.id if packet else None,
                event_type="autofill_navigation_failed",
                notes=summary["message"],
                old_status=initial_status,
                new_status=job.application_status,
                metadata_json={"url": job.url, "status": summary["status"], "http_status": response.status},
            )
            save_session_summary(summary)
            return summary

        warnings.extend(_detect_page_warnings(page))
        form_context, fields_detected = _detect_form_fields_in_page_or_frame(page, warnings)
        if not fields_detected and not _is_workday_url(job.url):
            page, start_action_message = _click_safe_start_application_action(page, warnings)
            if start_action_message:
                warnings.append(start_action_message)
                warnings.extend(_detect_page_warnings(page))
                form_context, fields_detected = _detect_form_fields_in_page_or_frame(page, warnings)
        blocked_actions = _combined_detected_actions(page, form_context, _detect_blocked_actions)
        apply_actions = _combined_detected_actions(page, form_context, _detect_apply_actions)
        for action in apply_actions:
            if action not in blocked_actions:
                blocked_actions.append(action)

        if _is_workday_url(job.url):
            warnings.append(
                "This appears to be a Workday job page. Workday job-detail pages often do not expose application form fields until the user proceeds manually."
            )

        if fields_detected:
            field_results, fields_filled, fields_attempted, files_uploaded = _fill_safe_fields(
                page=form_context,
                fields_detected=fields_detected,
                values=values,
                job=job,
                profile=profile,
                warnings=warnings,
                allow_sensitive_optional=bool(resolved_options.get("fill_sensitive_optional_fields")),
                ai_assisted_apply=bool(resolved_options.get("ai_assisted_apply")),
                user_triggered=bool(resolved_options.get("user_triggered", True)),
                headless=False,
                playwright_error_type=playwright_error_type,
            )
        else:
            if _is_workday_url(job.url) and apply_actions:
                warnings.append("An Apply button or link was found on this Workday page, but CareerAgent did not click it automatically.")
            warnings.append(NO_FIELDS_REASON)

        autofill_effective = fields_filled > 0 or bool(files_uploaded)
        if fields_detected and not autofill_effective:
            warnings.append(
                "CareerAgent detected fields but did not safely fill any of them. Review the field results and try the local test form or a direct application form URL."
            )

        session = create_session(
            browser=browser,
            context=context_manager,
            page=page,
            job_id=job.id,
            opened_url=page.url,
            mode="visible_review",
            playwright_manager=playwright_manager,
            xvfb_process=xvfb_process,
            previous_display=previous_display,
        )
        xvfb_process = None
        session_stored = True
        session_id = session["session_id"]

        if not fields_detected:
            summary_status = "no_fields_detected"
            success = False
            message = NO_FIELDS_MESSAGE
            recommended_next_action = (
                "Open this Workday job in your default browser and proceed manually to the application form, "
                "or save the direct application form URL in CareerAgent."
                if _is_workday_url(job.url)
                else NO_FIELDS_NEXT_ACTION
            )
            event_type = "autofill_no_fields_detected"
            event_notes = NO_FIELDS_MESSAGE
        elif autofill_effective:
            summary_status = "visible_session_started"
            success = True
            message = VISIBLE_SESSION_MESSAGE
            recommended_next_action = "continue_in_visible_browser"
            event_type = "autofill_completed"
            event_notes = "Completed a visible browser autofill session and left the browser open for manual review."
            promote_job_status_if_needed(db, job.id, "autofill_completed", notes=event_notes)
            db.refresh(job)
        else:
            summary_status = "no_fields_filled"
            success = False
            message = "CareerAgent opened the form and detected fields, but it did not safely fill any values."
            recommended_next_action = "Review the field results, generate a packet if files are missing, or continue manually in the visible browser."
            event_type = "autofill_no_fields_filled"
            event_notes = "Detected fields but did not safely fill any values."

        summary = {
            "success": success,
            "autofill_effective": autofill_effective,
            "can_continue_in_browser": True,
            "job_id": job.id,
            "packet_id": packet.id if packet else None,
            "status": summary_status,
            "mode": "visible_review",
            "session_mode": "visible_review",
            "session_id": session_id,
            "browser_mode": "headed",
            "opened_url": page.url,
            "fields_detected": len(fields_detected),
            "fields_filled": fields_filled,
            "fields_skipped": max(len(fields_detected) - fields_filled, 0),
            "files_uploaded": files_uploaded,
            "blocked_actions": blocked_actions,
            "warnings": warnings,
            "manual_review_required": True,
            "message": message,
            "no_fields_reason": NO_FIELDS_REASON if not fields_detected else None,
            "recommended_next_action": recommended_next_action,
            "screenshot_path": None,
            "screenshot_url": None,
            "manual_values": manual_values,
            "field_results": field_results,
        }

        log_event(
            db,
            job_id=job.id,
            packet_id=packet.id if packet else None,
            event_type=event_type,
            notes=event_notes,
            old_status=initial_status,
            new_status=job.application_status,
            metadata_json={
                "browser_mode": summary["browser_mode"],
                "opened_url": summary["opened_url"],
                "session_id": session_id,
                "session_mode": "visible_review",
                "can_continue_in_browser": True,
                "fields_detected": summary["fields_detected"],
                "fields_filled": summary["fields_filled"],
                "fields_attempted": fields_attempted,
                "files_uploaded": summary["files_uploaded"],
                "blocked_actions": summary["blocked_actions"],
                "application_status_advanced": bool(autofill_effective),
            },
        )
        save_session_summary(summary)
        return summary
    except AutofillError:
        raise
    except playwright_error_type as exc:
        if _is_browser_closed_error(exc):
            summary = _browser_closed_summary(
                job=job,
                packet=packet,
                warnings=warnings,
                manual_values=manual_values,
                fields_detected=len(fields_detected),
                fields_filled=fields_filled,
                fields_skipped=max(len(fields_detected) - fields_filled, 0),
                files_uploaded=files_uploaded,
                blocked_actions=blocked_actions,
                field_results=field_results,
            )
            save_session_summary(summary)
            return summary
        if _is_chromium_missing_error(exc):
            summary = _chromium_missing_summary(
                job=job,
                packet=packet,
                session_mode="visible_review",
                browser_mode="headed",
                warnings=warnings,
                manual_values=manual_values,
                fields_detected=len(fields_detected),
                fields_filled=fields_filled,
                fields_skipped=max(len(fields_detected) - fields_filled, 0),
                files_uploaded=files_uploaded,
                blocked_actions=blocked_actions,
                field_results=field_results,
            )
            save_session_summary(summary)
            return summary
        if _is_browser_display_error(exc):
            summary = {
                "success": False,
                "autofill_effective": False,
                "can_continue_in_browser": False,
                "job_id": job.id,
                "packet_id": packet.id if packet else None,
                "status": "browser_display_unavailable",
                "mode": "visible_review",
                "session_mode": "visible_review",
                "session_id": None,
                "browser_mode": "headed",
                "opened_url": job.url,
                "fields_detected": len(fields_detected),
                "fields_filled": fields_filled,
                "fields_skipped": max(len(fields_detected) - fields_filled, 0),
                "files_uploaded": files_uploaded,
                "blocked_actions": blocked_actions,
                "warnings": warnings,
                "manual_review_required": True,
                "message": DISPLAY_UNAVAILABLE_MESSAGE,
                "suggested_fix": DISPLAY_UNAVAILABLE_FIX,
                "recommended_next_action": DISPLAY_UNAVAILABLE_FIX,
                "manual_values": manual_values,
                "field_results": field_results,
            }
            save_session_summary(summary)
            return summary
        raise AutofillUnavailableError(_concise_playwright_error(exc)) from exc
    except Exception as exc:
        raise AutofillError(f"Visible autofill could not complete safely: {exc}") from exc
    finally:
        if not session_stored:
            for resource in (context_manager, browser):
                if resource is None:
                    continue
                try:
                    resource.close()
                except Exception:
                    pass
            if playwright_manager is not None:
                try:
                    if hasattr(playwright_manager, "stop"):
                        playwright_manager.stop()
                    elif hasattr(playwright_manager, "__exit__"):
                        playwright_manager.__exit__(None, None, None)
                except Exception:
                    pass
            _stop_xvfb_if_needed(xvfb_process, previous_display)
        if started_logged and not session_stored:
            save_session_summary(
                {
                    "success": False,
                    "autofill_effective": False,
                    "can_continue_in_browser": False,
                    "job_id": job.id,
                    "packet_id": packet.id if packet else None,
                    "status": "visible_session_failed",
                    "mode": "visible_review",
                    "session_mode": "visible_review",
                    "session_id": None,
                    "browser_mode": "headed",
                    "opened_url": job.url,
                    "fields_detected": len(fields_detected),
                    "fields_filled": fields_filled,
                    "fields_skipped": max(len(fields_detected) - fields_filled, 0),
                    "files_uploaded": files_uploaded,
                    "blocked_actions": blocked_actions,
                    "warnings": warnings,
                    "manual_review_required": True,
                    "message": "Visible autofill started but did not reach a clean handoff state.",
                    "manual_values": manual_values,
                    "field_results": field_results,
                }
            )


def start_autofill_session(
    db: Session,
    job_id: int,
    packet_id: int | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_options = dict(options or {})
    context = _prepare_autofill_context(db, job_id, packet_id=packet_id, options=resolved_options)
    job: Job = context["job"]
    packet: ApplicationPacket | None = context["packet"]
    values: dict[str, Any] = context["values"]
    profile: dict[str, Any] = context["profile"]
    manual_values = _manual_values(values)
    warnings: list[str] = list(context["warnings"])

    support_status = _get_playwright_support_status()
    session_mode = _resolve_session_mode(resolved_options)
    headless = session_mode == "headless_test"
    browser_mode = "headless" if headless else "headed"
    keep_open_seconds = _keep_open_seconds_for_visible_mode(resolved_options) if session_mode == "visible_review" else 0
    cleanup_closed_sessions()
    cleanup_expired_sessions(settings.playwright_keep_open_seconds)

    if session_mode == "visible_review" and settings.playwright_headless:
        summary = {
            "success": False,
            "autofill_effective": False,
            "can_continue_in_browser": False,
            "job_id": job.id,
            "packet_id": packet.id if packet else None,
            "status": "visible_browser_required",
            "mode": "visible_review",
            "session_mode": session_mode,
            "browser_mode": browser_mode,
            "opened_url": job.url,
            "fields_detected": 0,
            "fields_filled": 0,
            "fields_skipped": 0,
            "files_uploaded": [],
            "blocked_actions": [],
            "warnings": warnings,
            "manual_review_required": True,
            "message": VISIBLE_UNAVAILABLE_MESSAGE,
            "suggested_fix": VISIBLE_UNAVAILABLE_FIX,
            "recommended_next_action": "open_in_browser_or_run_visible_local_backend",
            "manual_values": manual_values,
            "field_results": [],
        }
        save_session_summary(summary)
        return summary

    if not support_status["playwright_installed"]:
        raise AutofillUnavailableError(
            "Playwright is not installed in this environment. Rebuild the backend with the new dependency and run 'python -m playwright install chromium'."
        )

    sync_playwright, PlaywrightError, PlaywrightTimeoutError = _load_playwright()

    initial_status = job.application_status
    if session_mode == "visible_review":
        return _start_visible_review_session(
            db=db,
            job=job,
            packet=packet,
            values=values,
            profile=profile,
            manual_values=manual_values,
            warnings=warnings,
            resolved_options=resolved_options,
            sync_playwright=sync_playwright,
            playwright_error_type=PlaywrightError,
            playwright_timeout_error_type=PlaywrightTimeoutError,
            initial_status=initial_status,
        )

    started_logged = False
    completed_logged = False
    fields_detected: list[dict[str, Any]] = []
    field_results: list[dict[str, Any]] = []
    blocked_actions: list[str] = []
    files_uploaded: list[str] = []
    fields_filled = 0
    fields_attempted = 0
    screenshot_path: str | None = None
    warnings.append(HEADLESS_REVIEW_MESSAGE if headless else HEADED_REVIEW_MESSAGE)

    try:
        with _xvfb_session_if_needed(headless), sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=headless,
                slow_mo=settings.playwright_slow_mo_ms,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context_manager = browser.new_context()
            page = context_manager.new_page()

            if headless:
                log_event(
                    db,
                    job_id=job.id,
                    packet_id=packet.id if packet else None,
                    event_type="autofill_diagnostic_started",
                    notes="Started a headless autofill diagnostic test. Application status was not advanced.",
                    old_status=initial_status,
                    new_status=initial_status,
                    metadata_json={
                        "url": job.url,
                        "packet_id": packet.id if packet else None,
                        "session_mode": session_mode,
                        "diagnostic": True,
                    },
                )
            else:
                promote_job_status_if_needed(db, job.id, "autofill_started", notes="Started a visible browser autofill session.")
                db.refresh(job)
                log_event(
                    db,
                    job_id=job.id,
                    packet_id=packet.id if packet else None,
                    event_type="autofill_started",
                    notes="Started a visible browser autofill session.",
                    old_status=initial_status,
                    new_status=job.application_status,
                    metadata_json={"url": job.url, "packet_id": packet.id if packet else None, "session_mode": session_mode},
                )
            started_logged = True

            try:
                page.goto(_browser_navigation_url(job.url), wait_until="domcontentloaded", timeout=settings.autofill_navigation_timeout_ms)
            except PlaywrightTimeoutError as exc:
                raise AutofillUnavailableError(
                    "The application page did not finish loading before the timeout. The site may be slow, blocked, or require login."
                ) from exc

            warnings.extend(_detect_page_warnings(page))
            fields_detected = detect_form_fields(page)
            blocked_actions = _detect_blocked_actions(page)
            apply_actions = _detect_apply_actions(page)
            for action in apply_actions:
                if action not in blocked_actions:
                    blocked_actions.append(action)
            screenshot_path = _capture_screenshot(page, job.id, "page-loaded", warnings) if headless else None

            if _is_workday_url(job.url):
                warnings.append(
                    "This appears to be a Workday job page. Workday job-detail pages often do not expose application form fields until the user proceeds manually."
                )

            if not fields_detected:
                if _is_workday_url(job.url) and apply_actions:
                    warnings.append(
                        "An Apply button or link was found on this Workday page, but CareerAgent did not click it automatically."
                    )
                warnings.append(NO_FIELDS_REASON)
                if not headless:
                    _hold_visible_browser_for_review(page, keep_open_seconds, warnings)
                summary = {
                    "success": False,
                    "autofill_effective": False,
                    "can_continue_in_browser": not headless,
                    "job_id": job.id,
                    "packet_id": packet.id if packet else None,
                    "status": "no_fields_detected",
                    "session_mode": session_mode,
                    "browser_mode": browser_mode,
                    "opened_url": page.url,
                    "fields_detected": 0,
                    "fields_filled": 0,
                    "fields_skipped": 0,
                    "files_uploaded": files_uploaded,
                    "blocked_actions": blocked_actions,
                    "warnings": warnings,
                    "manual_review_required": True,
                    "message": NO_FIELDS_MESSAGE,
                    "no_fields_reason": NO_FIELDS_REASON,
                    "recommended_next_action": (
                        "Open this Workday job in your default browser and proceed manually to the application form, "
                        "or save the direct application form URL in CareerAgent."
                        if _is_workday_url(job.url)
                        else NO_FIELDS_NEXT_ACTION
                    ),
                    "screenshot_path": screenshot_path,
                    "screenshot_url": _screenshot_url(screenshot_path),
                    "manual_values": manual_values,
                    "field_results": field_results,
                }
                log_event(
                    db,
                    job_id=job.id,
                    packet_id=packet.id if packet else None,
                    event_type="autofill_no_fields_detected",
                    notes=NO_FIELDS_MESSAGE,
                    old_status=initial_status,
                    new_status=job.application_status,
                    metadata_json={
                        "browser_mode": summary["browser_mode"],
                        "opened_url": summary["opened_url"],
                        "blocked_actions": summary["blocked_actions"],
                        "warnings": summary["warnings"],
                        "screenshot_path": screenshot_path,
                    },
                )
                completed_logged = True
                save_session_summary(summary)
                context_manager.close()
                browser.close()
                return summary

            field_results, fields_filled, fields_attempted, files_uploaded = _fill_safe_fields(
                page=page,
                fields_detected=fields_detected,
                values=values,
                job=job,
                profile=profile,
                warnings=warnings,
                allow_sensitive_optional=bool(resolved_options.get("fill_sensitive_optional_fields")),
                ai_assisted_apply=bool(resolved_options.get("ai_assisted_apply")),
                user_triggered=bool(resolved_options.get("user_triggered", True)),
                headless=headless,
                playwright_error_type=PlaywrightError,
            )

            screenshot_path = _capture_screenshot(page, job.id, "after-attempt", warnings) if headless else screenshot_path
            autofill_effective = fields_filled > 0 or bool(files_uploaded)
            if autofill_effective and headless:
                summary_status = "headless_diagnostic_completed"
            elif autofill_effective:
                summary_status = "visible_autofill_completed"
            else:
                summary_status = "no_fields_filled"
            if not autofill_effective:
                warnings.append("CareerAgent detected fields but did not safely fill any of them. Review the field results and try the local test form or a direct application form URL.")
            if not headless:
                _hold_visible_browser_for_review(page, keep_open_seconds, warnings)
            summary = {
                "success": autofill_effective,
                "autofill_effective": autofill_effective,
                "can_continue_in_browser": not headless,
                "job_id": job.id,
                "packet_id": packet.id if packet else None,
                "status": summary_status,
                "session_mode": session_mode,
                "browser_mode": browser_mode,
                "opened_url": page.url,
                "fields_detected": len(fields_detected),
                "fields_filled": fields_filled,
                "fields_skipped": max(len(fields_detected) - fields_filled, 0),
                "files_uploaded": files_uploaded,
                "blocked_actions": blocked_actions,
                "warnings": warnings,
                "manual_review_required": True,
                "message": (
                    (HEADLESS_REVIEW_MESSAGE if headless else DEFAULT_REVIEW_MESSAGE)
                    if autofill_effective
                    else "CareerAgent opened the form and detected fields, but it did not safely fill any values."
                ),
                "recommended_next_action": (
                    "run_visible_autofill_or_open_default_browser"
                    if autofill_effective and headless
                    else None
                    if autofill_effective
                    else "Review the field results, generate a packet if files are missing, or use Open in Browser."
                ),
                "screenshot_path": screenshot_path,
                "screenshot_url": _screenshot_url(screenshot_path),
                "manual_values": manual_values,
                "field_results": field_results,
            }

            status_before_completion = job.application_status
            if autofill_effective and not headless:
                promote_job_status_if_needed(db, job.id, "autofill_completed", notes="Completed a visible browser autofill session.")
                db.refresh(job)
            log_event(
                db,
                job_id=job.id,
                packet_id=packet.id if packet else None,
                event_type=(
                    "autofill_diagnostic_completed"
                    if autofill_effective and headless
                    else "autofill_completed"
                    if autofill_effective
                    else "autofill_no_fields_filled"
                ),
                notes=(
                    "Completed a headless autofill diagnostic test. Application status was not advanced."
                    if autofill_effective and headless
                    else "Completed a visible browser autofill session."
                    if autofill_effective
                    else "Detected fields but did not safely fill any values."
                ),
                old_status=status_before_completion if started_logged else initial_status,
                new_status=job.application_status,
                metadata_json={
                    "browser_mode": summary["browser_mode"],
                    "fields_detected": summary["fields_detected"],
                    "fields_filled": summary["fields_filled"],
                    "fields_attempted": fields_attempted,
                    "files_uploaded": summary["files_uploaded"],
                    "blocked_actions": summary["blocked_actions"],
                    "screenshot_path": screenshot_path,
                    "session_mode": session_mode,
                    "diagnostic": headless,
                    "application_status_advanced": bool(autofill_effective and not headless),
                },
            )
            completed_logged = True
            save_session_summary(summary)
            context_manager.close()
            browser.close()
            return summary
    except AutofillError:
        raise
    except PlaywrightTimeoutError as exc:
        raise AutofillUnavailableError("The browser timed out while interacting with the application page.") from exc
    except PlaywrightError as exc:
        if _is_chromium_missing_error(exc):
            summary = _chromium_missing_summary(
                job=job,
                packet=packet,
                session_mode=session_mode,
                browser_mode=browser_mode,
                warnings=warnings,
                manual_values=manual_values,
                fields_detected=len(fields_detected),
                fields_filled=fields_filled,
                fields_skipped=max(len(fields_detected) - fields_filled, 0),
                files_uploaded=files_uploaded,
                blocked_actions=blocked_actions,
                field_results=field_results,
            )
            save_session_summary(summary)
            return summary
        if _is_browser_display_error(exc):
            summary = {
                "success": False,
                "autofill_effective": False,
                "can_continue_in_browser": False,
                "job_id": job.id,
                "packet_id": packet.id if packet else None,
                "status": "browser_display_unavailable",
                "session_mode": session_mode,
                "browser_mode": browser_mode,
                "opened_url": job.url,
                "fields_detected": len(fields_detected),
                "fields_filled": fields_filled,
                "fields_skipped": max(len(fields_detected) - fields_filled, 0),
                "files_uploaded": files_uploaded,
                "blocked_actions": blocked_actions,
                "warnings": warnings,
                "manual_review_required": True,
                "message": DISPLAY_UNAVAILABLE_MESSAGE,
                "suggested_fix": DISPLAY_UNAVAILABLE_FIX,
                "recommended_next_action": DISPLAY_UNAVAILABLE_FIX,
                "manual_values": manual_values,
                "field_results": field_results,
            }
            save_session_summary(summary)
            return summary
        raise AutofillUnavailableError(_concise_playwright_error(exc)) from exc
    except Exception as exc:
        raise AutofillError(f"Autofill could not complete safely: {exc}") from exc
    finally:
        if started_logged and not completed_logged:
            save_session_summary(
                {
                    "success": False,
                    "autofill_effective": False,
                    "can_continue_in_browser": False,
                    "job_id": job.id,
                    "packet_id": packet.id if packet else None,
                    "status": "headless_autofill_test_started" if headless else "autofill_started",
                    "session_mode": session_mode,
                    "browser_mode": browser_mode,
                    "opened_url": job.url,
                    "fields_detected": len(fields_detected),
                    "fields_filled": fields_filled,
                    "fields_skipped": max(len(fields_detected) - fields_filled, 0),
                    "files_uploaded": files_uploaded,
                    "blocked_actions": blocked_actions,
                    "warnings": warnings,
                    "manual_review_required": True,
                    "message": "Autofill started but did not reach a clean completion state. Review the browser and tracker logs manually.",
                    "manual_values": manual_values,
                    "field_results": field_results,
                }
            )
