from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AutofillRequestBase(BaseModel):
    job_id: int
    packet_id: int | None = None
    allow_base_resume_upload: bool = False
    fill_sensitive_optional_fields: bool = False


class AutofillPreviewRequest(AutofillRequestBase):
    pass


class AutofillStartRequest(AutofillRequestBase):
    dry_run: bool = False


class AutofillFieldResult(BaseModel):
    field_key: str
    label: str | None = None
    selector: str | None = None
    filled: bool
    confidence: float
    reason: str


class AutofillPreviewResponse(BaseModel):
    job_id: int
    packet_id: int | None = None
    proposed_values: dict[str, Any] = Field(default_factory=dict)
    files_available: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    manual_review_required: bool = True
    message: str


class AutofillStartResponse(BaseModel):
    job_id: int
    packet_id: int | None = None
    status: str
    opened_url: str
    fields_detected: int
    fields_filled: int
    fields_skipped: int
    files_uploaded: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    manual_review_required: bool = True
    message: str
    field_results: list[AutofillFieldResult] = Field(default_factory=list)


class AutofillStatusResponse(BaseModel):
    status: str
    stage: str
    message: str
    manual_review_required: bool = True
    playwright_installed: bool
    chromium_installed: bool
    headed_browser_supported: bool
    install_command: str
    environment_note: str
    recent_sessions: list[dict[str, Any]] = Field(default_factory=list)


class AutofillSafetyResponse(BaseModel):
    blocked_final_action_words: list[str] = Field(default_factory=list)
    safety_rules: list[str] = Field(default_factory=list)
