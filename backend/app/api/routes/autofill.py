from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.schemas.autofill import (
    AutofillPreviewRequest,
    AutofillPreviewResponse,
    AutofillSafetyResponse,
    AutofillSessionCleanupResponse,
    AutofillSessionCloseResponse,
    AutofillSessionListResponse,
    AutofillStartRequest,
    AutofillStartResponse,
    AutofillStatusResponse,
)
from app.services.browser_agent import (
    AutofillError,
    AutofillNotFoundError,
    AutofillUnavailableError,
    get_autofill_safety,
    get_autofill_status,
    preview_autofill_plan,
    start_autofill_session,
)
from app.services.browser_agent.session_store import cleanup_closed_sessions, cleanup_expired_sessions, close_session, list_sessions

router = APIRouter()


def _raise_autofill_error(exc: AutofillError) -> None:
    if isinstance(exc, AutofillNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, AutofillUnavailableError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/status", response_model=AutofillStatusResponse)
def autofill_status() -> AutofillStatusResponse:
    return AutofillStatusResponse(**get_autofill_status())


@router.get("/safety", response_model=AutofillSafetyResponse)
def autofill_safety() -> AutofillSafetyResponse:
    return AutofillSafetyResponse(**get_autofill_safety())


@router.get("/sessions", response_model=AutofillSessionListResponse)
def autofill_sessions() -> AutofillSessionListResponse:
    return AutofillSessionListResponse(sessions=list_sessions())


@router.post("/sessions/{session_id}/close", response_model=AutofillSessionCloseResponse)
def autofill_close_session(session_id: str) -> AutofillSessionCloseResponse:
    closed = close_session(session_id)
    return AutofillSessionCloseResponse(success=True, session=closed)


@router.post("/sessions/cleanup", response_model=AutofillSessionCleanupResponse)
def autofill_cleanup_sessions(max_age_seconds: int | None = None) -> AutofillSessionCleanupResponse:
    closed = cleanup_closed_sessions()
    closed.extend(cleanup_expired_sessions(max_age_seconds or settings.playwright_keep_open_seconds))
    return AutofillSessionCleanupResponse(success=True, closed_sessions=closed)


@router.get("/screenshots/{filename}")
def autofill_screenshot(filename: str) -> FileResponse:
    if not re.fullmatch(r"job_\d+_[A-Za-z0-9T_-]+\.png", filename):
        raise HTTPException(status_code=404, detail="Screenshot was not found.")
    screenshot_dir = (settings.outputs_dir / "autofill_screenshots").resolve()
    path = (screenshot_dir / filename).resolve()
    try:
        path.relative_to(screenshot_dir)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Screenshot was not found.") from exc
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Screenshot was not found.")
    return FileResponse(path, media_type="image/png")


@router.post("/dry-run", response_model=AutofillPreviewResponse)
def autofill_dry_run(
    payload: AutofillPreviewRequest,
    db: Session = Depends(get_db),
) -> AutofillPreviewResponse:
    try:
        preview = preview_autofill_plan(
            db,
            payload.job_id,
            packet_id=payload.packet_id,
            options=payload.model_dump(),
        )
    except AutofillError as exc:
        _raise_autofill_error(exc)
    return AutofillPreviewResponse(**preview)


@router.post("/start", response_model=AutofillStartResponse)
def autofill_start(
    payload: AutofillStartRequest,
    db: Session = Depends(get_db),
) -> AutofillStartResponse:
    if payload.dry_run:
        try:
            preview = preview_autofill_plan(
                db,
                payload.job_id,
                packet_id=payload.packet_id,
                options=payload.model_dump(),
            )
        except AutofillError as exc:
            _raise_autofill_error(exc)
        raise HTTPException(
            status_code=400,
            detail=f"Use /api/autofill/dry-run for previews. Preview message: {preview['message']}",
        )

    try:
        summary = start_autofill_session(
            db,
            payload.job_id,
            packet_id=payload.packet_id,
            options=payload.model_dump(),
        )
    except AutofillError as exc:
        _raise_autofill_error(exc)
    return AutofillStartResponse(**summary)
