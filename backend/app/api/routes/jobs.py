from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
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
from app.services.scoring import build_job_scoring_updates, score_saved_job
from app.services.tracker import log_event, promote_job_status_if_needed
from app.services.verifier.verifier import build_job_verification_updates, verify_job_record, verify_job_url

router = APIRouter()


@router.get("", response_model=list[JobRead])
def jobs_index(
    status: str | None = None,
    role_category: str | None = None,
    source: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
) -> list[JobRead]:
    return list_jobs(
        db,
        status=status,
        role_category=role_category,
        source=source,
        search=search,
    )


@router.post("/parse", response_model=JobParseResult)
def preview_job_parse(payload: JobImportRequest) -> JobParseResult:
    try:
        parsed_job = _parse_job_import(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    parsed_job["source"] = payload.source
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
    parsing_warnings = list(parsed_job.pop("parsing_warnings", []) or [])
    raw_parsed_data = dict(parsed_job.get("raw_parsed_data") or {})
    raw_parsed_data["parsing_mode"] = parse_mode
    raw_parsed_data["ai_provider"] = parsing_provider
    raw_parsed_data["parsing_warnings"] = parsing_warnings
    parsed_job["raw_parsed_data"] = raw_parsed_data
    parsed_job["source"] = payload.source
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
            "provider": parsing_provider,
            "parsing_warnings": parsing_warnings,
        },
    )
    return job


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


def _parse_job_import(payload: JobImportRequest) -> dict:
    content = payload.content.strip()
    if not content:
        raise ValueError("Job content is empty. Paste a description or provide a URL before parsing.")

    if payload.input_type == "description":
        return parse_job_description(content, use_ai=payload.use_ai, provider_name=payload.provider)
    if payload.input_type == "url":
        return parse_job_url(content, use_ai=payload.use_ai, provider_name=payload.provider)
    raise ValueError(f"Unsupported job input type: {payload.input_type}")


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
