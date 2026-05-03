from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    job_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    employment_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    remote_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    role_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seniority_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    years_experience_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    years_experience_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    required_skills: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    preferred_skills: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    responsibilities: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    requirements: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    education_requirements: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    application_questions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    raw_parsed_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verification_evidence: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    verification_raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_verification_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    posted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    first_seen_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_seen_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_checked_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)
    verification_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    likely_closed_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    skill_match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    role_match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    experience_fit_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    profile_keyword_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    resume_match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    freshness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    location_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    application_ease_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    overall_priority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    scoring_status: Mapped[str] = mapped_column(String(50), default="unscored", nullable=False)
    scoring_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scoring_raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    application_status: Mapped[str] = mapped_column(String(50), default="found", nullable=False)
    application_link_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    packet_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    interview_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    offer_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_before_apply_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    events = relationship("ApplicationEvent", back_populates="job", cascade="all, delete-orphan")
    packets = relationship("ApplicationPacket", back_populates="job", cascade="all, delete-orphan")
