from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.job import JobRead


class ApplicationPacketBase(BaseModel):
    job_id: int
    packet_path: str
    tailored_resume_tex_path: str | None = None
    tailored_resume_pdf_path: str | None = None
    cover_letter_path: str | None = None
    cover_letter_pdf_path: str | None = None
    recruiter_message_path: str | None = None
    application_questions_path: str | None = None
    application_notes_path: str | None = None
    change_summary_path: str | None = None
    job_summary_path: str | None = None
    packet_metadata_path: str | None = None
    generation_status: str = "pending"
    generation_error: str | None = None
    generated_at: datetime | None = None


class ApplicationPacketCreate(ApplicationPacketBase):
    pass


class ApplicationPacketRead(ApplicationPacketBase):
    id: int
    created_at: datetime
    updated_at: datetime
    job: JobRead | None = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationPacketGenerateRequest(BaseModel):
    job_id: int
    include_cover_letter: bool = True
    include_recruiter_message: bool = True
    include_application_questions: bool = True
    compile_resume_pdf: bool = True


class ApplicationPacketGenerateResponse(BaseModel):
    packet: ApplicationPacketRead
    job: JobRead
    message: str
    compile_resume_pdf_requested: bool
    compile_resume_pdf_success: bool
    files_created: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApplicationPacketFileResponse(BaseModel):
    packet_id: int
    file_key: str
    path: str
    content: str
    format: str
