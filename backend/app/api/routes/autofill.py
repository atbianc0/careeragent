from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.autofill import (
    AutofillPreviewRequest,
    AutofillPreviewResponse,
    AutofillSafetyResponse,
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
