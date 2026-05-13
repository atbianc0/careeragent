from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AIProviderResult(BaseModel):
    provider: str
    success: bool
    task: str
    content: str = ""
    parsed_json: dict[str, Any] | list[Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    raw: dict[str, Any] | None = None


class AIProviderInfo(BaseModel):
    name: str
    available: bool
    message: str | None = None


class AIProvidersResponse(BaseModel):
    providers: list[AIProviderInfo] = Field(default_factory=list)


class AIStatusResponse(BaseModel):
    configured_provider: str
    active_provider: str
    openai_available: bool
    gemini_available: bool
    api_key_present: bool
    gemini_key_present: bool = False
    api_key_preview: None = None
    safety_mode: bool = True
    message: str
    ai_allow_external_calls: bool = False
    active_ai_provider: str = "mock"
    openai_configured: bool = False
    gemini_configured: bool = False
    both_provider_keys_configured: bool = False
    openai_model: str = ""
    gemini_model: str = ""
    current_model: str = "mock"
    allowed_ai_actions: list[str] = Field(default_factory=list)
    recent_api_usage: list[dict[str, Any]] = Field(default_factory=list)


class AITestRequest(BaseModel):
    task: str = "draft_cover_letter"
    prompt: str = "Write one short safe sentence."
    user_enabled: bool = True
    user_triggered: bool = True
    max_output_tokens: int = Field(default=120, ge=16, le=500)
