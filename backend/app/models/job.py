from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, String, Text
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
    posted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    first_seen_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_seen_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_checked_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(50), default="unverified", nullable=False)
    verification_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    likely_closed_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    resume_match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    freshness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    location_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    application_ease_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    overall_priority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    application_status: Mapped[str] = mapped_column(String(50), default="new", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    events = relationship("ApplicationEvent", back_populates="job", cascade="all, delete-orphan")
    packets = relationship("ApplicationPacket", back_populates="job", cascade="all, delete-orphan")
