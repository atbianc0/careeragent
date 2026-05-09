from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class JobSource(Base):
    __tablename__ = "job_sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str] = mapped_column(Text, default="", nullable=False, index=True)
    ats_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    jobs_found: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovery_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class JobDiscoveryRun(Base):
    __tablename__ = "job_discovery_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text, default="", nullable=False)
    location: Mapped[str] = mapped_column(String(255), default="Bay Area", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_candidates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    candidates = relationship("JobCandidate", back_populates="discovery_run", cascade="all, delete-orphan")


class JobCandidate(Base):
    __tablename__ = "job_candidates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    discovery_run_id: Mapped[int] = mapped_column(ForeignKey("job_discovery_runs.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str] = mapped_column(String(255), default="Unknown Company", nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="Unknown Title", nullable=False)
    location: Mapped[str] = mapped_column(String(255), default="Unknown", nullable=False)
    url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    role_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    seniority_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    level_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_fit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    remote_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    required_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    preferred_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    years_experience_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    years_experience_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    education_requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    missing_fields: Mapped[list | None] = mapped_column(JSON, nullable=True)
    posted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    filter_status: Mapped[str] = mapped_column(String(50), default="candidate", nullable=False, index=True)
    filter_reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)
    duplicate_key: Mapped[str] = mapped_column(String(500), default="", nullable=False, index=True)
    duplicate_of_job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    imported_job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    discovery_run = relationship("JobDiscoveryRun", back_populates="candidates")
