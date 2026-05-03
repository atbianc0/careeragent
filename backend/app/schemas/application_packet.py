from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApplicationPacketRead(BaseModel):
    id: int
    job_id: int
    packet_path: str
    tailored_resume_tex_path: str | None = None
    tailored_resume_pdf_path: str | None = None
    cover_letter_path: str | None = None
    recruiter_message_path: str | None = None
    application_questions_path: str | None = None
    application_notes_path: str | None = None
    change_summary_path: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

