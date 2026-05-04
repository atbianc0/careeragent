from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_packet import ApplicationPacket
from app.models.job import Job
from app.services.profile.profile_store import load_profile_document
from app.services.resume import compile_latex_file, load_resume_document
from app.services.tracker import log_event, promote_job_status_if_needed

from .field_detector import SENSITIVE_FIELD_KEYS, detect_form_fields
from .safe_actions import BLOCKED_FINAL_SUBMIT_WORDS, should_block_element
from .session_store import get_recent_session_summaries, save_session_summary

HIGH_CONFIDENCE_THRESHOLD = 0.8
SENSITIVE_OPTIONAL_FIELD_KEYS = {"race_ethnicity", "gender", "disability", "veteran_status"}
SKIPPED_ALWAYS_FIELD_KEYS = {"ssn", "date_of_birth", "unknown_sensitive"}
DEFAULT_REVIEW_MESSAGE = (
    "Autofill completed. Please review everything manually. CareerAgent will not submit the application."
)


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
        "city": personal.get("city"),
        "state": _first_non_empty(personal.get("state"), personal.get("province"), personal.get("region")),
        "zip": _first_non_empty(personal.get("zip"), personal.get("postal_code")),
        "country": personal.get("country"),
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

    prompt_answers = _load_packet_question_answers(packet)
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
        warnings.append("No application packet exists for this job yet. CareerAgent can still preview basic profile fields, but there may be no uploadable files.")

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
        warnings.append("No tailored resume PDF is available to upload. Generate a packet with PDF compilation or explicitly allow a compiled base resume upload.")

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
        "files_available": context["files_available"],
        "warnings": context["warnings"],
        "manual_review_required": True,
        "message": "Preview ready. CareerAgent will only fill safe, high-confidence fields and will never submit the application.",
    }


def _get_playwright_support_status() -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return {
            "playwright_installed": False,
            "chromium_installed": False,
            "headed_browser_supported": False,
        }

    chromium_installed = False
    try:
        with sync_playwright() as playwright:
            executable_path = Path(playwright.chromium.executable_path)
            chromium_installed = executable_path.exists()
    except Exception:
        chromium_installed = False

    return {
        "playwright_installed": True,
        "chromium_installed": chromium_installed,
        "headed_browser_supported": chromium_installed,
    }


def get_autofill_status() -> dict[str, Any]:
    support_status = _get_playwright_support_status()
    status = "ready" if support_status["headed_browser_supported"] else "environment_warning"
    return {
        "status": status,
        "stage": "Stage 8 - Browser Autofill with Playwright",
        "message": "CareerAgent opens a visible Chromium browser, fills safe high-confidence fields, uploads packet files when available, and always stops before final submit.",
        "manual_review_required": True,
        "install_command": "python -m playwright install chromium",
        "environment_note": (
            "Headed Playwright sessions may need extra display setup in Docker on macOS. If the browser window does not appear, run the backend locally outside Docker for autofill testing."
        ),
        "recent_sessions": get_recent_session_summaries(),
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


def _detect_blocked_actions(page: Any) -> list[str]:
    raw_actions = page.evaluate(
        """
        () => Array.from(document.querySelectorAll("button, input[type=submit], input[type=button], [role='button']")).map((element) => ({
          text: (element.innerText || element.textContent || element.getAttribute("value") || element.getAttribute("aria-label") || "").trim(),
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
    warnings: list[str] = list(context["warnings"])

    support_status = _get_playwright_support_status()
    if not support_status["playwright_installed"]:
        raise AutofillUnavailableError(
            "Playwright is not installed in this environment. Rebuild the backend with the new dependency and run 'python -m playwright install chromium'."
        )
    if not support_status["chromium_installed"]:
        raise AutofillUnavailableError(
            "Chromium is not installed for Playwright in this environment. Run 'python -m playwright install chromium'."
        )

    sync_playwright, PlaywrightError, PlaywrightTimeoutError = _load_playwright()
    review_timeout_ms = max(settings.autofill_review_timeout_seconds, 0) * 1000

    initial_status = job.application_status
    started_logged = False
    completed_logged = False
    fields_detected: list[dict[str, Any]] = []
    field_results: list[dict[str, Any]] = []
    blocked_actions: list[str] = []
    files_uploaded: list[str] = []
    fields_filled = 0

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=False,
                slow_mo=settings.autofill_slow_mo_ms,
            )
            context_manager = browser.new_context()
            page = context_manager.new_page()

            promote_job_status_if_needed(db, job.id, "autofill_started", notes="Started a Stage 8 browser autofill session.")
            db.refresh(job)
            log_event(
                db,
                job_id=job.id,
                packet_id=packet.id if packet else None,
                event_type="autofill_started",
                notes="Started a Stage 8 browser autofill session.",
                old_status=initial_status,
                new_status=job.application_status,
                metadata_json={"url": job.url, "packet_id": packet.id if packet else None},
            )
            started_logged = True

            try:
                page.goto(job.url, wait_until="domcontentloaded", timeout=settings.autofill_navigation_timeout_ms)
            except PlaywrightTimeoutError as exc:
                raise AutofillUnavailableError(
                    "The application page did not finish loading before the timeout. The site may be slow, blocked, or require login."
                ) from exc

            warnings.extend(_detect_page_warnings(page))
            fields_detected = detect_form_fields(page)
            blocked_actions = _detect_blocked_actions(page)

            allow_sensitive_optional = bool(resolved_options.get("fill_sensitive_optional_fields"))

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

            if review_timeout_ms > 0:
                page.wait_for_timeout(review_timeout_ms)

            summary_status = "autofill_completed"
            summary = {
                "job_id": job.id,
                "packet_id": packet.id if packet else None,
                "status": summary_status,
                "opened_url": page.url,
                "fields_detected": len(fields_detected),
                "fields_filled": fields_filled,
                "fields_skipped": max(len(fields_detected) - fields_filled, 0),
                "files_uploaded": files_uploaded,
                "blocked_actions": blocked_actions,
                "warnings": warnings,
                "manual_review_required": True,
                "message": DEFAULT_REVIEW_MESSAGE,
                "field_results": field_results,
            }

            status_before_completion = job.application_status
            promote_job_status_if_needed(db, job.id, "autofill_completed", notes="Completed a Stage 8 browser autofill session.")
            db.refresh(job)
            log_event(
                db,
                job_id=job.id,
                packet_id=packet.id if packet else None,
                event_type="autofill_completed",
                notes="Completed a Stage 8 browser autofill session.",
                old_status=status_before_completion if started_logged else initial_status,
                new_status=job.application_status,
                metadata_json={
                    "fields_detected": summary["fields_detected"],
                    "fields_filled": summary["fields_filled"],
                    "files_uploaded": summary["files_uploaded"],
                    "blocked_actions": summary["blocked_actions"],
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
        raise AutofillUnavailableError(f"Playwright could not complete the autofill session: {exc}") from exc
    except Exception as exc:
        raise AutofillError(f"Autofill could not complete safely: {exc}") from exc
    finally:
        if started_logged and not completed_logged:
            save_session_summary(
                {
                    "job_id": job.id,
                    "packet_id": packet.id if packet else None,
                    "status": "autofill_started",
                    "opened_url": job.url,
                    "fields_detected": len(fields_detected),
                    "fields_filled": fields_filled,
                    "fields_skipped": max(len(fields_detected) - fields_filled, 0),
                    "files_uploaded": files_uploaded,
                    "blocked_actions": blocked_actions,
                    "warnings": warnings,
                    "manual_review_required": True,
                    "message": "Autofill started but did not reach a clean completion state. Review the browser and tracker logs manually.",
                    "field_results": field_results,
                }
            )
