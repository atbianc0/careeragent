from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.market import (
    export_market_data,
    get_activity_over_time,
    get_market_dashboard,
    get_market_summary,
    get_outcome_summary,
    get_recommended_insights,
    get_response_rates,
    get_score_summary,
    get_stale_jobs,
    get_top_missing_skills,
    get_top_requested_skills,
)

router = APIRouter()


@router.get("/dashboard")
def market_dashboard(db: Session = Depends(get_db)) -> dict:
    return get_market_dashboard(db)


@router.get("/summary")
def market_summary(db: Session = Depends(get_db)) -> dict:
    return get_market_summary(db)


@router.get("/skills")
def market_skills(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    requested_skills = get_top_requested_skills(db, limit=limit)
    missing_skills = get_top_missing_skills(db, limit=limit)
    return {
        "requested_skills": requested_skills,
        "missing_skills": missing_skills,
        "message": None if (requested_skills or missing_skills) else "Import and score more jobs to see skill analytics.",
    }


@router.get("/scores")
def market_scores(db: Session = Depends(get_db)) -> dict:
    return get_score_summary(db)


@router.get("/outcomes")
def market_outcomes(db: Session = Depends(get_db)) -> dict:
    return {
        "outcome_summary": get_outcome_summary(db),
        "response_rates": get_response_rates(db),
    }


@router.get("/activity")
def market_activity(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> dict:
    return get_activity_over_time(db, days=days)


@router.get("/stale-jobs")
def market_stale_jobs(db: Session = Depends(get_db)) -> list[dict]:
    return get_stale_jobs(db)


@router.get("/insights")
def market_insights(db: Session = Depends(get_db)) -> list[dict]:
    return get_recommended_insights(db)


@router.get("/export", response_model=None)
def market_export(
    format: str = Query("json"),
    db: Session = Depends(get_db),
):
    try:
        export_payload = export_market_data(db, format=format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    normalized_format = format.strip().lower()
    if normalized_format == "csv":
        return Response(
            content=str(export_payload),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="careeragent_market_export.csv"'},
        )
    return export_payload  # type: ignore[return-value]
