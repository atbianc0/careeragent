from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class ApplicationPacket(Base):
    __tablename__ = "application_packets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    packet_path: Mapped[str] = mapped_column(String(500), nullable=False)
    tailored_resume_tex_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tailored_resume_pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_letter_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recruiter_message_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    application_questions_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    application_notes_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    change_summary_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("Job", back_populates="packets")
