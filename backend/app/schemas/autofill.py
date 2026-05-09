from __future__ import annotations

from typing import Any, Literal

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
    mode: Literal["headless_test", "visible_review"] | None = None
    keep_browser_open: bool = False
    keep_open_seconds: int | None = Field(default=None, ge=0, le=1800)


class AutofillManualValue(BaseModel):
    key: str
    label: str
    value: str


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
    manual_values: list[AutofillManualValue] = Field(default_factory=list)
    files_available: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    manual_review_required: bool = True
    message: str


class AutofillStartResponse(BaseModel):
    success: bool = True
    autofill_effective: bool = False
    can_continue_in_browser: bool = False
    job_id: int
    packet_id: int | None = None
    status: str
    mode: str | None = None
    session_mode: str = "headless_test"
    session_id: str | None = None
    browser_mode: str = "headed"
    opened_url: str
    fields_detected: int
    fields_filled: int
    fields_skipped: int
    files_uploaded: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    manual_review_required: bool = True
    message: str
    suggested_fix: str | None = None
    fix_command: str | None = None
    details: str | None = None
    no_fields_reason: str | None = None
    recommended_next_action: str | None = None
    screenshot_path: str | None = None
    screenshot_url: str | None = None
    manual_values: list[AutofillManualValue] = Field(default_factory=list)
    field_results: list[AutofillFieldResult] = Field(default_factory=list)


class AutofillSessionRead(BaseModel):
    session_id: str
    job_id: int
    opened_url: str
    mode: str
    created_at: str


class AutofillSessionListResponse(BaseModel):
    sessions: list[AutofillSessionRead] = Field(default_factory=list)


class AutofillSessionCloseResponse(BaseModel):
    success: bool = True
    session: dict[str, Any]


class AutofillSessionCleanupResponse(BaseModel):
    success: bool = True
    closed_sessions: list[dict[str, Any]] = Field(default_factory=list)


class AutofillStatusResponse(BaseModel):
    status: str
    stage: str
    message: str
    manual_review_required: bool = True
    browser_mode: Literal["headless", "headed"]
    visible_autofill_available: bool
    headless_diagnostic_available: bool
    can_continue_from_autofill: bool
    recommended_user_action: Literal["open_in_browser", "fill_application"]
    active_sessions: list[AutofillSessionRead] = Field(default_factory=list)
    playwright_installed: bool
    chromium_installed: bool
    headed_browser_supported: bool
    headed_display_available: bool
    configured_browser_mode: str
    playwright_headless: bool
    playwright_use_xvfb: bool
    playwright_slow_mo_ms: int
    install_command: str
    playwright_install_hint: str
    python_executable: str
    backend_runtime: Literal["local", "docker", "unknown"]
    database_host_hint: str
    environment_note: str
    recent_sessions: list[dict[str, Any]] = Field(default_factory=list)


class AutofillSafetyResponse(BaseModel):
    blocked_final_action_words: list[str] = Field(default_factory=list)
    safety_rules: list[str] = Field(default_factory=list)
