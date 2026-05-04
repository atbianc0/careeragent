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
    local_available: bool
    api_key_present: bool
    api_key_preview: None = None
    safety_mode: bool = True
    message: str


class AITestRequest(BaseModel):
    provider: str = "mock"
    task: str = "test"
    prompt: str = "Write one short safe sentence."
