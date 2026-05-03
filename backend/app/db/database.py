from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings
from app.services.scoring.scoring import calculate_priority_score

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def seed_sample_jobs() -> None:
    from app.models.job import Job

    db: Session = SessionLocal()
    try:
        if db.query(Job).count() > 0:
            return

        samples = [
            {
                "company": "OpenRoad Analytics",
                "title": "Junior Data Scientist",
                "location": "San Francisco, CA",
                "url": "https://example.com/jobs/openroad-data-scientist",
                "source": "sample_seed",
                "job_description": "Early-career data science role focused on experimentation, dashboards, and SQL pipelines.",
                "posted_date": date(2026, 4, 27),
                "first_seen_date": date(2026, 4, 29),
                "last_seen_date": date(2026, 5, 1),
                "last_checked_date": date(2026, 5, 2),
                "verification_status": "verified_open",
                "verification_score": 92.0,
                "likely_closed_score": 8.0,
                "resume_match_score": 86.0,
                "freshness_score": 88.0,
                "location_score": 95.0,
                "application_ease_score": 70.0,
                "application_status": "new",
            },
            {
                "company": "Northstar Data",
                "title": "Data Engineer I",
                "location": "Remote",
                "url": "https://example.com/jobs/northstar-data-engineer",
                "source": "sample_seed",
                "job_description": "Entry-level data engineering role working with ETL jobs, orchestration, and warehouse modeling.",
                "posted_date": date(2026, 4, 24),
                "first_seen_date": date(2026, 4, 25),
                "last_seen_date": date(2026, 5, 2),
                "last_checked_date": date(2026, 5, 2),
                "verification_status": "needs_review",
                "verification_score": 74.0,
                "likely_closed_score": 22.0,
                "resume_match_score": 81.0,
                "freshness_score": 71.0,
                "location_score": 100.0,
                "application_ease_score": 78.0,
                "application_status": "researching",
            },
            {
                "company": "Harbor ML",
                "title": "ML Engineer Intern",
                "location": "Berkeley, CA",
                "url": "https://example.com/jobs/harbor-ml-intern",
                "source": "sample_seed",
                "job_description": "Internship focused on model evaluation, Python tooling, and production experimentation support.",
                "posted_date": date(2026, 4, 18),
                "first_seen_date": date(2026, 4, 20),
                "last_seen_date": date(2026, 4, 28),
                "last_checked_date": date(2026, 5, 2),
                "verification_status": "stale_listing",
                "verification_score": 48.0,
                "likely_closed_score": 61.0,
                "resume_match_score": 84.0,
                "freshness_score": 42.0,
                "location_score": 89.0,
                "application_ease_score": 64.0,
                "application_status": "watching",
            },
        ]

        for payload in samples:
            payload["overall_priority_score"] = calculate_priority_score(
                resume_match_score=payload["resume_match_score"],
                verification_score=payload["verification_score"],
                freshness_score=payload["freshness_score"],
                location_score=payload["location_score"],
                application_ease_score=payload["application_ease_score"],
            )
            db.add(Job(**payload))

        db.commit()
    finally:
        db.close()

