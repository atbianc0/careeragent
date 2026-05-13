from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.application_packet import ApplicationPacket
from app.schemas.job import (
    JobImportRequest,
    JobParseResult,
    JobRead,
    JobScoreResult,
    JobScoringResponse,
    JobUpdate,
    JobVerificationResponse,
    JobVerificationResult,
    RecommendationResponse,
    ScoreAllSummary,
    TopJobSummary,
    VerifyAllSummary,
    VerifyUrlRequest,
)
from app.services.jobs.job_store import create_job, delete_job, get_job, list_jobs, list_recommendations, update_job
from app.services.jobs.parser import parse_job_description, parse_job_url
from app.services.generator import generate_application_packet
from app.services.scoring import build_job_scoring_updates, score_saved_job
from app.services.browser_agent import AutofillError, get_autofill_status, preview_autofill_plan, start_autofill_session
from app.services.tracker import log_event, open_application_link, promote_job_status_if_needed, update_job_status
from app.services.verifier.verifier import build_job_verification_updates, verify_job_record, verify_job_url

router = APIRouter()


class StartAiAssistedApplyRequest(BaseModel):
    user_triggered: bool = True
    include_resume: bool = True
    include_cover_letter: bool = True
    include_application_answers: bool = True


class StartBasicAutofillRequest(BaseModel):
    user_triggered: bool = True
    allow_base_resume_upload: bool = True
    fill_sensitive_optional_fields: bool = False


class FillApplicationRequest(BaseModel):
    user_triggered: bool = True
    packet_id: int | None = None
    allow_base_resume_upload: bool = True
    fill_sensitive_optional_fields: bool = False
    keep_browser_open: bool = True
    ai_assisted_apply: bool = False


VISIBLE_AUTOFILL_SETUP_INSTRUCTIONS = [
    "A normal Chromium review window must be launched by a backend running on your host machine.",
    "Docker on macOS cannot open a native Chromium window you can continue from.",
    "Stop the Docker backend, run the backend locally with PLAYWRIGHT_HEADLESS=false, then return to Apply.",
]

VISIBLE_AUTOFILL_SETUP_COMMAND = (
    "cd backend && PLAYWRIGHT_HEADLESS=false python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
)
CHROMIUM_INSTALL_COMMAND = "cd backend && source .venv/bin/activate && python -m playwright install chromium"


def _latest_packet_for_job(db: Session, job_id: int) -> ApplicationPacket | None:
    return (
        db.query(ApplicationPacket)
        .filter(ApplicationPacket.job_id == job_id)
        .order_by(ApplicationPacket.generated_at.desc().nullslast(), ApplicationPacket.id.desc())
        .first()
    )


def _packet_manual_warnings(packet: ApplicationPacket | None) -> list[str]:
    if packet is None:
        return []

    warnings: list[str] = []
    if packet.generation_status == "completed_with_warnings" or packet.generation_error:
        warnings.append("Packet has warnings. Review before uploading manually.")
    if not packet.tailored_resume_pdf_path:
        warnings.append("Packet resume PDF is missing. Review before uploading manually.")
    return warnings


@router.get("", response_model=list[JobRead])
def jobs_index(
    status: str | None = None,
    role_category: str | None = None,
    source: str | None = None,
    search: str | None = None,
    saved_only: bool = False,
    applied_only: bool = False,
    db: Session = Depends(get_db),
) -> list[JobRead]:
    jobs = list_jobs(
        db,
        status=status,
        role_category=role_category,
        source=source,
        search=search,
    )
    saved_statuses = {
        "saved",
        "ready_to_apply",
        "verified_open",
        "packet_ready",
        "application_opened",
        "applying",
        "autofill_started",
        "autofill_completed",
    }
    applied_statuses = {"applied", "applied_manual", "interview", "rejected", "offer", "withdrawn", "closed_after_apply"}
    if saved_only:
        return [job for job in jobs if job.application_status in saved_statuses and job.applied_at is None]
    if applied_only:
        return [job for job in jobs if job.application_status in applied_statuses or job.applied_at is not None]
    return jobs


@router.post("/parse", response_model=JobParseResult)
def preview_job_parse(payload: JobImportRequest) -> JobParseResult:
    try:
        parsed_job = _parse_job_import(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _apply_import_source(parsed_job, payload)
    parsed_job["input_type"] = payload.input_type
    return parsed_job


@router.post("/import", response_model=JobRead)
def import_job(payload: JobImportRequest, db: Session = Depends(get_db)) -> JobRead:
    try:
        parsed_job = _parse_job_import(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    parse_mode = str(parsed_job.pop("parse_mode", "rule_based") or "rule_based")
    parsing_provider = parsed_job.pop("provider", None)
    parsing_status = str(parsed_job.pop("parsing_status", "full") or "full")
    parsing_warnings = list(parsed_job.pop("parsing_warnings", []) or [])
    raw_parsed_data = dict(parsed_job.get("raw_parsed_data") or {})
    raw_parsed_data["parsing_mode"] = parse_mode
    raw_parsed_data["parsing_status"] = parsing_status
    raw_parsed_data["ai_provider"] = parsing_provider
    raw_parsed_data["parsing_warnings"] = parsing_warnings
    parsed_job["raw_parsed_data"] = raw_parsed_data
    _apply_import_source(parsed_job, payload)
    job = create_job(db, parsed_job)
    log_event(
        db,
        job_id=job.id,
        event_type="job_imported",
        notes=f"Imported job from {payload.input_type} input using {parse_mode} parsing.",
        new_status=job.application_status,
        metadata_json={
            "input_type": payload.input_type,
            "source": payload.source,
            "parse_mode": parse_mode,
            "parsing_status": parsing_status,
            "provider": parsing_provider,
            "parsing_warnings": parsing_warnings,
        },
    )
    log_event(
        db,
        job_id=job.id,
        event_type="job_saved",
        notes="Saved job from manual import.",
        new_status=job.application_status,
        metadata_json={"source": payload.source, "input_type": payload.input_type},
    )
    job, _, _, _ = _verify_and_score_saved_job(db, job, source_label="manual import")
    return job


@router.post("/{job_id}/apply/start-ai-assisted")
def start_ai_assisted_apply(
    job_id: int,
    payload: StartAiAssistedApplyRequest = StartAiAssistedApplyRequest(),
    db: Session = Depends(get_db),
) -> dict:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.")

    if not payload.user_triggered:
        raise HTTPException(status_code=400, detail="Start AI-assisted apply must be triggered by the user.")

    try:
        result = generate_application_packet(
            db,
            job_id,
            {
                "include_cover_letter": payload.include_cover_letter,
                "include_recruiter_message": False,
                "include_application_questions": payload.include_application_answers,
                "compile_resume_pdf": True,
                "use_ai": True,
                "ai_tasks": ["resume", "answers", "cover_letter"],
                "user_triggered": payload.user_triggered,
            },
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        if "was not found" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc

    packet = result["packet"]
    job = result["job"]
    metadata = dict(result.get("metadata") or {})
    warnings = list(metadata.get("ai_warnings") or [])
    ai_used = bool(metadata.get("api_used"))
    provider = metadata.get("provider") if isinstance(metadata.get("provider"), str) else None
    packet_status = str(getattr(packet, "generation_status", "") or "completed")
    if ai_used or provider == "mock":
        message = "AI-assisted application materials are ready to review. CareerAgent did not submit anything."
    else:
        message = "AI is disabled or unavailable. Created/reused a local packet. You can continue with Basic Autofill or enable AI in Settings."
    if packet_status == "completed_with_warnings":
        warnings.append(str(getattr(packet, "generation_error", "") or "Packet completed with warnings."))

    autofill_status = get_autofill_status()
    visible_available = bool(autofill_status.get("visible_autofill_available"))
    browser_mode = str(autofill_status.get("browser_mode") or "headless")
    configured_browser_mode = str(autofill_status.get("configured_browser_mode") or browser_mode)

    return jsonable_encoder({
        "success": True,
        "job_id": job.id,
        "packet_id": packet.id,
        "packet_status": packet_status,
        "ai_used": ai_used,
        "provider": provider,
        "message": message,
        "warnings": [warning for warning in dict.fromkeys(warnings) if warning],
        "visible_autofill_available": visible_available,
        "can_fill_application": visible_available,
        "browser_mode": browser_mode,
        "configured_browser_mode": configured_browser_mode,
        "setup_instructions": None if visible_available else VISIBLE_AUTOFILL_SETUP_INSTRUCTIONS,
        "setup_command": None if visible_available else VISIBLE_AUTOFILL_SETUP_COMMAND,
        "autofill_environment": autofill_status,
        "next_actions": ["review_packet", "fill_application" if visible_available else "setup_visible_autofill", "open_application", "mark_applied"],
        "packet": packet,
        "job": job,
    })


@router.post("/{job_id}/apply/start-basic-autofill")
def start_basic_autofill(
    job_id: int,
    payload: StartBasicAutofillRequest = StartBasicAutofillRequest(),
    db: Session = Depends(get_db),
) -> dict:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.")
    if not payload.user_triggered:
        raise HTTPException(status_code=400, detail="Start Basic Autofill must be triggered by the user.")
    packet = _latest_packet_for_job(db, job.id)
    if not (job.url or "").strip():
        return jsonable_encoder({
            "success": False,
            "status": "missing_application_url",
            "job_id": job.id,
            "job": job,
            "open_url": "",
            "packet_id": packet.id if packet else None,
            "packet_status": packet.generation_status if packet else "No packet available",
            "upload_status": "No upload possible without an application URL.",
            "visible_autofill_available": False,
            "can_fill_application": False,
            "can_open_in_browser": False,
            "browser_mode": "headless",
            "configured_browser_mode": "headless",
            "manual_review_required": True,
            "message": "This job does not have an application URL.",
            "setup_instructions": None,
            "setup_command": None,
            "packet": packet,
            "manual_values": [],
            "files_available": [],
            "warnings": ["No application URL is saved for this job."],
            "next_actions": ["add_application_url", "mark_applied"],
        })

    autofill_status = get_autofill_status()
    visible_available = bool(autofill_status.get("visible_autofill_available"))
    browser_mode = str(autofill_status.get("browser_mode") or "headless")
    configured_browser_mode = str(autofill_status.get("configured_browser_mode") or browser_mode)
    setup_instructions = None if visible_available else VISIBLE_AUTOFILL_SETUP_INSTRUCTIONS
    manual_values: list[dict] = []
    files_available: list[str] = []
    warnings: list[str] = _packet_manual_warnings(packet)

    try:
        preview = preview_autofill_plan(
            db,
            job.id,
            packet_id=packet.id if packet else None,
            options={
                "allow_base_resume_upload": payload.allow_base_resume_upload,
                "fill_sensitive_optional_fields": payload.fill_sensitive_optional_fields,
            },
        )
        manual_values = list(preview.get("manual_values") or [])
        files_available = list(preview.get("files_available") or [])
        warnings.extend(str(warning) for warning in list(preview.get("warnings") or []) if warning)
    except Exception as exc:  # pragma: no cover - fallback data should not block opening the application
        warnings.append(f"Manual copy values could not be prepared: {exc}")

    if visible_available:
        message = "Basic autofill is ready. Use Fill Application for visible browser autofill, then submit manually."
        status = "ready"
    else:
        status = "manual_fallback_ready"
        if autofill_status.get("backend_runtime") == "docker" and browser_mode == "headed":
            message = (
                "PLAYWRIGHT_HEADLESS=false was read, but Docker does not have a browser display. "
                "Set PLAYWRIGHT_USE_XVFB=true and run docker compose up --build."
            )
        else:
            message = (
                "Visible autofill is unavailable. Set PLAYWRIGHT_HEADLESS=false and PLAYWRIGHT_USE_XVFB=true, "
                "then run docker compose up --build."
            )
        if browser_mode == "headless":
            warnings.append(message)

    log_event(
        db,
        job_id=job.id,
        event_type="basic_autofill_prepared",
        notes="Prepared Basic Autofill options. CareerAgent did not submit anything.",
        old_status=job.application_status,
        new_status=job.application_status,
        metadata_json={
            "visible_autofill_available": visible_available,
            "browser_mode": browser_mode,
            "allow_base_resume_upload": payload.allow_base_resume_upload,
            "fill_sensitive_optional_fields": payload.fill_sensitive_optional_fields,
        },
    )

    return jsonable_encoder({
        "success": True,
        "status": status,
        "job_id": job.id,
        "job": job,
        "open_url": job.url,
        "packet_id": packet.id if packet else None,
        "packet_status": packet.generation_status if packet else "No packet available",
        "upload_status": (
            "A packet is available for file upload review." if packet else "No packet exists yet. Basic Autofill can still open the application."
        ),
        "visible_autofill_available": visible_available,
        "browser_mode": browser_mode,
        "configured_browser_mode": configured_browser_mode,
        "can_fill_application": visible_available,
        "can_open_in_browser": True,
        "manual_review_required": True,
        "message": message,
        "setup_instructions": setup_instructions,
        "setup_command": VISIBLE_AUTOFILL_SETUP_COMMAND if not visible_available else None,
        "packet": packet,
        "manual_values": manual_values,
        "files_available": files_available,
        "warnings": [warning for warning in dict.fromkeys(warnings) if warning],
        "next_actions": ["open_application", "fill_application" if visible_available else "setup_visible_autofill", "mark_applied"],
    })


@router.post("/{job_id}/apply/fill-application")
def fill_application(
    job_id: int,
    payload: FillApplicationRequest = FillApplicationRequest(),
    db: Session = Depends(get_db),
) -> dict:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.")
    if not payload.user_triggered:
        raise HTTPException(status_code=400, detail="Fill Application must be triggered by the user.")
    if not (job.url or "").strip():
        return jsonable_encoder({
            "success": False,
            "status": "missing_application_url",
            "job_id": job.id,
            "packet_id": payload.packet_id,
            "can_continue_in_browser": False,
            "browser_mode": "headless",
            "opened_url": "",
            "fields_detected": 0,
            "fields_filled": 0,
            "fields_skipped": 0,
            "files_uploaded": [],
            "blocked_actions": [],
            "blocked_final_actions": [],
            "warnings": ["No application URL is saved for this job."],
            "manual_review_required": True,
            "message": "This job does not have an application URL.",
            "setup_instructions": [],
            "manual_values": [],
            "field_results": [],
        })

    autofill_status = get_autofill_status()
    browser_mode = str(autofill_status.get("browser_mode") or "headless")
    if not bool(autofill_status.get("chromium_installed")):
        return jsonable_encoder({
            "success": False,
            "status": "chromium_missing",
            "job_id": job.id,
            "packet_id": payload.packet_id,
            "can_continue_in_browser": False,
            "browser_mode": browser_mode,
            "opened_url": job.url,
            "fields_detected": 0,
            "fields_filled": 0,
            "fields_skipped": 0,
            "files_uploaded": [],
            "blocked_actions": [],
            "blocked_final_actions": [],
            "warnings": [],
            "manual_review_required": True,
            "message": "Chromium is not installed for Playwright in the current backend environment.",
            "setup_command": CHROMIUM_INSTALL_COMMAND,
            "setup_instructions": VISIBLE_AUTOFILL_SETUP_INSTRUCTIONS,
            "manual_values": [],
            "field_results": [],
        })
    if not bool(autofill_status.get("visible_autofill_available")):
        return jsonable_encoder({
            "success": False,
            "status": "visible_browser_required",
            "job_id": job.id,
            "packet_id": payload.packet_id,
            "can_continue_in_browser": False,
            "browser_mode": browser_mode,
            "opened_url": job.url,
            "fields_detected": 0,
            "fields_filled": 0,
            "fields_skipped": 0,
            "files_uploaded": [],
            "blocked_actions": [],
            "blocked_final_actions": [],
            "warnings": [],
            "manual_review_required": True,
            "message": "Fill Application requires a normal Chromium window from a backend running on your Mac. Docker cannot open that native browser window.",
            "setup_command": VISIBLE_AUTOFILL_SETUP_COMMAND,
            "setup_instructions": VISIBLE_AUTOFILL_SETUP_INSTRUCTIONS,
            "manual_values": [],
            "field_results": [],
        })

    try:
        summary = start_autofill_session(
            db,
            job.id,
            packet_id=payload.packet_id,
            options={
                "mode": "visible_review",
                "keep_browser_open": payload.keep_browser_open,
                "allow_base_resume_upload": payload.allow_base_resume_upload,
                "fill_sensitive_optional_fields": payload.fill_sensitive_optional_fields,
                "ai_assisted_apply": payload.ai_assisted_apply,
                "user_triggered": payload.user_triggered,
            },
        )
    except AutofillError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    blocked_actions = list(summary.get("blocked_actions") or [])
    if summary.get("status") == "visible_session_started":
        summary["status"] = "visible_autofill_started"
        summary["message"] = "Visible Chromium is open and filled. Review missing fields and submit manually."
    if summary.get("status") == "playwright_chromium_missing":
        summary["status"] = "chromium_missing"
        summary["message"] = "Chromium is not installed for Playwright in the current backend environment."
        summary["setup_command"] = CHROMIUM_INSTALL_COMMAND
    summary["blocked_final_actions"] = blocked_actions
    summary["setup_instructions"] = VISIBLE_AUTOFILL_SETUP_INSTRUCTIONS if not summary.get("success") else []
    return jsonable_encoder(summary)


@router.post("/{job_id}/mark-applied")
def mark_job_applied(job_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        job, event = update_job_status(db, job_id, "applied_manual", notes="User confirmed they manually submitted the application.")
    except ValueError as exc:
        raise HTTPException(status_code=404 if "was not found" in str(exc) else 400, detail=str(exc)) from exc
    return jsonable_encoder({
        "job": job,
        "event": event,
        "message": "Marked applied after manual submission.",
    })


@router.post("/{job_id}/open-application")
def open_job_application(job_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        job, event, url = open_application_link(db, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "was not found" in str(exc) else 400, detail=str(exc)) from exc
    return jsonable_encoder({
        "success": True,
        "job_id": job.id,
        "job": job,
        "event": event,
        "url": url,
        "message": "Application opened. Complete it manually, then return and click Mark Applied.",
    })


@router.post("/verify-url", response_model=JobVerificationResult)
def verify_raw_job_url(payload: VerifyUrlRequest) -> JobVerificationResult:
    try:
        result = verify_job_url(
            payload.url,
            first_seen_date=payload.first_seen_date,
            posted_date=payload.posted_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _verification_response_from_result(result)


@router.post("/score-all", response_model=ScoreAllSummary)
def score_all_jobs(db: Session = Depends(get_db)) -> ScoreAllSummary:
    jobs = list_jobs(db)
    summary = {
        "total_jobs": len(jobs),
        "scored_count": 0,
        "skipped_count": 0,
        "average_resume_match_score": 0.0,
        "average_overall_priority_score": 0.0,
        "top_jobs": [],
        "errors": [],
    }

    scored_jobs: list = []
    for job in jobs:
        try:
            result = score_saved_job(job)
        except (FileNotFoundError, ValueError) as exc:
            summary["errors"].append(str(exc))
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive fallback for network/file edge cases
            summary["skipped_count"] += 1
            summary["errors"].append(f"Job {job.id}: {exc}")
            continue

        updated_job = update_job(db, job.id, build_job_scoring_updates(result))
        if updated_job is None:
            summary["skipped_count"] += 1
            summary["errors"].append(f"Job {job.id}: record disappeared before scoring could be saved.")
            continue
        log_event(
            db,
            job_id=updated_job.id,
            event_type="job_scored",
            notes=f"Scored job at {updated_job.overall_priority_score}/100 overall priority.",
            old_status=updated_job.application_status,
            new_status=updated_job.application_status,
            metadata_json={
                "resume_match_score": updated_job.resume_match_score,
                "overall_priority_score": updated_job.overall_priority_score,
            },
        )
        summary["scored_count"] += 1
        scored_jobs.append(updated_job)

    if scored_jobs:
        summary["average_resume_match_score"] = round(
            sum(job.resume_match_score for job in scored_jobs) / len(scored_jobs),
            2,
        )
        summary["average_overall_priority_score"] = round(
            sum(job.overall_priority_score for job in scored_jobs) / len(scored_jobs),
            2,
        )
        summary["top_jobs"] = [
            TopJobSummary(
                id=job.id,
                company=job.company,
                title=job.title,
                overall_priority_score=job.overall_priority_score,
                resume_match_score=job.resume_match_score,
                verification_status=job.verification_status,
            )
            for job in sorted(
                scored_jobs,
                key=lambda job: (
                    job.overall_priority_score,
                    job.resume_match_score,
                    job.verification_score,
                ),
                reverse=True,
            )[:5]
        ]

    return summary


@router.get("/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    limit: int = 10,
    include_closed: bool = False,
    role_category: str | None = None,
    location: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    jobs = list_recommendations(
        db,
        limit=limit,
        include_closed=include_closed,
        role_category=role_category,
        location=location,
        status=status,
    )
    return RecommendationResponse(count=len(jobs), jobs=jobs)


@router.post("/verify-all", response_model=VerifyAllSummary)
def verify_all_jobs(db: Session = Depends(get_db)) -> VerifyAllSummary:
    jobs = list_jobs(db)
    summary = {
        "total_jobs": len(jobs),
        "verified_count": 0,
        "skipped_count": 0,
        "open_count": 0,
        "probably_open_count": 0,
        "unknown_count": 0,
        "possibly_closed_count": 0,
        "likely_closed_count": 0,
        "closed_count": 0,
        "errors": [],
    }

    for job in jobs:
        if not job.url.strip():
            summary["skipped_count"] += 1
            summary["errors"].append(f"Skipped job {job.id}: no URL is stored.")
            continue

        result = verify_job_record(job)
        updates = build_job_verification_updates(job, result)
        updated_job = update_job(db, job.id, updates)
        if updated_job is None:
            summary["skipped_count"] += 1
            summary["errors"].append(f"Job {job.id}: record disappeared before verification could be saved.")
            continue
        log_event(
            db,
            job_id=updated_job.id,
            event_type="job_verified",
            notes=f"Verification status: {updated_job.verification_status}.",
            old_status=updated_job.application_status,
            new_status=updated_job.application_status,
            metadata_json={
                "verification_status": updated_job.verification_status,
                "verification_score": updated_job.verification_score,
                "likely_closed_score": updated_job.likely_closed_score,
            },
        )
        if updated_job.verification_status in {"open", "probably_open"}:
            promote_job_status_if_needed(
                db,
                updated_job.id,
                "verified_open",
                notes="Promoted to verified_open after verification found the posting appears active.",
            )
        summary["verified_count"] += 1
        summary_key = f"{result['verification_status']}_count"
        if summary_key in summary:
            summary[summary_key] += 1
        else:
            summary["unknown_count"] += 1
        if result.get("last_verification_error"):
            summary["errors"].append(f"Job {job.id}: {result['last_verification_error']}")

    return summary


@router.post("/{job_id}/score", response_model=JobScoringResponse)
def score_single_job(job_id: int, db: Session = Depends(get_db)) -> JobScoringResponse:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.")

    try:
        result = score_saved_job(job)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    updated_job = update_job(db, job.id, build_job_scoring_updates(result))
    if updated_job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.")
    log_event(
        db,
        job_id=updated_job.id,
        event_type="job_scored",
        notes=f"Scored job at {updated_job.overall_priority_score}/100 overall priority.",
        old_status=updated_job.application_status,
        new_status=updated_job.application_status,
        metadata_json={
            "resume_match_score": updated_job.resume_match_score,
            "overall_priority_score": updated_job.overall_priority_score,
        },
    )
    return {
        "job": updated_job,
        "score": _score_response_from_job(updated_job),
    }


@router.post("/{job_id}/verify", response_model=JobVerificationResponse)
def verify_single_job(job_id: int, db: Session = Depends(get_db)) -> JobVerificationResponse:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.")

    result = verify_job_record(job)
    updates = build_job_verification_updates(job, result)
    updated_job = update_job(db, job.id, updates)
    if updated_job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.")
    log_event(
        db,
        job_id=updated_job.id,
        event_type="job_verified",
        notes=f"Verification status: {updated_job.verification_status}.",
        old_status=updated_job.application_status,
        new_status=updated_job.application_status,
        metadata_json={
            "verification_status": updated_job.verification_status,
            "verification_score": updated_job.verification_score,
            "likely_closed_score": updated_job.likely_closed_score,
        },
    )
    if updated_job.verification_status in {"open", "probably_open"}:
        promote_job_status_if_needed(
            db,
            updated_job.id,
            "verified_open",
            notes="Promoted to verified_open after verification found the posting appears active.",
        )
    return {
        "job": updated_job,
        "verification": _verification_response_from_job(updated_job),
    }


@router.get("/{job_id}/score", response_model=JobScoreResult)
def get_job_score(job_id: int, db: Session = Depends(get_db)) -> JobScoreResult:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.")
    return _score_response_from_job(job)


@router.get("/{job_id}/verification", response_model=JobVerificationResult)
def get_job_verification(job_id: int, db: Session = Depends(get_db)) -> JobVerificationResult:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.")
    return _verification_response_from_job(job)


@router.get("/{job_id}", response_model=JobRead)
def job_detail(job_id: int, db: Session = Depends(get_db)) -> JobRead:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.")
    return job


@router.put("/{job_id}", response_model=JobRead)
def job_update(job_id: int, payload: JobUpdate, db: Session = Depends(get_db)) -> JobRead:
    job = update_job(db, job_id, payload.model_dump(exclude_unset=True))
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.")
    return job


@router.delete("/{job_id}")
def job_delete(job_id: int, db: Session = Depends(get_db)) -> dict[str, str | int]:
    deleted = delete_job(db, job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.")
    return {"status": "deleted", "job_id": job_id}


def _verify_and_score_saved_job(db: Session, job, *, source_label: str) -> tuple:
    verified = False
    scored = False
    warnings: list[str] = []

    if (job.url or "").strip():
        try:
            result = verify_job_record(job)
            updated_job = update_job(db, job.id, build_job_verification_updates(job, result))
            if updated_job is not None:
                job = updated_job
                verified = True
                log_event(
                    db,
                    job_id=job.id,
                    event_type="verification_completed",
                    notes=f"Auto-verified saved job from {source_label}: {job.verification_status}.",
                    old_status=job.application_status,
                    new_status=job.application_status,
                    metadata_json={
                        "verification_status": job.verification_status,
                        "verification_score": job.verification_score,
                        "likely_closed_score": job.likely_closed_score,
                    },
                )
                if job.verification_status in {"open", "probably_open"}:
                    promote_job_status_if_needed(
                        db,
                        job.id,
                        "verified_open",
                        notes="Promoted after automatic save verification.",
                    )
                    db.refresh(job)
        except Exception as exc:  # pragma: no cover - save should survive flaky network/pages
            warnings.append(f"Verification failed: {exc}")
    else:
        warnings.append("Verification skipped because no URL was saved.")

    try:
        result = score_saved_job(job)
        updated_job = update_job(db, job.id, build_job_scoring_updates(result))
        if updated_job is not None:
            job = updated_job
            scored = True
            log_event(
                db,
                job_id=job.id,
                event_type="scoring_completed",
                notes=f"Auto-scored saved job from {source_label}.",
                old_status=job.application_status,
                new_status=job.application_status,
                metadata_json={
                    "resume_match_score": job.resume_match_score,
                    "overall_priority_score": job.overall_priority_score,
                },
            )
    except Exception as exc:  # pragma: no cover - missing profile/resume should not block save
        warnings.append(f"Scoring failed: {exc}")

    return job, verified, scored, warnings


def _parse_job_import(payload: JobImportRequest) -> dict:
    content = payload.content.strip()
    if not content:
        raise ValueError("Job content is empty. Paste a description or provide a URL before parsing.")

    if payload.input_type == "description":
        return parse_job_description(content, use_ai=False, provider_name=None)
    if payload.input_type == "url":
        return parse_job_url(content, use_ai=False, provider_name=None)
    raise ValueError(f"Unsupported job input type: {payload.input_type}")


def _apply_import_source(parsed_job: dict, payload: JobImportRequest) -> None:
    if payload.source and payload.source != "manual":
        parsed_job["source"] = payload.source
        return
    parsed_job["source"] = parsed_job.get("source") or payload.source


def _verification_response_from_job(job) -> JobVerificationResult:
    raw = dict(job.verification_raw_data or {})
    return JobVerificationResult(
        verification_status=job.verification_status,
        verification_score=job.verification_score,
        likely_closed_score=job.likely_closed_score,
        evidence=list(job.verification_evidence or []),
        checked_at=str(raw.get("checked_at") or ""),
        http_status=raw.get("http_status"),
        final_url=str(raw.get("final_url") or job.url or ""),
        redirected=bool(raw.get("redirected", False)),
        page_title=str(raw.get("page_title") or ""),
        days_since_posted=raw.get("days_since_posted"),
        days_since_first_seen=raw.get("days_since_first_seen"),
        last_checked_date=job.last_checked_date,
        last_seen_date=job.last_seen_date,
        closed_date=job.closed_date,
        freshness_score=job.freshness_score,
        overall_priority_score=job.overall_priority_score,
        verification_raw_data=raw,
        last_verification_error=job.last_verification_error,
    )


def _verification_response_from_result(result: dict) -> JobVerificationResult:
    raw = dict(result.get("verification_raw_data") or {})
    raw.setdefault("days_since_posted", result.get("days_since_posted"))
    raw.setdefault("days_since_first_seen", result.get("days_since_first_seen"))
    return JobVerificationResult(
        verification_status=result["verification_status"],
        verification_score=float(result["verification_score"]),
        likely_closed_score=float(result["likely_closed_score"]),
        evidence=list(result.get("evidence") or []),
        checked_at=str(result.get("checked_at") or ""),
        http_status=result.get("http_status"),
        final_url=str(result.get("final_url") or ""),
        redirected=bool(result.get("redirected", False)),
        page_title=str(result.get("page_title") or ""),
        days_since_posted=result.get("days_since_posted"),
        days_since_first_seen=result.get("days_since_first_seen"),
        last_checked_date=None,
        last_seen_date=None,
        closed_date=None,
        freshness_score=0.0,
        overall_priority_score=0.0,
        verification_raw_data=raw,
        last_verification_error=result.get("last_verification_error"),
    )


def _score_response_from_job(job) -> JobScoreResult:
    scoring_evidence = dict(job.scoring_evidence or {})
    scoring_raw_data = dict(job.scoring_raw_data or {})
    return JobScoreResult(
        skill_match_score=job.skill_match_score,
        role_match_score=job.role_match_score,
        experience_fit_score=job.experience_fit_score,
        profile_keyword_score=job.profile_keyword_score,
        resume_match_score=job.resume_match_score,
        freshness_score=job.freshness_score,
        location_score=job.location_score,
        application_ease_score=job.application_ease_score,
        verification_score=job.verification_score,
        overall_priority_score=job.overall_priority_score,
        scoring_status=job.scoring_status,
        scored_at=job.scored_at.isoformat() if job.scored_at else None,
        evidence=list(scoring_evidence.get("summary") or []),
        scoring_evidence=scoring_evidence,
        scoring_raw_data=scoring_raw_data,
    )
