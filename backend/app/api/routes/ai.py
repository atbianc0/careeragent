from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.ai import AIProviderResult, AIProvidersResponse, AIStatusResponse, AITestRequest
from app.services.ai import MockProvider, get_ai_provider, get_provider_availability, normalize_provider_name

router = APIRouter()


@router.get("/status", response_model=AIStatusResponse)
def ai_status() -> AIStatusResponse:
    configured_provider_name = normalize_provider_name(settings.ai_provider)
    configured_provider = get_ai_provider(configured_provider_name)
    active_provider = configured_provider if configured_provider.is_available() else MockProvider()
    openai_provider = get_ai_provider("openai")
    local_provider = get_ai_provider("local")

    if active_provider.name == "mock":
        message = "Using MockProvider. Set AI_PROVIDER=openai and OPENAI_API_KEY in .env to enable OpenAI."
    else:
        message = f"Using {active_provider.name} provider. AI output is still a draft and must be reviewed manually."

    return AIStatusResponse(
        configured_provider=configured_provider_name,
        active_provider=active_provider.name,
        openai_available=openai_provider.is_available(),
        local_available=local_provider.is_available(),
        api_key_present=bool(settings.openai_api_key),
        api_key_preview=None,
        safety_mode=True,
        message=message,
    )


@router.get("/providers", response_model=AIProvidersResponse)
def ai_providers() -> AIProvidersResponse:
    providers = [dict(entry) for entry in get_provider_availability()]
    return AIProvidersResponse(providers=providers)


@router.post("/test", response_model=AIProviderResult)
def ai_test(payload: AITestRequest) -> AIProviderResult:
    provider = get_ai_provider(payload.provider)
    if not provider.is_available():
        raise HTTPException(
            status_code=400,
            detail=provider.unavailable_reason or f"{provider.name} provider is unavailable.",
        )

    result = provider.generate_text(
        payload.task,
        payload.prompt,
        context={"task": payload.task},
    )
    return AIProviderResult(**result)
