from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.application_event import ApplicationEventRead
from app.schemas.tracker import (
    CompleteFollowUpRequest,
    FollowUpRequest,
    NoteCreateRequest,
    OpenApplicationResponse,
    StatusUpdateRequest,
    TrackerJobRead,
    TrackerMutationResponse,
    TrackerSummary,
)
from app.services.tracker import (
    add_job_note,
    complete_follow_up,
    get_job_timeline,
    get_jobs_by_status,
    get_recent_events,
    get_tracker_summary,
    open_application_link,
    set_follow_up,
    update_job_status,
)

router = APIRouter()


def _raise_from_value_error(exc: ValueError) -> None:
    message = str(exc)
    if "was not found" in message:
        raise HTTPException(status_code=404, detail=message) from exc
    raise HTTPException(status_code=400, detail=message) from exc


@router.get("/summary", response_model=TrackerSummary)
def tracker_summary(db: Session = Depends(get_db)) -> TrackerSummary:
    return TrackerSummary(**get_tracker_summary(db))


@router.get("/jobs", response_model=list[TrackerJobRead])
def tracker_jobs(
    status: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
) -> list[TrackerJobRead]:
    return get_jobs_by_status(db, status=status, search=search)


@router.get("/jobs/{job_id}/timeline", response_model=list[ApplicationEventRead])
def tracker_job_timeline(job_id: int, db: Session = Depends(get_db)) -> list[ApplicationEventRead]:
    try:
        return get_job_timeline(db, job_id)
    except ValueError as exc:
        _raise_from_value_error(exc)


@router.post("/jobs/{job_id}/status", response_model=TrackerMutationResponse)
def tracker_update_status(
    job_id: int,
    payload: StatusUpdateRequest,
    db: Session = Depends(get_db),
) -> TrackerMutationResponse:
    try:
        job, event = update_job_status(db, job_id, payload.status, notes=payload.notes)
    except ValueError as exc:
        _raise_from_value_error(exc)
    return TrackerMutationResponse(job=job, event=event)


@router.post("/jobs/{job_id}/note", response_model=TrackerMutationResponse)
def tracker_add_note(
    job_id: int,
    payload: NoteCreateRequest,
    db: Session = Depends(get_db),
) -> TrackerMutationResponse:
    try:
        job, event = add_job_note(db, job_id, payload.notes)
    except ValueError as exc:
        _raise_from_value_error(exc)
    return TrackerMutationResponse(job=job, event=event)


@router.post("/jobs/{job_id}/follow-up", response_model=TrackerMutationResponse)
def tracker_set_follow_up(
    job_id: int,
    payload: FollowUpRequest,
    db: Session = Depends(get_db),
) -> TrackerMutationResponse:
    try:
        job, event = set_follow_up(db, job_id, payload.follow_up_at, notes=payload.notes)
    except ValueError as exc:
        _raise_from_value_error(exc)
    return TrackerMutationResponse(job=job, event=event)


@router.post("/jobs/{job_id}/follow-up/complete", response_model=TrackerMutationResponse)
def tracker_complete_follow_up(
    job_id: int,
    payload: CompleteFollowUpRequest | None = Body(default=None),
    db: Session = Depends(get_db),
) -> TrackerMutationResponse:
    try:
        job, event = complete_follow_up(db, job_id, notes=payload.notes if payload else None)
    except ValueError as exc:
        _raise_from_value_error(exc)
    return TrackerMutationResponse(job=job, event=event)


@router.post("/jobs/{job_id}/open-application", response_model=OpenApplicationResponse)
def tracker_open_application(
    job_id: int,
    db: Session = Depends(get_db),
) -> OpenApplicationResponse:
    try:
        job, event, url = open_application_link(db, job_id)
    except ValueError as exc:
        _raise_from_value_error(exc)
    return OpenApplicationResponse(job=job, event=event, url=url)


@router.get("/events", response_model=list[ApplicationEventRead])
def tracker_events(
    limit: int = Query(20, ge=1, le=100),
    job_id: int | None = None,
    event_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[ApplicationEventRead]:
    return get_recent_events(db, limit=limit, job_id=job_id, event_type=event_type)
