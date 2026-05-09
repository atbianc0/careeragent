from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.schemas.application_event import ApplicationEventRead
from app.schemas.job import JobRead

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
NOTE_ALIAS = AliasChoices("notes", "note")


class TrackerJobRead(JobRead):
    pass


class StatusUpdateRequest(BaseModel):
    status: str
    notes: Annotated[str | None, Field(validation_alias=NOTE_ALIAS)] = None

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in VALID_APPLICATION_STATUSES:
            raise ValueError(f"Unsupported application status: {value}")
        return normalized


class NoteCreateRequest(BaseModel):
    notes: Annotated[str, Field(validation_alias=NOTE_ALIAS)]

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Notes cannot be empty.")
        return normalized


class FollowUpRequest(BaseModel):
    follow_up_at: datetime
    notes: Annotated[str | None, Field(validation_alias=NOTE_ALIAS)] = None

    model_config = ConfigDict(populate_by_name=True)


class CompleteFollowUpRequest(BaseModel):
    notes: Annotated[str | None, Field(validation_alias=NOTE_ALIAS)] = None

    model_config = ConfigDict(populate_by_name=True)


class TrackerSummary(BaseModel):
    total_jobs: int
    saved_count: int
    packet_ready_count: int
    application_opened_count: int
    applied_count: int
    follow_up_count: int
    interview_count: int
    rejected_count: int
    offer_count: int
    withdrawn_count: int
    closed_before_apply_count: int
    counts_by_status: dict[str, int] = Field(default_factory=dict)
    upcoming_follow_ups: list[TrackerJobRead] = Field(default_factory=list)
    recent_events: list[ApplicationEventRead] = Field(default_factory=list)


class TrackerMutationResponse(BaseModel):
    job: TrackerJobRead
    event: ApplicationEventRead


class OpenApplicationResponse(BaseModel):
    success: bool = True
    job_id: int
    job: TrackerJobRead
    event: ApplicationEventRead
    url: str
    message: str = "Application link opened and logged."


class TrackerEventsQuery(BaseModel):
    limit: int = 20
    job_id: int | None = None
    event_type: str | None = None


class TrackerMetadata(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
