from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class EventJobSummary(BaseModel):
    id: int
    company: str
    title: str
    application_status: str

    model_config = ConfigDict(from_attributes=True)


class ApplicationEventCreate(BaseModel):
    job_id: int
    packet_id: int | None = None
    event_type: str
    event_time: datetime | None = None
    old_status: str | None = None
    new_status: str | None = None
    notes: str | None = None
    metadata_json: dict[str, Any] | None = None


class ApplicationEventRead(BaseModel):
    id: int
    job_id: int
    packet_id: int | None = None
    event_type: str
    event_time: datetime
    old_status: str | None = None
    new_status: str | None = None
    notes: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    job: EventJobSummary | None = None

    model_config = ConfigDict(from_attributes=True)
