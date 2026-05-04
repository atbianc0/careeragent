from __future__ import annotations

from app.core.config import settings

from .base import AIProvider
from .local_provider import LocalLLMProvider
from .mock_provider import MockProvider
from .openai_provider import OpenAIProvider

SUPPORTED_PROVIDER_NAMES = ("mock", "openai", "local")


def normalize_provider_name(provider_name: str | None) -> str:
    normalized = str(provider_name or "").strip().lower()
    if normalized in SUPPORTED_PROVIDER_NAMES:
        return normalized
    return "mock"


def get_ai_provider(provider_name: str | None = None) -> AIProvider:
    resolved_name = normalize_provider_name(provider_name or settings.ai_provider)
    if resolved_name == "openai":
        return OpenAIProvider()
    if resolved_name == "local":
        return LocalLLMProvider()
    return MockProvider()


def get_active_ai_provider(provider_name: str | None = None) -> AIProvider:
    provider = get_ai_provider(provider_name)
    if provider.is_available():
        return provider
    return MockProvider()


def get_provider_availability() -> list[dict[str, str | bool | None]]:
    providers = [MockProvider(), OpenAIProvider(), LocalLLMProvider()]
    return [
        {
            "name": provider.name,
            "available": provider.is_available(),
            "message": provider.unavailable_reason,
        }
        for provider in providers
    ]
