from datetime import date

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings
from app.services.scoring.scoring import calculate_priority_score, freshness_score_value

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()
SAMPLE_JOB_SOURCE = "sample_seed"
VALID_APPLICATION_STATUSES = {
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
}
STATIC_SAMPLE_FIELDS = [
    "company",
    "title",
    "location",
    "url",
    "source",
    "job_description",
    "employment_type",
    "remote_status",
    "role_category",
    "seniority_level",
    "required_skills",
    "preferred_skills",
    "responsibilities",
    "requirements",
    "education_requirements",
    "application_questions",
    "posted_date",
    "first_seen_date",
]
JOB_COLUMN_DEFINITIONS = {
    "employment_type": "VARCHAR(100)",
    "remote_status": "VARCHAR(50)",
    "role_category": "VARCHAR(100)",
    "seniority_level": "VARCHAR(50)",
    "years_experience_min": "INTEGER",
    "years_experience_max": "INTEGER",
    "salary_min": "FLOAT",
    "salary_max": "FLOAT",
    "salary_currency": "VARCHAR(20)",
    "required_skills": "JSON",
    "preferred_skills": "JSON",
    "responsibilities": "JSON",
    "requirements": "JSON",
    "education_requirements": "JSON",
    "application_questions": "JSON",
    "raw_parsed_data": "JSON",
    "verification_evidence": "JSON",
    "verification_raw_data": "JSON",
    "last_verification_error": "TEXT",
    "skill_match_score": "FLOAT",
    "role_match_score": "FLOAT",
    "experience_fit_score": "FLOAT",
    "profile_keyword_score": "FLOAT",
    "scoring_status": "VARCHAR(50)",
    "scoring_evidence": "JSON",
    "scoring_raw_data": "JSON",
    "scored_at": "TIMESTAMP WITH TIME ZONE",
    "application_link_opened_at": "TIMESTAMP WITH TIME ZONE",
    "packet_generated_at": "TIMESTAMP WITH TIME ZONE",
    "applied_at": "TIMESTAMP WITH TIME ZONE",
    "follow_up_at": "TIMESTAMP WITH TIME ZONE",
    "interview_at": "TIMESTAMP WITH TIME ZONE",
    "rejected_at": "TIMESTAMP WITH TIME ZONE",
    "offer_at": "TIMESTAMP WITH TIME ZONE",
    "withdrawn_at": "TIMESTAMP WITH TIME ZONE",
    "closed_before_apply_at": "TIMESTAMP WITH TIME ZONE",
    "user_notes": "TEXT",
    "next_action": "TEXT",
    "next_action_due_at": "TIMESTAMP WITH TIME ZONE",
}
APPLICATION_PACKET_COLUMN_DEFINITIONS = {
    "cover_letter_pdf_path": "VARCHAR(500)",
    "job_summary_path": "VARCHAR(500)",
    "packet_metadata_path": "VARCHAR(500)",
    "generation_status": "VARCHAR(50) DEFAULT 'pending'",
    "generation_error": "TEXT",
    "generated_at": "TIMESTAMP WITH TIME ZONE",
    "updated_at": "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",
}
APPLICATION_EVENT_COLUMN_DEFINITIONS = {
    "packet_id": "INTEGER",
    "old_status": "VARCHAR(50)",
    "new_status": "VARCHAR(50)",
    "metadata_json": "JSON",
    "created_at": "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _sync_job_columns()
    _sync_application_packet_columns()
    _sync_application_event_columns()
    backfill_job_defaults()
    backfill_application_packet_defaults()
    backfill_application_event_defaults()
    normalize_sample_jobs()


def _sync_job_columns() -> None:
    inspector = inspect(engine)
    if "jobs" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("jobs")}
    missing_columns = {
        column_name: column_type
        for column_name, column_type in JOB_COLUMN_DEFINITIONS.items()
        if column_name not in existing_columns
    }
    if not missing_columns:
        return

    with engine.begin() as connection:
        for column_name, column_type in missing_columns.items():
            connection.execute(text(f"ALTER TABLE jobs ADD COLUMN {column_name} {column_type}"))


def _sync_application_packet_columns() -> None:
    inspector = inspect(engine)
    if "application_packets" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("application_packets")}
    missing_columns = {
        column_name: column_type
        for column_name, column_type in APPLICATION_PACKET_COLUMN_DEFINITIONS.items()
        if column_name not in existing_columns
    }
    if not missing_columns:
        return

    with engine.begin() as connection:
        for column_name, column_type in missing_columns.items():
            connection.execute(text(f"ALTER TABLE application_packets ADD COLUMN {column_name} {column_type}"))


def _sync_application_event_columns() -> None:
    inspector = inspect(engine)
    if "application_events" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("application_events")}
    missing_columns = {
        column_name: column_type
        for column_name, column_type in APPLICATION_EVENT_COLUMN_DEFINITIONS.items()
        if column_name not in existing_columns
    }

    with engine.begin() as connection:
        for column_name, column_type in missing_columns.items():
            connection.execute(text(f"ALTER TABLE application_events ADD COLUMN {column_name} {column_type}"))

        if "packet_id" in missing_columns:
            connection.execute(
                text(
                    "ALTER TABLE application_events "
                    "ADD CONSTRAINT application_events_packet_id_fkey "
                    "FOREIGN KEY (packet_id) REFERENCES application_packets(id)"
                )
            )
        connection.execute(text("ALTER TABLE application_events ALTER COLUMN notes DROP NOT NULL"))


def backfill_job_defaults() -> None:
    from app.models.job import Job
    from app.services.jobs.job_store import calculate_freshness_score

    db: Session = SessionLocal()
    try:
        jobs = db.query(Job).all()
        if not jobs:
            return

        for job in jobs:
            if job.url is None:
                job.url = ""
            if job.job_description is None:
                job.job_description = ""
            if job.required_skills is None:
                job.required_skills = []
            if job.preferred_skills is None:
                job.preferred_skills = []
            if job.responsibilities is None:
                job.responsibilities = []
            if job.requirements is None:
                job.requirements = []
            if job.education_requirements is None:
                job.education_requirements = []
            if job.application_questions is None:
                job.application_questions = []
            if job.raw_parsed_data is None:
                job.raw_parsed_data = {}
            if job.verification_evidence is None:
                job.verification_evidence = []
            if job.verification_raw_data is None:
                job.verification_raw_data = {}
            if job.verification_status is None:
                job.verification_status = "unknown"
            if job.verification_score is None:
                job.verification_score = 0.0
            if job.likely_closed_score is None:
                job.likely_closed_score = 0.0
            if job.skill_match_score is None:
                job.skill_match_score = 0.0
            if job.role_match_score is None:
                job.role_match_score = 0.0
            if job.experience_fit_score is None:
                job.experience_fit_score = 0.0
            if job.profile_keyword_score is None:
                job.profile_keyword_score = 0.0
            if job.resume_match_score is None:
                job.resume_match_score = 0.0
            if job.location_score is None:
                job.location_score = 50.0
            if job.application_ease_score is None:
                job.application_ease_score = 50.0
            if job.scoring_status is None:
                job.scoring_status = "unscored"
            if job.scoring_evidence is None:
                job.scoring_evidence = {}
            if job.scoring_raw_data is None:
                job.scoring_raw_data = {}
            if job.application_status is None:
                job.application_status = "found"
            elif job.application_status not in VALID_APPLICATION_STATUSES:
                job.application_status = "saved" if job.source != SAMPLE_JOB_SOURCE else "found"
            elif job.application_status == "found" and job.source != SAMPLE_JOB_SOURCE:
                job.application_status = "saved"

            job.freshness_score = calculate_freshness_score(job.posted_date, job.first_seen_date)
            job.overall_priority_score = calculate_priority_score(
                resume_match_score=job.resume_match_score or 0.0,
                verification_score=job.verification_score or 0.0,
                freshness_score=job.freshness_score or 50.0,
                location_score=job.location_score or 50.0,
                application_ease_score=job.application_ease_score or 50.0,
            )

        db.commit()
    finally:
        db.close()


def backfill_application_packet_defaults() -> None:
    from app.models.application_packet import ApplicationPacket

    db: Session = SessionLocal()
    try:
        packets = db.query(ApplicationPacket).all()
        if not packets:
            return

        for packet in packets:
            if not packet.generation_status:
                has_outputs = any(
                    [
                        packet.tailored_resume_tex_path,
                        packet.cover_letter_path,
                        packet.recruiter_message_path,
                        packet.application_questions_path,
                        packet.application_notes_path,
                        packet.change_summary_path,
                    ]
                )
                packet.generation_status = "completed" if has_outputs else "pending"
            if packet.generated_at is None and packet.created_at is not None:
                packet.generated_at = packet.created_at
            if packet.updated_at is None and packet.created_at is not None:
                packet.updated_at = packet.created_at

        db.commit()
    finally:
        db.close()


def backfill_application_event_defaults() -> None:
    from app.models.application_event import ApplicationEvent

    db: Session = SessionLocal()
    try:
        events = db.query(ApplicationEvent).all()
        if not events:
            return

        for event in events:
            if event.created_at is None and event.event_time is not None:
                event.created_at = event.event_time

        db.commit()
    finally:
        db.close()


def _sample_jobs() -> list[dict]:
    return [
        {
            "company": "OpenRoad Analytics",
            "title": "Junior Data Scientist",
            "location": "San Francisco, CA",
            "url": "https://example.com/jobs/openroad-data-scientist",
            "source": SAMPLE_JOB_SOURCE,
            "job_description": "Early-career data science role focused on experimentation, dashboards, and SQL pipelines.",
            "employment_type": "Full-time",
            "remote_status": "Hybrid",
            "role_category": "Data Scientist",
            "seniority_level": "Entry Level",
            "required_skills": ["Python", "SQL", "Pandas", "experimentation"],
            "preferred_skills": ["Tableau"],
            "responsibilities": ["Support experiments and dashboards", "Build SQL-driven analyses"],
            "requirements": ["Python experience", "SQL experience"],
            "education_requirements": ["Bachelor's degree or equivalent experience"],
            "application_questions": ["Why are you interested in OpenRoad Analytics?"],
            "raw_parsed_data": {"parser": SAMPLE_JOB_SOURCE, "sample_demo": True},
            "posted_date": date(2026, 4, 27),
            "first_seen_date": date(2026, 4, 29),
            "last_seen_date": date(2026, 5, 1),
            "last_checked_date": None,
            "verification_status": "unknown",
            "verification_score": 0.0,
            "likely_closed_score": 0.0,
            "skill_match_score": 0.0,
            "role_match_score": 0.0,
            "experience_fit_score": 0.0,
            "profile_keyword_score": 0.0,
            "resume_match_score": 0.0,
            "freshness_score": 0.0,
            "location_score": 50.0,
            "application_ease_score": 50.0,
            "scoring_status": "unscored",
            "scoring_evidence": {},
            "scoring_raw_data": {},
            "scored_at": None,
            "application_status": "found",
            "verification_evidence": [],
            "verification_raw_data": {},
            "last_verification_error": None,
        },
        {
            "company": "Northstar Data",
            "title": "Data Engineer I",
            "location": "Remote",
            "url": "https://example.com/jobs/northstar-data-engineer",
            "source": SAMPLE_JOB_SOURCE,
            "job_description": "Entry-level data engineering role working with ETL jobs, orchestration, and warehouse modeling.",
            "employment_type": "Full-time",
            "remote_status": "Remote",
            "role_category": "Data Engineer",
            "seniority_level": "Entry Level",
            "required_skills": ["Python", "SQL", "ETL", "data pipelines"],
            "preferred_skills": ["Airflow", "dbt"],
            "responsibilities": ["Maintain ETL jobs", "Support warehouse modeling"],
            "requirements": ["Experience with SQL", "Exposure to orchestration tools"],
            "education_requirements": ["Bachelor's degree in a related field"],
            "application_questions": ["Are you authorized to work in the United States?"],
            "raw_parsed_data": {"parser": SAMPLE_JOB_SOURCE, "sample_demo": True},
            "posted_date": date(2026, 4, 24),
            "first_seen_date": date(2026, 4, 25),
            "last_seen_date": date(2026, 5, 2),
            "last_checked_date": None,
            "verification_status": "unknown",
            "verification_score": 0.0,
            "likely_closed_score": 0.0,
            "skill_match_score": 0.0,
            "role_match_score": 0.0,
            "experience_fit_score": 0.0,
            "profile_keyword_score": 0.0,
            "resume_match_score": 0.0,
            "freshness_score": 0.0,
            "location_score": 50.0,
            "application_ease_score": 50.0,
            "scoring_status": "unscored",
            "scoring_evidence": {},
            "scoring_raw_data": {},
            "scored_at": None,
            "application_status": "found",
            "verification_evidence": [],
            "verification_raw_data": {},
            "last_verification_error": None,
        },
        {
            "company": "Harbor ML",
            "title": "ML Engineer Intern",
            "location": "Berkeley, CA",
            "url": "https://example.com/jobs/harbor-ml-intern",
            "source": SAMPLE_JOB_SOURCE,
            "job_description": "Internship focused on model evaluation, Python tooling, and production experimentation support.",
            "employment_type": "Internship",
            "remote_status": "Onsite",
            "role_category": "ML Engineer",
            "seniority_level": "Internship",
            "required_skills": ["Python", "machine learning", "PyTorch"],
            "preferred_skills": ["TensorFlow"],
            "responsibilities": ["Evaluate models", "Support experimentation tooling"],
            "requirements": ["Python experience", "Interest in machine learning systems"],
            "education_requirements": ["Currently pursuing a degree"],
            "application_questions": ["Tell us about yourself."],
            "raw_parsed_data": {"parser": SAMPLE_JOB_SOURCE, "sample_demo": True},
            "posted_date": date(2026, 4, 18),
            "first_seen_date": date(2026, 4, 20),
            "last_seen_date": date(2026, 4, 28),
            "last_checked_date": None,
            "verification_status": "unknown",
            "verification_score": 0.0,
            "likely_closed_score": 0.0,
            "skill_match_score": 0.0,
            "role_match_score": 0.0,
            "experience_fit_score": 0.0,
            "profile_keyword_score": 0.0,
            "resume_match_score": 0.0,
            "freshness_score": 0.0,
            "location_score": 50.0,
            "application_ease_score": 50.0,
            "scoring_status": "unscored",
            "scoring_evidence": {},
            "scoring_raw_data": {},
            "scored_at": None,
            "application_status": "found",
            "verification_evidence": [],
            "verification_raw_data": {},
            "last_verification_error": None,
        },
    ]


def seed_sample_jobs() -> None:
    from app.models.job import Job
    from app.services.jobs.job_store import calculate_freshness_score

    if not settings.enable_sample_jobs:
        return

    db: Session = SessionLocal()
    try:
        if db.query(Job).count() > 0:
            return

        samples = _sample_jobs()

        for payload in samples:
            payload["freshness_score"] = calculate_freshness_score(payload.get("posted_date"), payload.get("first_seen_date"))
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


def normalize_sample_jobs() -> None:
    from app.models.job import Job
    from app.services.jobs.job_store import calculate_freshness_score

    db: Session = SessionLocal()
    try:
        sample_payloads = {payload["url"]: payload for payload in _sample_jobs()}
        sample_jobs = db.query(Job).filter(Job.source == SAMPLE_JOB_SOURCE).all()
        if not sample_jobs:
            return

        for job in sample_jobs:
            payload = sample_payloads.get(job.url or "")
            if payload:
                for field in STATIC_SAMPLE_FIELDS:
                    value = payload.get(field)
                    setattr(job, field, value)

            raw_parsed_data = dict(job.raw_parsed_data or {})
            raw_parsed_data["sample_demo"] = True
            raw_parsed_data.setdefault("parser", SAMPLE_JOB_SOURCE)
            job.raw_parsed_data = raw_parsed_data

            if not job.skill_match_score:
                job.skill_match_score = 0.0
            if not job.role_match_score:
                job.role_match_score = 0.0
            if not job.experience_fit_score:
                job.experience_fit_score = 0.0
            if not job.profile_keyword_score:
                job.profile_keyword_score = 0.0
            if not job.resume_match_score:
                job.resume_match_score = 0.0
            if not job.location_score:
                job.location_score = 50.0
            if not job.application_ease_score:
                job.application_ease_score = 50.0
            if not job.scoring_status:
                job.scoring_status = "unscored"
            if job.scoring_evidence is None:
                job.scoring_evidence = {}
            if job.scoring_raw_data is None:
                job.scoring_raw_data = {}

            if (
                job.verification_status == "unknown"
                and not job.verification_score
                and not job.likely_closed_score
                and not job.verification_evidence
            ):
                job.verification_raw_data = {}
                job.last_verification_error = None
                job.last_checked_date = None
                job.closed_date = None

            job.freshness_score = freshness_score_value(job.posted_date, job.first_seen_date)
            job.overall_priority_score = calculate_priority_score(
                resume_match_score=job.resume_match_score,
                verification_score=job.verification_score,
                freshness_score=job.freshness_score,
                location_score=job.location_score,
                application_ease_score=job.application_ease_score,
            )

        db.commit()
    finally:
        db.close()
