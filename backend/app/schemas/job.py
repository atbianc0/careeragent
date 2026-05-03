from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class JobRead(BaseModel):
    id: int
    company: str
    title: str
    location: str
    url: str
    source: str
    job_description: str
    posted_date: date | None = None
    first_seen_date: date | None = None
    last_seen_date: date | None = None
    last_checked_date: date | None = None
    closed_date: date | None = None
    verification_status: str
    verification_score: float
    likely_closed_score: float
    resume_match_score: float
    freshness_score: float
    location_score: float
    application_ease_score: float
    overall_priority_score: float
    application_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

