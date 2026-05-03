from datetime import date
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.job import Job
from app.services.scoring.scoring import calculate_priority_score, freshness_score_value


def _today() -> date:
    return date.today()


def _days_since(reference_date: date | None) -> int | None:
    if reference_date is None:
        return None
    return max((_today() - reference_date).days, 0)


def calculate_freshness_score(posted_date: date | None, first_seen_date: date | None = None) -> float:
    return freshness_score_value(posted_date, first_seen_date)


def calculate_placeholder_priority_score(
    *,
    resume_match_score: float | None,
    verification_score: float | None,
    freshness_score: float | None,
    location_score: float | None,
    application_ease_score: float | None,
) -> float:
    return calculate_priority_score(
        resume_match_score=resume_match_score if resume_match_score is not None else 0.0,
        verification_score=verification_score if verification_score is not None else 0.0,
        freshness_score=freshness_score if freshness_score is not None else 50.0,
        location_score=location_score if location_score is not None else 50.0,
        application_ease_score=application_ease_score if application_ease_score is not None else 50.0,
    )


def create_job(db: Session, parsed_job: dict[str, Any]) -> Job:
    payload = dict(parsed_job)
    today = _today()
    payload.setdefault("company", "Unknown Company")
    payload.setdefault("title", "Unknown Title")
    payload.setdefault("location", "Unknown")
    payload.setdefault("url", "")
    payload.setdefault("source", "manual")
    payload.setdefault("job_description", "")
    payload.setdefault("required_skills", [])
    payload.setdefault("preferred_skills", [])
    payload.setdefault("responsibilities", [])
    payload.setdefault("requirements", [])
    payload.setdefault("education_requirements", [])
    payload.setdefault("application_questions", [])
    payload.setdefault("raw_parsed_data", {})
    payload.setdefault("verification_evidence", [])
    payload.setdefault("verification_raw_data", {})
    payload.setdefault("last_verification_error", None)
    payload.setdefault("first_seen_date", today)
    payload.setdefault("last_seen_date", today)
    payload.setdefault("application_status", "found")
    payload.setdefault("verification_status", "unknown")
    payload.setdefault("verification_score", 0.0)
    payload.setdefault("likely_closed_score", 0.0)
    payload.setdefault("skill_match_score", 0.0)
    payload.setdefault("role_match_score", 0.0)
    payload.setdefault("experience_fit_score", 0.0)
    payload.setdefault("profile_keyword_score", 0.0)
    payload.setdefault("resume_match_score", 0.0)
    payload.setdefault("location_score", 50.0)
    payload.setdefault("application_ease_score", 50.0)
    payload.setdefault("scoring_status", "unscored")
    payload.setdefault("scoring_evidence", {})
    payload.setdefault("scoring_raw_data", {})
    payload.setdefault("scored_at", None)
    payload["freshness_score"] = calculate_freshness_score(
        payload.get("posted_date"),
        payload.get("first_seen_date"),
    )
    payload["overall_priority_score"] = calculate_placeholder_priority_score(
        resume_match_score=payload.get("resume_match_score"),
        verification_score=payload.get("verification_score"),
        freshness_score=payload.get("freshness_score"),
        location_score=payload.get("location_score"),
        application_ease_score=payload.get("application_ease_score"),
    )

    job = Job(**payload)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_jobs(
    db: Session,
    *,
    status: str | None = None,
    role_category: str | None = None,
    source: str | None = None,
    search: str | None = None,
) -> list[Job]:
    query = db.query(Job)

    if status:
        query = query.filter(or_(Job.application_status == status, Job.verification_status == status))
    if role_category:
        query = query.filter(Job.role_category == role_category)
    if source:
        query = query.filter(Job.source == source)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Job.company.ilike(search_term),
                Job.title.ilike(search_term),
                Job.location.ilike(search_term),
                Job.job_description.ilike(search_term),
            )
        )

    return query.order_by(Job.first_seen_date.desc(), Job.created_at.desc(), Job.id.desc()).all()


def get_job(db: Session, job_id: int) -> Job | None:
    return db.query(Job).filter(Job.id == job_id).first()


def update_job(db: Session, job_id: int, update_data: dict[str, Any]) -> Job | None:
    job = get_job(db, job_id)
    if job is None:
        return None

    for field, value in update_data.items():
        setattr(job, field, value)

    freshness_inputs_changed = "posted_date" in update_data or "first_seen_date" in update_data
    score_inputs_changed = freshness_inputs_changed or any(
        field in update_data
        for field in [
            "resume_match_score",
            "verification_score",
            "freshness_score",
            "location_score",
            "application_ease_score",
            "skill_match_score",
            "role_match_score",
            "experience_fit_score",
            "profile_keyword_score",
        ]
    )

    if freshness_inputs_changed and "freshness_score" not in update_data:
        job.freshness_score = calculate_freshness_score(job.posted_date, job.first_seen_date)

    if score_inputs_changed and "overall_priority_score" not in update_data:
        job.overall_priority_score = calculate_placeholder_priority_score(
            resume_match_score=job.resume_match_score,
            verification_score=job.verification_score,
            freshness_score=job.freshness_score,
            location_score=job.location_score,
            application_ease_score=job.application_ease_score,
        )

    db.commit()
    db.refresh(job)
    return job


def delete_job(db: Session, job_id: int) -> bool:
    job = get_job(db, job_id)
    if job is None:
        return False

    db.delete(job)
    db.commit()
    return True


def list_recommendations(
    db: Session,
    *,
    limit: int = 10,
    include_closed: bool = False,
    role_category: str | None = None,
    location: str | None = None,
    status: str | None = None,
) -> list[Job]:
    query = db.query(Job).filter(Job.scoring_status == "scored")

    if not include_closed:
        query = query.filter(Job.verification_status.notin_(["closed", "likely_closed"]))
    if role_category:
        query = query.filter(Job.role_category == role_category)
    if location:
        location_term = f"%{location.strip()}%"
        query = query.filter(Job.location.ilike(location_term))
    if status:
        query = query.filter(Job.verification_status == status)

    return (
        query.order_by(
            Job.overall_priority_score.desc(),
            Job.resume_match_score.desc(),
            Job.verification_score.desc(),
            Job.freshness_score.desc(),
            Job.id.desc(),
        )
        .limit(max(limit, 1))
        .all()
    )
