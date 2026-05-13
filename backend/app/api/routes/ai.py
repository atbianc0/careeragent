from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.ai import AIProviderResult, AIProvidersResponse, AIStatusResponse, AITestRequest
from app.services.ai import (
    MockProvider,
    external_api_status,
    get_ai_provider,
    get_provider_availability,
    normalize_provider_name,
    require_ai_allowed,
)
from app.services.ai.policy import normalize_api_action

router = APIRouter()


@router.get("/status", response_model=AIStatusResponse)
def ai_status() -> AIStatusResponse:
    configured_provider_name = normalize_provider_name(settings.ai_provider)
    configured_provider = get_ai_provider(configured_provider_name)
    active_provider = configured_provider if configured_provider.is_available() else MockProvider()
    openai_provider = get_ai_provider("openai")
    gemini_provider = get_ai_provider("gemini")

    policy_status = external_api_status()
    if configured_provider_name != "mock" and not configured_provider.is_available():
        message = configured_provider.unavailable_reason or (
            f"{configured_provider_name} is selected but unavailable. Check AI_ALLOW_EXTERNAL_CALLS and the provider key."
        )
    elif active_provider.name == "mock":
        message = (
            "External AI calls are disabled unless AI_ALLOW_EXTERNAL_CALLS=true is enabled in .env "
            "and you explicitly trigger an allowed AI writing/query action."
        )
    else:
        message = f"Using {active_provider.name} provider. AI output is still a draft and must be reviewed manually."

    return AIStatusResponse(
        configured_provider=configured_provider_name,
        active_provider=active_provider.name,
        openai_available=openai_provider.is_available(),
        gemini_available=gemini_provider.is_available(),
        api_key_present=bool(settings.openai_api_key),
        gemini_key_present=bool(settings.gemini_api_key),
        api_key_preview=None,
        safety_mode=True,
        message=message,
        **policy_status,
    )


@router.get("/providers", response_model=AIProvidersResponse)
def ai_providers() -> AIProvidersResponse:
    providers = [dict(entry) for entry in get_provider_availability()]
    return AIProvidersResponse(providers=providers)


@router.post("/test", response_model=AIProviderResult)
def ai_test(payload: AITestRequest) -> AIProviderResult:
    action = normalize_api_action(payload.task)
    policy_result = require_ai_allowed(
        action,
        user_enabled=payload.user_enabled,
        user_triggered=payload.user_triggered,
    )
    if not policy_result.get("allowed"):
        return AIProviderResult(
            provider=policy_result.get("provider", "mock"),
            success=False,
            task=action,
            content="",
            warnings=[policy_result.get("message", "AI provider call blocked by policy.")],
            safety_notes=["No external provider request was made."],
            raw={
                "api_used": False,
                "api_action": action,
                "blocked_reason": policy_result.get("reason", "blocked_by_policy"),
                "provider": policy_result.get("provider", "mock"),
                "user_triggered": payload.user_triggered,
                "model": policy_result.get("model"),
            },
        )

    provider = get_ai_provider()
    if not provider.is_available():
        return AIProviderResult(
            provider=provider.name,
            success=False,
            task=payload.task,
            content="",
            warnings=[provider.unavailable_reason or f"{provider.name} provider is unavailable."],
            safety_notes=["No external provider request was made."],
            raw={
                "api_used": False,
                "api_action": action,
                "blocked_reason": "provider_unavailable",
                "provider": provider.name,
                "selected_provider": settings.ai_provider,
            },
        )

    result = provider.generate_text(
        action,
        payload.prompt,
        context={
            "task": action,
            "api_action": action,
            "user_enabled": payload.user_enabled,
            "user_triggered": payload.user_triggered,
            "max_output_tokens": payload.max_output_tokens,
            "test_call": True,
        },
    )
    return AIProviderResult(**result)
