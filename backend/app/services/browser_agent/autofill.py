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
from app.services.profile.profile_store import load_profile_document
from app.services.resume import compile_latex_file, load_resume_document
from app.services.tracker import log_event, promote_job_status_if_needed

from .field_detector import SENSITIVE_FIELD_KEYS, detect_form_fields
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
    "Fill Application requires a visible browser session so you can continue from the filled form. "
    "The current Docker backend is running headless, so it cannot hand off a live browser. "
    "Use Open in Browser, or run the backend locally with PLAYWRIGHT_HEADLESS=false."
)
VISIBLE_UNAVAILABLE_FIX = "Run the backend locally outside Docker with PLAYWRIGHT_HEADLESS=false and a display, then retry visible autofill."
NO_FIELDS_MESSAGE = "CareerAgent opened the page, but no application form fields were detected."
NO_FIELDS_REASON = (
    "This may be a job detail page, a JavaScript-heavy page, a page requiring login, or not the actual application form."
)
NO_FIELDS_NEXT_ACTION = "Use Open in Browser or navigate to the actual application form manually."
DISPLAY_UNAVAILABLE_MESSAGE = (
    "Headed Chromium cannot launch because the Docker container has no X server/display. "
    "Set PLAYWRIGHT_HEADLESS=true or run the backend locally with a display."
)
DISPLAY_UNAVAILABLE_FIX = "Use headless mode in Docker, or run backend locally outside Docker for visible browser autofill."
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


def build_autofill_values(profile: dict[str, Any], packet: ApplicationPacket | None, job: Job) -> dict[str, Any]:
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

    for field_key, source_value in {
        "email": personal.get("email"),
        "phone": personal.get("phone"),
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
        "linkedin": links.get("linkedin"),
        "github": links.get("github"),
        "portfolio": _first_non_empty(links.get("portfolio"), links.get("website")),
        "website": _first_non_empty(links.get("website"), links.get("portfolio")),
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

    profile_only_answer_keys = {
        "work_authorized_us",
        "need_sponsorship_now",
        "need_sponsorship_future",
        "willing_to_relocate",
    }
    prompt_answers = {
        key: value
        for key, value in _load_packet_question_answers(packet).items()
        if key not in profile_only_answer_keys
    }
    values.update({key: value for key, value in prompt_answers.items() if _first_non_empty(value)})

    if not values.get("why_company"):
        relevant_skills = _summarize_relevant_skills(job, profile)
        values["why_company"] = (
            f"I'm interested in {job.company} because the {job.title} role overlaps with work I'm already pursuing, "
            f"especially around {relevant_skills}. I would still review the company mission and team context manually before submitting."
        )

    if not values.get("tell_us_about_yourself"):
        current_focus = _first_non_empty(education.get("degree"), ", ".join(profile.get("target_roles") or []), "the work in my resume")
        relevant_skills = _summarize_relevant_skills(job, profile)
        values["tell_us_about_yourself"] = (
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
    values = build_autofill_values(dict(profile_document.get("profile") or {}), packet, job)
    warnings: list[str] = []

    if profile_document.get("source") == "example":
        warnings.append("CareerAgent is using the safe example profile. Review every autofill value before using it on a real application.")

    if packet is None:
        warnings.append("No application packet exists. Generate a packet first to upload tailored resume/cover letter.")

    files_available: list[str] = []
    if values.get("resume_upload"):
        files_available.append(str(values["resume_upload"]))
    elif resolved_options.get("allow_base_resume_upload"):
        base_resume_upload, compile_warnings = _compile_base_resume_for_upload()
        warnings.extend(compile_warnings)
        if base_resume_upload:
            values["resume_upload"] = base_resume_upload
            files_available.append(base_resume_upload)
    else:
        warnings.append("No tailored_resume.pdf available. Compile PDF or use manual upload.")

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
    process: subprocess.Popen[bytes] | None = None
    previous_display = os.getenv("DISPLAY")
    launch_is_headless = settings.playwright_headless if headless is None else headless

    if launch_is_headless or not settings.playwright_use_xvfb or previous_display:
        yield
        return

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
    try:
        yield
    finally:
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
        chromium_installed = False

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
    return bool(
        not settings.playwright_headless
        and support_status.get("playwright_installed")
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
    elif browser_mode == "headless" or visible_autofill_available:
        status = "ready"
    else:
        status = "environment_warning"

    if browser_mode == "headless":
        message = (
            "CareerAgent is configured for headless diagnostics. Fill Application requires a visible local browser, "
            "so use Open in Browser or run the backend locally with PLAYWRIGHT_HEADLESS=false."
        )
        environment_note = (
            "Docker on macOS usually has no X server/display, so Docker defaults to PLAYWRIGHT_HEADLESS=true. "
            "Run the backend locally with PLAYWRIGHT_HEADLESS=false for Fill Application."
        )
    else:
        message = (
            "CareerAgent is configured for visible browser autofill. It fills safe high-confidence fields and always stops before final submit."
        )
        environment_note = (
            "Headed Chromium requires a display/XServer. If it fails in Docker, set PLAYWRIGHT_HEADLESS=true or run the backend locally outside Docker."
        )

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
        if not _choice_matches_boolean(field, desired_value):
            return False, "This option does not match the desired yes/no answer."
        locator.check()
        return True, "Selected the matching choice."

    if field_key == "phone":
        locator.fill(str(desired_value))
        return True, "Filled phone field."

    locator.fill(str(desired_value))
    return True, "Filled text field."


def _fill_safe_fields(
    *,
    page: Any,
    fields_detected: list[dict[str, Any]],
    values: dict[str, Any],
    warnings: list[str],
    allow_sensitive_optional: bool,
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
        label = _first_non_empty(field.get("label_text"), field.get("placeholder"), field.get("name"), field.get("id"), field_key)
        confidence = float(field.get("confidence") or 0.0)
        value = values.get(field_key)
        safe_to_fill = bool(field.get("safe_to_fill"))

        if field_key in SKIPPED_ALWAYS_FIELD_KEYS:
            field_results.append(
                {
                    "field_key": field_key,
                    "label": label,
                    "selector": field.get("selector"),
                    "filled": False,
                    "confidence": confidence,
                    "reason": "Sensitive field skipped by policy.",
                }
            )
            continue

        if field_key in SENSITIVE_OPTIONAL_FIELD_KEYS and not allow_sensitive_optional:
            field_results.append(
                {
                    "field_key": field_key,
                    "label": label,
                    "selector": field.get("selector"),
                    "filled": False,
                    "confidence": confidence,
                    "reason": "Sensitive optional field skipped unless explicitly enabled.",
                }
            )
            continue

        if field_key in SENSITIVE_OPTIONAL_FIELD_KEYS and allow_sensitive_optional:
            safe_to_fill = True

        if not safe_to_fill:
            field_results.append(
                {
                    "field_key": field_key,
                    "label": label,
                    "selector": field.get("selector"),
                    "filled": False,
                    "confidence": confidence,
                    "reason": str(field.get("reason") or "Field not considered safe to autofill."),
                }
            )
            continue

        if confidence < HIGH_CONFIDENCE_THRESHOLD:
            field_results.append(
                {
                    "field_key": field_key,
                    "label": label,
                    "selector": field.get("selector"),
                    "filled": False,
                    "confidence": confidence,
                    "reason": "Confidence below the Stage 8 autofill threshold.",
                }
            )
            continue

        if value in (None, "", []):
            field_results.append(
                {
                    "field_key": field_key,
                    "label": label,
                    "selector": field.get("selector"),
                    "filled": False,
                    "confidence": confidence,
                    "reason": "No truthful value was available for this field.",
                }
            )
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

        field_results.append(
            {
                "field_key": field_key,
                "label": label,
                "selector": field.get("selector"),
                "filled": filled,
                "confidence": confidence,
                "reason": reason,
            }
        )

    return field_results, fields_filled, fields_attempted, files_uploaded


def _start_visible_review_session(
    *,
    db: Session,
    job: Job,
    packet: ApplicationPacket | None,
    values: dict[str, Any],
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
        with _xvfb_session_if_needed(False):
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
            fields_detected = detect_form_fields(page)
            blocked_actions = _detect_blocked_actions(page)
            apply_actions = _detect_apply_actions(page)
            for action in apply_actions:
                if action not in blocked_actions:
                    blocked_actions.append(action)

            if _is_workday_url(job.url):
                warnings.append(
                    "This appears to be a Workday job page. Workday job-detail pages often do not expose application form fields until the user proceeds manually."
                )

            if fields_detected:
                field_results, fields_filled, fields_attempted, files_uploaded = _fill_safe_fields(
                    page=page,
                    fields_detected=fields_detected,
                    values=values,
                    warnings=warnings,
                    allow_sensitive_optional=bool(resolved_options.get("fill_sensitive_optional_fields")),
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
            )
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

            allow_sensitive_optional = bool(resolved_options.get("fill_sensitive_optional_fields"))
            if headless and allow_sensitive_optional:
                warnings.append("Headless mode skips sensitive optional fields even when optional EEO autofill is requested.")
                allow_sensitive_optional = False

            for field in fields_detected:
                field_key = str(field.get("field_key") or "unknown_question")
                label = _first_non_empty(field.get("label_text"), field.get("placeholder"), field.get("name"), field.get("id"), field_key)
                confidence = float(field.get("confidence") or 0.0)
                value = values.get(field_key)
                safe_to_fill = bool(field.get("safe_to_fill"))

                if field_key in SKIPPED_ALWAYS_FIELD_KEYS:
                    field_results.append(
                        {
                            "field_key": field_key,
                            "label": label,
                            "selector": field.get("selector"),
                            "filled": False,
                            "confidence": confidence,
                            "reason": "Sensitive field skipped by policy.",
                        }
                    )
                    continue

                if field_key in SENSITIVE_OPTIONAL_FIELD_KEYS and not allow_sensitive_optional:
                    field_results.append(
                        {
                            "field_key": field_key,
                            "label": label,
                            "selector": field.get("selector"),
                            "filled": False,
                            "confidence": confidence,
                            "reason": "Sensitive optional field skipped unless explicitly enabled.",
                        }
                    )
                    continue

                if field_key in SENSITIVE_OPTIONAL_FIELD_KEYS and allow_sensitive_optional:
                    safe_to_fill = True

                if not safe_to_fill:
                    field_results.append(
                        {
                            "field_key": field_key,
                            "label": label,
                            "selector": field.get("selector"),
                            "filled": False,
                            "confidence": confidence,
                            "reason": str(field.get("reason") or "Field not considered safe to autofill."),
                        }
                    )
                    continue

                if confidence < HIGH_CONFIDENCE_THRESHOLD:
                    field_results.append(
                        {
                            "field_key": field_key,
                            "label": label,
                            "selector": field.get("selector"),
                            "filled": False,
                            "confidence": confidence,
                            "reason": "Confidence below the Stage 8 autofill threshold.",
                        }
                    )
                    continue

                if value in (None, "", []):
                    field_results.append(
                        {
                            "field_key": field_key,
                            "label": label,
                            "selector": field.get("selector"),
                            "filled": False,
                            "confidence": confidence,
                            "reason": "No truthful value was available for this field.",
                        }
                    )
                    continue

                try:
                    fields_attempted += 1
                    filled, reason = _apply_value_to_field(page, field, value)
                except PlaywrightError as exc:
                    filled = False
                    reason = f"Browser interaction failed: {exc}"

                if filled:
                    fields_filled += 1
                    if field_key in {"resume_upload", "cover_letter_upload"}:
                        files_uploaded.append(Path(str(value)).name)

                field_results.append(
                    {
                        "field_key": field_key,
                        "label": label,
                        "selector": field.get("selector"),
                        "filled": filled,
                        "confidence": confidence,
                        "reason": reason,
                    }
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
