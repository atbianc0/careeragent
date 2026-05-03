from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_event import ApplicationEvent
from app.models.application_packet import ApplicationPacket
from app.models.job import Job
from app.services.profile.profile_store import load_profile_document
from app.services.resume import compile_latex_file, generate_tailored_resume_source, load_resume_document

from .application_notes import generate_application_notes
from .application_questions import generate_application_question_answers
from .change_summary import generate_change_summary
from .cover_letter import generate_cover_letter
from .recruiter_message import generate_recruiter_message

GENERATION_MODE = "deterministic_mock"
SUCCESS_STATUSES = {"completed", "completed_with_warnings"}


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(settings.project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _safe_slug_piece(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "unknown"


def _packet_slug(job: Job) -> str:
    return f"{_safe_slug_piece(job.company)}_{_safe_slug_piece(job.title)}_{job.id}"


def _json_default(value: Any) -> str | float | int | bool | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return _relative_path(path)


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")
    return _relative_path(path)


def _job_summary_payload(job: Job, generated_at: datetime) -> dict[str, Any]:
    return {
        "job_id": job.id,
        "company": job.company,
        "title": job.title,
        "location": job.location,
        "url": job.url,
        "source": job.source,
        "generated_at": generated_at,
        "core_job_data": {
            "employment_type": job.employment_type,
            "remote_status": job.remote_status,
            "role_category": job.role_category,
            "seniority_level": job.seniority_level,
            "posted_date": job.posted_date,
            "first_seen_date": job.first_seen_date,
            "last_seen_date": job.last_seen_date,
            "application_status": job.application_status,
        },
        "parsed_fields": {
            "required_skills": list(job.required_skills or []),
            "preferred_skills": list(job.preferred_skills or []),
            "responsibilities": list(job.responsibilities or []),
            "requirements": list(job.requirements or []),
            "education_requirements": list(job.education_requirements or []),
            "application_questions": list(job.application_questions or []),
            "raw_parsed_data": dict(job.raw_parsed_data or {}),
        },
        "verification_fields": {
            "verification_status": job.verification_status,
            "verification_score": job.verification_score,
            "likely_closed_score": job.likely_closed_score,
            "verification_evidence": list(job.verification_evidence or []),
            "verification_raw_data": dict(job.verification_raw_data or {}),
            "last_verification_error": job.last_verification_error,
            "last_checked_date": job.last_checked_date,
            "closed_date": job.closed_date,
        },
        "scoring_fields": {
            "skill_match_score": job.skill_match_score,
            "role_match_score": job.role_match_score,
            "experience_fit_score": job.experience_fit_score,
            "profile_keyword_score": job.profile_keyword_score,
            "resume_match_score": job.resume_match_score,
            "freshness_score": job.freshness_score,
            "location_score": job.location_score,
            "application_ease_score": job.application_ease_score,
            "overall_priority_score": job.overall_priority_score,
            "scoring_status": job.scoring_status,
            "scoring_evidence": dict(job.scoring_evidence or {}),
            "scoring_raw_data": dict(job.scoring_raw_data or {}),
            "scored_at": job.scored_at,
        },
    }


def _packet_metadata_payload(
    *,
    packet: ApplicationPacket,
    job: Job,
    source_resume_path: str,
    files_created: list[str],
    compile_resume_pdf_requested: bool,
    compile_resume_pdf_result: dict[str, Any] | None,
    safety_notes: list[str],
) -> dict[str, Any]:
    compile_success = bool((compile_resume_pdf_result or {}).get("success"))
    compile_message = str((compile_resume_pdf_result or {}).get("message") or "")
    return {
        "packet_id": packet.id,
        "job_id": job.id,
        "company": job.company,
        "title": job.title,
        "generated_at": packet.generated_at,
        "source_resume_path": source_resume_path,
        "output_folder": packet.packet_path,
        "files_created": files_created,
        "compile_resume_pdf_requested": compile_resume_pdf_requested,
        "compile_resume_pdf_success": compile_success,
        "compile_resume_pdf_message": compile_message,
        "generation_mode": GENERATION_MODE,
        "safety_notes": safety_notes,
    }


def generate_application_packet(db: Session, job_id: int, options: dict[str, Any]) -> dict[str, Any]:
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise ValueError(f"Job {job_id} was not found.")

    profile_document = load_profile_document()
    resume_document = load_resume_document()
    profile = dict(profile_document.get("profile") or {})
    base_resume_tex = str(resume_document.get("content") or "")
    source_resume_path = str(resume_document.get("path") or "")
    scoring_evidence = dict(job.scoring_evidence or {}) or None

    packet_dir = settings.application_packets_dir / _packet_slug(job)
    packet_dir.mkdir(parents=True, exist_ok=True)

    existing_packets = (
        db.query(ApplicationPacket)
        .filter(ApplicationPacket.job_id == job.id)
        .order_by(ApplicationPacket.generated_at.desc().nullslast(), ApplicationPacket.id.desc())
        .all()
    )
    packet = existing_packets[0] if existing_packets else ApplicationPacket(job_id=job.id, packet_path=_relative_path(packet_dir))
    for stale_packet in existing_packets[1:]:
        db.delete(stale_packet)

    packet.packet_path = _relative_path(packet_dir)
    packet.generation_status = "generating"
    packet.generation_error = None
    packet.generated_at = None
    packet.tailored_resume_tex_path = None
    packet.tailored_resume_pdf_path = None
    packet.cover_letter_path = None
    packet.cover_letter_pdf_path = None
    packet.recruiter_message_path = None
    packet.application_questions_path = None
    packet.application_notes_path = None
    packet.change_summary_path = None
    packet.job_summary_path = None
    packet.packet_metadata_path = None
    db.add(packet)
    db.commit()
    db.refresh(packet)

    generated_at = datetime.now(timezone.utc)
    compile_result: dict[str, Any] | None = None
    files_created: list[str] = []
    generation_error: str | None = None

    try:
        job_summary_path = _write_json(packet_dir / "job_summary.json", _job_summary_payload(job, generated_at))
        files_created.append(job_summary_path)

        tailoring_result = generate_tailored_resume_source(base_resume_tex, job, profile, scoring_evidence)
        tailored_resume_tex_path = _write_text(packet_dir / "tailored_resume.tex", str(tailoring_result["content"]))
        files_created.append(tailored_resume_tex_path)

        tailored_resume_pdf_path: str | None = None
        if bool(options.get("compile_resume_pdf", True)):
            compile_result = compile_latex_file(packet_dir / "tailored_resume.tex", packet_dir, "tailored_resume")
            if compile_result.get("success"):
                tailored_resume_pdf_path = str(compile_result.get("output_path") or "")
                if tailored_resume_pdf_path:
                    files_created.append(tailored_resume_pdf_path)
            else:
                generation_error = str(compile_result.get("message") or "Tailored resume PDF compilation was not available.")

        cover_letter_path: str | None = None
        if bool(options.get("include_cover_letter", True)):
            cover_letter_content = generate_cover_letter(job, profile, base_resume_tex, scoring_evidence)
            cover_letter_path = _write_text(packet_dir / "cover_letter.md", cover_letter_content)
            files_created.append(cover_letter_path)

        recruiter_message_path: str | None = None
        if bool(options.get("include_recruiter_message", True)):
            recruiter_message_content = generate_recruiter_message(job, profile, scoring_evidence)
            recruiter_message_path = _write_text(packet_dir / "recruiter_message.md", recruiter_message_content)
            files_created.append(recruiter_message_path)

        application_questions_path: str | None = None
        if bool(options.get("include_application_questions", True)):
            application_questions_content = generate_application_question_answers(job, profile, scoring_evidence)
            application_questions_path = _write_text(packet_dir / "application_questions.md", application_questions_content)
            files_created.append(application_questions_path)

        application_notes_content = generate_application_notes(job, profile, scoring_evidence)
        application_notes_path = _write_text(packet_dir / "application_notes.md", application_notes_content)
        files_created.append(application_notes_path)

        change_summary_content = generate_change_summary(
            job=job,
            source_resume_path=source_resume_path,
            tailoring_result=tailoring_result,
        )
        change_summary_path = _write_text(packet_dir / "change_summary.md", change_summary_content)
        files_created.append(change_summary_path)

        packet.generated_at = generated_at
        packet.tailored_resume_tex_path = tailored_resume_tex_path
        packet.tailored_resume_pdf_path = tailored_resume_pdf_path
        packet.cover_letter_path = cover_letter_path
        packet.cover_letter_pdf_path = None
        packet.recruiter_message_path = recruiter_message_path
        packet.application_questions_path = application_questions_path
        packet.application_notes_path = application_notes_path
        packet.change_summary_path = change_summary_path
        packet.job_summary_path = job_summary_path
        packet.generation_error = generation_error
        packet.generation_status = "completed_with_warnings" if generation_error else "completed"

        metadata_payload = _packet_metadata_payload(
            packet=packet,
            job=job,
            source_resume_path=source_resume_path,
            files_created=files_created,
            compile_resume_pdf_requested=bool(options.get("compile_resume_pdf", True)),
            compile_resume_pdf_result=compile_result,
            safety_notes=list(tailoring_result.get("safety_notes") or []),
            )
        packet_metadata_path = _write_json(packet_dir / "packet_metadata.json", metadata_payload)
        files_created.append(packet_metadata_path)
        packet.packet_metadata_path = packet_metadata_path

        job.application_status = "packet_ready"
        db.add(
            ApplicationEvent(
                job_id=job.id,
                event_type="packet_generated",
                notes=f"Generated packet at {packet.packet_path}",
            )
        )
        db.commit()
        db.refresh(packet)
        db.refresh(job)

        metadata_payload["files_created"] = files_created
        if packet.packet_metadata_path:
            _write_json(packet_dir / "packet_metadata.json", metadata_payload)

        return {
            "packet": packet,
            "job": job,
            "message": "Application packet generated successfully." if not generation_error else "Application packet generated with warnings.",
            "compile_resume_pdf_requested": bool(options.get("compile_resume_pdf", True)),
            "compile_resume_pdf_success": bool((compile_result or {}).get("success")),
            "files_created": files_created,
            "metadata": metadata_payload,
        }
    except Exception as exc:
        db.rollback()
        failed_packet = db.query(ApplicationPacket).filter(ApplicationPacket.id == packet.id).first()
        if failed_packet is not None:
            failed_packet.generated_at = datetime.now(timezone.utc)
            failed_packet.generation_status = "failed"
            failed_packet.generation_error = str(exc)
            db.commit()
        raise
