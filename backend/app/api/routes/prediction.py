from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.job import Job
from app.services.prediction import (
    estimate_best_apply_windows,
    estimate_role_quality,
    estimate_source_quality,
    generate_prediction_insights,
    get_prediction_dashboard,
    get_prediction_data_export,
    get_prediction_jobs,
    predict_close_risk,
    predict_job_priority,
    predict_response_likelihood,
    recalculate_prediction_scores,
)

router = APIRouter()


def _get_job_or_404(db: Session, job_id: int) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.")
    return job


@router.get("/dashboard")
def prediction_dashboard(db: Session = Depends(get_db)) -> dict:
    return get_prediction_dashboard(db)


@router.post("/recalculate")
def prediction_recalculate(db: Session = Depends(get_db)) -> dict:
    return recalculate_prediction_scores(db)


@router.get("/jobs")
def prediction_jobs(
    include_closed: bool = Query(False),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0),
    role_category: str | None = None,
    source: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    return get_prediction_jobs(
        db,
        include_closed=include_closed,
        min_confidence=min_confidence,
        role_category=role_category,
        source=source,
    )


@router.get("/jobs/{job_id}")
def prediction_job_detail(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = _get_job_or_404(db, job_id)
    return {
        "job_id": job.id,
        "company": job.company,
        "title": job.title,
        "role_category": job.role_category,
        "source": job.source,
        "application_status": job.application_status,
        "verification_status": job.verification_status,
        "stored_prediction": {
            "predicted_priority_score": job.predicted_priority_score,
            "predicted_close_risk_score": job.predicted_close_risk_score,
            "predicted_response_score": job.predicted_response_score,
            "prediction_confidence": job.prediction_confidence,
            "prediction_updated_at": job.prediction_updated_at.isoformat() if job.prediction_updated_at else None,
            "prediction_evidence": job.prediction_evidence or {},
        },
        "priority_prediction": predict_job_priority(db, job),
        "close_risk_prediction": predict_close_risk(db, job),
        "response_likelihood_prediction": predict_response_likelihood(db, job),
        "note": "Prediction details are cautious estimates from stored CareerAgent data, not guarantees.",
    }


@router.get("/source-quality")
def prediction_source_quality(db: Session = Depends(get_db)) -> dict:
    return estimate_source_quality(db)


@router.get("/role-quality")
def prediction_role_quality(db: Session = Depends(get_db)) -> dict:
    return estimate_role_quality(db)


@router.get("/apply-windows")
def prediction_apply_windows(db: Session = Depends(get_db)) -> dict:
    return estimate_best_apply_windows(db)


@router.get("/insights")
def prediction_insights(db: Session = Depends(get_db)) -> list[dict]:
    return generate_prediction_insights(db)


@router.get("/export", response_model=None)
def prediction_export(
    format: str = Query("json"),
    db: Session = Depends(get_db),
):
    try:
        export_payload = get_prediction_data_export(db, format=format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    normalized_format = format.strip().lower()
    if normalized_format == "csv":
        return Response(
            content=str(export_payload),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="careeragent_prediction_export.csv"'},
        )
    return export_payload  # type: ignore[return-value]
