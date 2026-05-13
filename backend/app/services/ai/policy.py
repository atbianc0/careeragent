from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

# External API use is assistive and optional. Core CareerAgent workflows remain
# local/rule-based: parsing, saved-source search, matching, scoring,
# verification, insights, predictions, tracking, autofill, and applying do not
# require or call paid external providers.

VALID_AI_PROVIDERS = {"mock", "openai", "gemini"}

ALLOWED_AI_ACTIONS = {
    "tailor_resume",
    "draft_cover_letter",
    "draft_recruiter_message",
    "draft_application_answer",
    "generate_job_search_queries",
}

DISALLOWED_ACTION_MESSAGES = {
    "parse_job_url": "AI is not allowed for job URL parsing. CareerAgent parsing is local/rule-based.",
    "parse_job_posting_core": "AI is not allowed for core job parsing. CareerAgent parsing is local/rule-based.",
    "score_job": "AI is not allowed for job scoring. CareerAgent scoring is local/rule-based.",
    "match_job": "AI is not allowed for job matching. CareerAgent matching is local/rule-based.",
    "verify_job": "AI is not allowed for job verification. CareerAgent verification is local/rule-based.",
    "discover_sources": "AI is not allowed for source discovery. Saved ATS source discovery is local/source-based.",
    "search_saved_sources": "AI is not allowed for saved-source search. Saved ATS source search is local/source-based.",
    "generate_insights": "AI is not allowed for insights. CareerAgent insights use local processing.",
    "predict_outcome_core": "AI is not allowed for prediction estimates. CareerAgent predictions are local/rule-based.",
    "autofill": "AI is not allowed for autofill.",
    "submit_application": "AI is never allowed to submit applications.",
}

TASK_ACTION_MAP = {
    "resume_tailor": "tailor_resume",
    "tailor_resume": "tailor_resume",
    "cover_letter": "draft_cover_letter",
    "draft_cover_letter": "draft_cover_letter",
    "recruiter_message": "draft_recruiter_message",
    "draft_recruiter_message": "draft_recruiter_message",
    "application_questions": "draft_application_answer",
    "draft_application_answer": "draft_application_answer",
    "job_finder_queries": "generate_job_search_queries",
    "generate_job_search_queries": "generate_job_search_queries",
    "job_parse": "parse_job_posting_core",
    "market_insights": "generate_insights",
    "discover_sources_unattended": "discover_sources",
    "search_sources_unattended": "search_saved_sources",
}

RECENT_API_POLICY_EVENTS: list[dict[str, Any]] = []
MAX_POLICY_EVENTS = 50


def normalize_api_action(action_or_task: str | None) -> str:
    normalized = str(action_or_task or "").strip().lower()
    return TASK_ACTION_MAP.get(normalized, normalized)


def _event(action: str, provider: str, allowed: bool, reason: str, user_triggered: bool) -> dict[str, Any]:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "provider": provider,
        "allowed": allowed,
        "reason": reason,
        "user_triggered": user_triggered,
    }
    RECENT_API_POLICY_EVENTS.append(entry)
    del RECENT_API_POLICY_EVENTS[:-MAX_POLICY_EVENTS]
    return entry


def _result(
    *,
    allowed: bool,
    action: str,
    provider: str,
    reason: str,
    message: str,
    user_triggered: bool,
    model: str | None = None,
) -> dict[str, Any]:
    _event(action, provider, allowed, reason, user_triggered)
    return {
        "allowed": allowed,
        "reason": reason,
        "message": message,
        "api_used": False,
        "api_action": action,
        "provider": provider,
        "user_triggered": user_triggered,
        "model": model,
    }


def selected_ai_provider() -> str:
    provider = str(settings.ai_provider or "mock").strip().lower()
    return provider if provider in VALID_AI_PROVIDERS else "mock"


def selected_ai_model(provider: str | None = None) -> str | None:
    resolved = provider or selected_ai_provider()
    if resolved == "openai":
        return settings.openai_model
    if resolved == "gemini":
        return settings.gemini_model
    return None


def is_ai_allowed(
    action: str,
    user_enabled: bool = False,
    user_triggered: bool = False,
) -> bool:
    return bool(
        require_ai_allowed(
            action=action,
            user_enabled=user_enabled,
            user_triggered=user_triggered,
        ).get("allowed")
    )


def require_ai_allowed(
    action: str,
    user_enabled: bool = False,
    user_triggered: bool = False,
) -> dict[str, Any]:
    resolved_action = normalize_api_action(action)
    configured_provider = str(settings.ai_provider or "mock").strip().lower()
    resolved_provider = selected_ai_provider()

    if not user_enabled:
        return _result(
            allowed=False,
            action=resolved_action,
            provider=resolved_provider,
            reason="user_toggle_disabled",
            message="AI calls require the matching Settings/UI toggle before an explicit action can use them.",
            user_triggered=user_triggered,
            model=selected_ai_model(resolved_provider),
        )
    if not user_triggered:
        return _result(
            allowed=False,
            action=resolved_action,
            provider=resolved_provider,
            reason="not_user_triggered",
            message="AI calls are blocked unless the user explicitly triggers an allowed action.",
            user_triggered=user_triggered,
            model=selected_ai_model(resolved_provider),
        )

    if configured_provider not in VALID_AI_PROVIDERS:
        return _result(
            allowed=False,
            action=resolved_action,
            provider=resolved_provider,
            reason="invalid_provider",
            message=f"AI_PROVIDER={configured_provider!r} is not valid. Use mock, openai, or gemini.",
            user_triggered=user_triggered,
        )

    if resolved_action not in ALLOWED_AI_ACTIONS:
        return _result(
            allowed=False,
            action=resolved_action,
            provider=resolved_provider,
            reason="action_not_allowed",
            message=DISALLOWED_ACTION_MESSAGES.get(
                resolved_action,
                f"AI is not allowed for action '{resolved_action}'.",
            ),
            user_triggered=user_triggered,
            model=selected_ai_model(resolved_provider),
        )

    if resolved_provider == "mock":
        return _result(
            allowed=True,
            action=resolved_action,
            provider=resolved_provider,
            reason="mock_provider",
            message="Mock provider does not make external AI calls.",
            user_triggered=user_triggered,
        )

    if resolved_provider == "openai":
        if not settings.ai_allow_external_calls:
            return _result(
                allowed=False,
                action=resolved_action,
                provider=resolved_provider,
                reason="external_ai_disabled",
                message="External AI calls are disabled. Set AI_ALLOW_EXTERNAL_CALLS=true and explicitly trigger an allowed AI action.",
                user_triggered=user_triggered,
                model=settings.openai_model,
            )
        if not settings.openai_api_key:
            return _result(
                allowed=False,
                action=resolved_action,
                provider=resolved_provider,
                reason="openai_api_key_missing",
                message="OpenAI is not configured. Set OPENAI_API_KEY after enabling AI_ALLOW_EXTERNAL_CALLS=true.",
                user_triggered=user_triggered,
                model=settings.openai_model,
            )
        return _result(
            allowed=True,
            action=resolved_action,
            provider=resolved_provider,
            reason="allowed",
            message="OpenAI call allowed for this explicit assistive action.",
            user_triggered=user_triggered,
            model=settings.openai_model,
        )

    if resolved_provider == "gemini":
        if not settings.ai_allow_external_calls:
            return _result(
                allowed=False,
                action=resolved_action,
                provider=resolved_provider,
                reason="external_ai_disabled",
                message="External AI calls are disabled. Set AI_ALLOW_EXTERNAL_CALLS=true and explicitly trigger an allowed AI action.",
                user_triggered=user_triggered,
                model=settings.gemini_model,
            )
        if not settings.gemini_api_key:
            return _result(
                allowed=False,
                action=resolved_action,
                provider=resolved_provider,
                reason="gemini_api_key_missing",
                message="Gemini is not configured. Set GEMINI_API_KEY after enabling AI_ALLOW_EXTERNAL_CALLS=true.",
                user_triggered=user_triggered,
                model=settings.gemini_model,
            )
        return _result(
            allowed=True,
            action=resolved_action,
            provider=resolved_provider,
            reason="allowed",
            message="Gemini call allowed for this explicit assistive action.",
            user_triggered=user_triggered,
            model=settings.gemini_model,
        )

    return _result(
        allowed=False,
        action=resolved_action,
        provider=resolved_provider,
        reason="provider_not_allowed",
        message=f"Provider '{resolved_provider}' is not allowed for external API calls.",
        user_triggered=user_triggered,
    )


def is_external_api_allowed(
    action: str,
    provider: str | None = None,
    user_enabled: bool = False,
    user_triggered: bool = False,
) -> bool:
    del provider
    return is_ai_allowed(action, user_enabled=user_enabled, user_triggered=user_triggered)


def require_external_api_allowed(
    action: str,
    provider: str | None = None,
    user_enabled: bool = False,
    user_triggered: bool = False,
) -> dict[str, Any]:
    del provider
    return require_ai_allowed(action, user_enabled=user_enabled, user_triggered=user_triggered)


def external_api_status() -> dict[str, Any]:
    provider = selected_ai_provider()
    both_keys_configured = bool(settings.openai_api_key and settings.gemini_api_key)
    return {
        "ai_allow_external_calls": settings.ai_allow_external_calls,
        "active_ai_provider": provider,
        "openai_configured": bool(settings.openai_api_key),
        "gemini_configured": bool(settings.gemini_api_key),
        "both_provider_keys_configured": both_keys_configured,
        "openai_model": settings.openai_model,
        "gemini_model": settings.gemini_model,
        "current_model": selected_ai_model(provider) or "mock",
        "allowed_ai_actions": sorted(ALLOWED_AI_ACTIONS),
        "recent_api_usage": list(reversed(RECENT_API_POLICY_EVENTS[-10:])),
    }
