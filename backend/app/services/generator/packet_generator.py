from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_packet import ApplicationPacket
from app.models.job import Job
from app.services.ai import (
    build_application_questions_prompt,
    build_cover_letter_prompt,
    build_recruiter_message_prompt,
    build_resume_tailor_prompt,
    check_no_unsupported_claims,
    get_ai_provider,
)
from app.services.profile.profile_store import load_profile_document
from app.services.resume import compile_latex_file, generate_tailored_resume_source, load_resume_document
from app.services.tracker import log_event, promote_job_status_if_needed

from .application_notes import generate_application_notes
from .application_questions import generate_application_question_answers
from .change_summary import generate_change_summary
from .cover_letter import generate_cover_letter
from .recruiter_message import generate_recruiter_message

DEFAULT_GENERATION_MODE = "deterministic_mock"
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


def _job_context(job: Job) -> dict[str, Any]:
    return {
        "id": job.id,
        "company": job.company,
        "title": job.title,
        "location": job.location,
        "url": job.url,
        "required_skills": list(job.required_skills or []),
        "preferred_skills": list(job.preferred_skills or []),
        "application_questions": list(job.application_questions or []),
    }


def _extract_bullets(text: str) -> list[str]:
    bullets: list[str] = []
    for line in str(text or "").splitlines():
        cleaned = line.strip()
        if cleaned.startswith(("-", "*")):
            bullets.append(cleaned.lstrip("-* ").strip())
    return [bullet for bullet in bullets if bullet]


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique.append(cleaned)
    return unique


def _apply_ai_draft(
    *,
    task: str,
    provider: Any,
    prompt: str,
    context: dict[str, Any],
    profile: dict[str, Any],
    resume_text: str,
    fallback_content: str,
) -> dict[str, Any]:
    ai_result = provider.generate_text(task, prompt, context=context)
    warnings = list(ai_result.get("warnings") or [])
    if not ai_result.get("success"):
        return {
            "content": fallback_content,
            "used_ai": False,
            "warnings": warnings or [f"{provider.name} generation failed for {task}. Fell back to deterministic output."],
            "safety_notes": list(ai_result.get("safety_notes") or []),
        }

    safety_check = check_no_unsupported_claims(str(ai_result.get("content") or ""), profile, resume_text)
    warnings.extend(list(safety_check.get("warnings") or []))
    if not safety_check.get("safe"):
        warnings.append(f"{provider.name} {task} draft contained unsupported-claim warnings and was replaced with deterministic output.")
        return {
            "content": fallback_content,
            "used_ai": False,
            "warnings": warnings,
            "safety_notes": list(safety_check.get("safety_notes") or []),
        }

    return {
        "content": str(safety_check.get("content") or fallback_content),
        "used_ai": True,
        "warnings": warnings,
        "safety_notes": list(safety_check.get("safety_notes") or []),
    }


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
    generation_mode: str,
    ai_provider_name: str | None,
    ai_warnings: list[str],
    use_ai: bool,
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
        "generation_mode": generation_mode,
        "ai_requested": use_ai,
        "ai_provider": ai_provider_name,
        "ai_warnings": ai_warnings,
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
    use_ai = bool(options.get("use_ai", False))
    provider = get_ai_provider(options.get("provider"))
    ai_provider_name = provider.name if use_ai else None
    generation_mode = DEFAULT_GENERATION_MODE
    ai_warnings: list[str] = []
    ai_safety_notes: list[str] = []
    ai_tailoring_notes: list[str] = []
    if use_ai and provider.is_available():
        generation_mode = f"ai_{provider.name}"
    elif use_ai and not provider.is_available():
        ai_warnings.append(provider.unavailable_reason or f"{provider.name} provider is unavailable. Falling back to deterministic generation.")

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
        if use_ai and provider.is_available():
            resume_ai_result = provider.generate_text(
                "resume_tailor",
                build_resume_tailor_prompt(base_resume_tex, job, profile, scoring_evidence),
                context={
                    "job": _job_context(job),
                    "profile": profile,
                    "scoring_evidence": scoring_evidence or {},
                },
            )
            ai_warnings.extend(list(resume_ai_result.get("warnings") or []))
            if resume_ai_result.get("success"):
                resume_safety = check_no_unsupported_claims(str(resume_ai_result.get("content") or ""), profile, base_resume_tex)
                ai_safety_notes.extend(list(resume_safety.get("safety_notes") or []))
                ai_warnings.extend(list(resume_safety.get("warnings") or []))
                if resume_safety.get("safe"):
                    ai_tailoring_notes.extend(_extract_bullets(str(resume_safety.get("content") or "")))
                else:
                    ai_warnings.append("AI resume tailoring advisory notes were skipped because safety checks found unsupported-claim risk.")
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
            if use_ai and provider.is_available():
                cover_letter_result = _apply_ai_draft(
                    task="cover_letter",
                    provider=provider,
                    prompt=build_cover_letter_prompt(job, profile, base_resume_tex, scoring_evidence),
                    context={"job": _job_context(job), "profile": profile, "scoring_evidence": scoring_evidence or {}},
                    profile=profile,
                    resume_text=base_resume_tex,
                    fallback_content=cover_letter_content,
                )
                cover_letter_content = cover_letter_result["content"]
                ai_warnings.extend(list(cover_letter_result.get("warnings") or []))
                ai_safety_notes.extend(list(cover_letter_result.get("safety_notes") or []))
            cover_letter_path = _write_text(packet_dir / "cover_letter.md", cover_letter_content)
            files_created.append(cover_letter_path)

        recruiter_message_path: str | None = None
        if bool(options.get("include_recruiter_message", True)):
            recruiter_message_content = generate_recruiter_message(job, profile, scoring_evidence)
            if use_ai and provider.is_available():
                recruiter_result = _apply_ai_draft(
                    task="recruiter_message",
                    provider=provider,
                    prompt=build_recruiter_message_prompt(job, profile, scoring_evidence),
                    context={"job": _job_context(job), "profile": profile, "scoring_evidence": scoring_evidence or {}},
                    profile=profile,
                    resume_text=base_resume_tex,
                    fallback_content=recruiter_message_content,
                )
                recruiter_message_content = recruiter_result["content"]
                ai_warnings.extend(list(recruiter_result.get("warnings") or []))
                ai_safety_notes.extend(list(recruiter_result.get("safety_notes") or []))
            recruiter_message_path = _write_text(packet_dir / "recruiter_message.md", recruiter_message_content)
            files_created.append(recruiter_message_path)

        application_questions_path: str | None = None
        if bool(options.get("include_application_questions", True)):
            application_questions_content = generate_application_question_answers(job, profile, scoring_evidence)
            if use_ai and provider.is_available():
                question_result = _apply_ai_draft(
                    task="application_questions",
                    provider=provider,
                    prompt=build_application_questions_prompt(job, profile, scoring_evidence),
                    context={"job": _job_context(job), "profile": profile, "scoring_evidence": scoring_evidence or {}},
                    profile=profile,
                    resume_text=base_resume_tex,
                    fallback_content=application_questions_content,
                )
                application_questions_content = question_result["content"]
                ai_warnings.extend(list(question_result.get("warnings") or []))
                ai_safety_notes.extend(list(question_result.get("safety_notes") or []))
            application_questions_path = _write_text(packet_dir / "application_questions.md", application_questions_content)
            files_created.append(application_questions_path)

        application_notes_content = generate_application_notes(job, profile, scoring_evidence)
        application_notes_path = _write_text(packet_dir / "application_notes.md", application_notes_content)
        files_created.append(application_notes_path)

        ai_warnings = _unique_strings(ai_warnings)
        ai_safety_notes = _unique_strings(ai_safety_notes)
        ai_tailoring_notes = _unique_strings(ai_tailoring_notes)
        packet_safety_notes = _unique_strings(
            list(tailoring_result.get("safety_notes") or [])
            + ai_safety_notes
            + (["AI output is a draft and requires manual review."] if use_ai else [])
        )

        change_summary_content = generate_change_summary(
            job=job,
            source_resume_path=source_resume_path,
            tailoring_result=tailoring_result,
            generation_mode=generation_mode,
            provider_name=ai_provider_name,
            ai_warnings=ai_warnings,
            ai_tailoring_notes=ai_tailoring_notes,
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
            safety_notes=packet_safety_notes,
            generation_mode=generation_mode,
            ai_provider_name=ai_provider_name,
            ai_warnings=ai_warnings,
            use_ai=use_ai,
        )
        packet_metadata_path = _write_json(packet_dir / "packet_metadata.json", metadata_payload)
        files_created.append(packet_metadata_path)
        packet.packet_metadata_path = packet_metadata_path

        job.packet_generated_at = generated_at
        db.add(job)
        db.add(packet)
        db.commit()
        db.refresh(packet)
        db.refresh(job)

        promote_job_status_if_needed(
            db,
            job.id,
            "packet_ready",
            notes="Generated an application packet for this job.",
        )
        log_event(
            db,
            job_id=job.id,
            packet_id=packet.id,
            event_type="packet_generated",
            notes=f"Generated packet at {packet.packet_path}",
            old_status=job.application_status,
            new_status=job.application_status,
            metadata_json={
                "packet_path": packet.packet_path,
                "generation_status": packet.generation_status,
            },
        )
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
