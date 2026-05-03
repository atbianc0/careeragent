from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.application_event import ApplicationEvent
from app.models.job import Job

APPLICATION_STATUS_VALUES = (
    "found",
    "saved",
    "verified_open",
    "packet_ready",
    "application_opened",
    "autofill_started",
    "autofill_completed",
    "applied_manual",
    "follow_up",
    "interview",
    "rejected",
    "offer",
    "withdrawn",
    "closed_before_apply",
)
APPLICATION_STATUS_RANK = {
    "found": 0,
    "saved": 1,
    "verified_open": 2,
    "packet_ready": 3,
    "application_opened": 4,
    "autofill_started": 5,
    "autofill_completed": 6,
    "applied_manual": 7,
    "follow_up": 8,
    "interview": 9,
    "rejected": 10,
    "offer": 10,
    "withdrawn": 10,
    "closed_before_apply": 10,
}
STATUS_EVENT_TYPE_MAP = {
    "applied_manual": "manual_applied",
    "interview": "interview_received",
    "rejected": "rejected",
    "offer": "offer_received",
    "withdrawn": "withdrawn",
    "closed_before_apply": "closed_before_apply",
    "autofill_started": "autofill_started",
    "autofill_completed": "autofill_completed",
}
APPLICATION_OPEN_LATER_STATUSES = {
    "applied_manual",
    "follow_up",
    "interview",
    "rejected",
    "offer",
    "withdrawn",
    "closed_before_apply",
    "autofill_started",
    "autofill_completed",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_job_or_raise(db: Session, job_id: int) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise ValueError(f"Job {job_id} was not found.")
    return job


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _append_note(existing: str | None, note: str, *, label: str = "Note") -> str:
    timestamp = _now().strftime("%Y-%m-%d %H:%M UTC")
    entry = f"[{timestamp}] {label}: {note.strip()}"
    if not existing:
        return entry
    return f"{existing.rstrip()}\n\n{entry}"


def _apply_status_timestamps(
    job: Job,
    new_status: str,
    *,
    reference_time: datetime,
    follow_up_at: datetime | None = None,
) -> None:
    if new_status == "packet_ready" and job.packet_generated_at is None:
        job.packet_generated_at = reference_time
    if new_status == "application_opened":
        job.application_link_opened_at = reference_time
    if new_status == "applied_manual":
        job.applied_at = reference_time
    if new_status == "follow_up":
        job.follow_up_at = follow_up_at or job.follow_up_at or reference_time
    if new_status == "interview":
        job.interview_at = reference_time
    if new_status == "rejected":
        job.rejected_at = reference_time
    if new_status == "offer":
        job.offer_at = reference_time
    if new_status == "withdrawn":
        job.withdrawn_at = reference_time
    if new_status == "closed_before_apply":
        job.closed_before_apply_at = reference_time

    if new_status in {"applied_manual", "interview", "rejected", "offer", "withdrawn", "closed_before_apply"}:
        job.follow_up_at = None
        job.next_action_due_at = None

    if new_status in {"interview", "rejected", "offer", "withdrawn", "closed_before_apply"}:
        job.next_action = None


def _load_event(db: Session, event_id: int) -> ApplicationEvent:
    event = (
        db.query(ApplicationEvent)
        .options(joinedload(ApplicationEvent.job))
        .filter(ApplicationEvent.id == event_id)
        .first()
    )
    if event is None:
        raise ValueError(f"Application event {event_id} was not found.")
    return event


def _should_promote_status(current_status: str | None, target_status: str) -> bool:
    current_rank = APPLICATION_STATUS_RANK.get(current_status or "", -1)
    target_rank = APPLICATION_STATUS_RANK.get(target_status, -1)
    return target_rank > current_rank


def _fallback_status_after_follow_up(job: Job) -> str:
    if job.offer_at is not None:
        return "offer"
    if job.rejected_at is not None:
        return "rejected"
    if job.interview_at is not None:
        return "interview"
    if job.applied_at is not None:
        return "applied_manual"
    if job.application_link_opened_at is not None:
        return "application_opened"
    if job.packet_generated_at is not None:
        return "packet_ready"
    if job.verification_status in {"open", "probably_open"}:
        return "verified_open"
    if job.source != "sample_seed":
        return "saved"
    return "found"


def log_event(
    db: Session,
    job_id: int,
    event_type: str,
    notes: str | None = None,
    old_status: str | None = None,
    new_status: str | None = None,
    packet_id: int | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> ApplicationEvent:
    event = ApplicationEvent(
        job_id=job_id,
        packet_id=packet_id,
        event_type=event_type,
        event_time=_now(),
        old_status=old_status,
        new_status=new_status,
        notes=_normalize_optional_text(notes),
        metadata_json=metadata_json or None,
    )
    db.add(event)
    db.commit()
    return _load_event(db, event.id)


def promote_job_status_if_needed(
    db: Session,
    job_id: int,
    new_status: str,
    notes: str | None = None,
) -> tuple[Job, ApplicationEvent | None]:
    job = _get_job_or_raise(db, job_id)
    old_status = job.application_status
    if not _should_promote_status(old_status, new_status):
        return job, None

    reference_time = _now()
    job.application_status = new_status
    _apply_status_timestamps(job, new_status, reference_time=reference_time)
    db.add(job)
    event = log_event(
        db,
        job_id=job.id,
        event_type="status_changed",
        notes=notes,
        old_status=old_status,
        new_status=new_status,
    )
    db.refresh(job)
    return job, event


def update_job_status(db: Session, job_id: int, new_status: str, notes: str | None = None) -> tuple[Job, ApplicationEvent]:
    job = _get_job_or_raise(db, job_id)
    old_status = job.application_status
    normalized_notes = _normalize_optional_text(notes)

    if normalized_notes:
        job.user_notes = _append_note(job.user_notes, normalized_notes, label=f"Status set to {new_status}")

    reference_time = _now()
    job.application_status = new_status
    _apply_status_timestamps(job, new_status, reference_time=reference_time)
    db.add(job)
    event = log_event(
        db,
        job_id=job.id,
        event_type="status_changed",
        notes=normalized_notes,
        old_status=old_status,
        new_status=new_status,
    )

    domain_event = STATUS_EVENT_TYPE_MAP.get(new_status)
    if domain_event:
        log_event(
            db,
            job_id=job.id,
            event_type=domain_event,
            notes=normalized_notes,
            old_status=old_status,
            new_status=new_status,
        )

    db.refresh(job)
    return job, event


def add_job_note(db: Session, job_id: int, notes: str) -> tuple[Job, ApplicationEvent]:
    job = _get_job_or_raise(db, job_id)
    normalized_notes = _normalize_optional_text(notes)
    if not normalized_notes:
        raise ValueError("Notes cannot be empty.")

    job.user_notes = _append_note(job.user_notes, normalized_notes)
    db.add(job)
    event = log_event(
        db,
        job_id=job.id,
        event_type="note_added",
        notes=normalized_notes,
        old_status=job.application_status,
        new_status=job.application_status,
    )
    db.refresh(job)
    return job, event


def set_follow_up(db: Session, job_id: int, follow_up_at: datetime, notes: str | None = None) -> tuple[Job, ApplicationEvent]:
    job = _get_job_or_raise(db, job_id)
    old_status = job.application_status
    normalized_notes = _normalize_optional_text(notes)

    job.follow_up_at = follow_up_at
    job.next_action = normalized_notes or "Follow up on this application"
    job.next_action_due_at = follow_up_at
    job.application_status = "follow_up"
    _apply_status_timestamps(job, "follow_up", reference_time=_now(), follow_up_at=follow_up_at)

    if normalized_notes:
        job.user_notes = _append_note(job.user_notes, normalized_notes, label="Follow-up")

    db.add(job)
    if old_status != "follow_up":
        log_event(
            db,
            job_id=job.id,
            event_type="status_changed",
            notes=normalized_notes,
            old_status=old_status,
            new_status="follow_up",
        )
    event = log_event(
        db,
        job_id=job.id,
        event_type="follow_up_set",
        notes=normalized_notes,
        old_status=old_status,
        new_status="follow_up",
        metadata_json={"follow_up_at": follow_up_at.isoformat()},
    )
    db.refresh(job)
    return job, event


def complete_follow_up(db: Session, job_id: int, notes: str | None = None) -> tuple[Job, ApplicationEvent]:
    job = _get_job_or_raise(db, job_id)
    old_status = job.application_status
    normalized_notes = _normalize_optional_text(notes)

    job.follow_up_at = None
    job.next_action = None
    job.next_action_due_at = None
    fallback_status = _fallback_status_after_follow_up(job)
    job.application_status = fallback_status

    if normalized_notes:
        job.user_notes = _append_note(job.user_notes, normalized_notes, label="Follow-up completed")

    db.add(job)
    if old_status != fallback_status:
        log_event(
            db,
            job_id=job.id,
            event_type="status_changed",
            notes=normalized_notes,
            old_status=old_status,
            new_status=fallback_status,
        )
    event = log_event(
        db,
        job_id=job.id,
        event_type="follow_up_completed",
        notes=normalized_notes,
        old_status=old_status,
        new_status=fallback_status,
    )
    db.refresh(job)
    return job, event


def open_application_link(db: Session, job_id: int) -> tuple[Job, ApplicationEvent, str]:
    job = _get_job_or_raise(db, job_id)
    if not (job.url or "").strip():
        raise ValueError(f"Job {job_id} does not have an application URL.")

    old_status = job.application_status
    reference_time = _now()
    job.application_link_opened_at = reference_time

    if job.application_status not in APPLICATION_OPEN_LATER_STATUSES and _should_promote_status(old_status, "application_opened"):
        job.application_status = "application_opened"
        log_event(
            db,
            job_id=job.id,
            event_type="status_changed",
            notes="Opened the application link through CareerAgent.",
            old_status=old_status,
            new_status="application_opened",
        )

    db.add(job)
    event = log_event(
        db,
        job_id=job.id,
        event_type="application_link_opened",
        notes="Opened the application link through CareerAgent.",
        old_status=old_status,
        new_status=job.application_status,
        metadata_json={"url": job.url},
    )
    db.refresh(job)
    return job, event, job.url


def get_job_timeline(db: Session, job_id: int) -> list[ApplicationEvent]:
    _get_job_or_raise(db, job_id)
    return (
        db.query(ApplicationEvent)
        .options(joinedload(ApplicationEvent.job))
        .filter(ApplicationEvent.job_id == job_id)
        .order_by(ApplicationEvent.event_time.desc(), ApplicationEvent.id.desc())
        .all()
    )


def get_recent_events(
    db: Session,
    *,
    limit: int = 20,
    job_id: int | None = None,
    event_type: str | None = None,
) -> list[ApplicationEvent]:
    query = db.query(ApplicationEvent).options(joinedload(ApplicationEvent.job))
    if job_id is not None:
        query = query.filter(ApplicationEvent.job_id == job_id)
    if event_type:
        query = query.filter(ApplicationEvent.event_type == event_type)
    return query.order_by(ApplicationEvent.event_time.desc(), ApplicationEvent.id.desc()).limit(max(limit, 1)).all()


def get_jobs_by_status(
    db: Session,
    status: str | None = None,
    search: str | None = None,
) -> list[Job]:
    query = db.query(Job)
    if status:
        query = query.filter(Job.application_status == status)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Job.company.ilike(search_term),
                Job.title.ilike(search_term),
                Job.location.ilike(search_term),
                Job.user_notes.ilike(search_term),
            )
        )
    return query.order_by(Job.updated_at.desc(), Job.overall_priority_score.desc(), Job.id.desc()).all()


def get_tracker_summary(db: Session) -> dict[str, Any]:
    jobs = db.query(Job).order_by(Job.updated_at.desc(), Job.id.desc()).all()
    counts_by_status = {status: 0 for status in APPLICATION_STATUS_VALUES}
    for job in jobs:
        counts_by_status[job.application_status] = counts_by_status.get(job.application_status, 0) + 1

    upcoming_follow_ups = (
        db.query(Job)
        .filter(Job.follow_up_at.isnot(None))
        .order_by(Job.follow_up_at.asc(), Job.updated_at.desc())
        .limit(10)
        .all()
    )
    recent_events = get_recent_events(db, limit=15)

    return {
        "total_jobs": len(jobs),
        "saved_count": counts_by_status.get("saved", 0),
        "packet_ready_count": counts_by_status.get("packet_ready", 0),
        "application_opened_count": counts_by_status.get("application_opened", 0)
        + counts_by_status.get("autofill_started", 0)
        + counts_by_status.get("autofill_completed", 0),
        "applied_count": counts_by_status.get("applied_manual", 0),
        "follow_up_count": counts_by_status.get("follow_up", 0),
        "interview_count": counts_by_status.get("interview", 0),
        "rejected_count": counts_by_status.get("rejected", 0),
        "offer_count": counts_by_status.get("offer", 0),
        "withdrawn_count": counts_by_status.get("withdrawn", 0),
        "closed_before_apply_count": counts_by_status.get("closed_before_apply", 0),
        "counts_by_status": counts_by_status,
        "upcoming_follow_ups": upcoming_follow_ups,
        "recent_events": recent_events,
    }
