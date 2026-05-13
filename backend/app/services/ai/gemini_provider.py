from __future__ import annotations

import json
from typing import Any

import requests

from app.core.config import settings

from .base import AIProvider
from .policy import normalize_api_action, require_ai_allowed
from .safety import sanitize_ai_output

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _extract_text(response_json: dict[str, Any]) -> str:
    chunks: list[str] = []
    for candidate in response_json.get("candidates") or []:
        content = candidate.get("content") if isinstance(candidate, dict) else {}
        for part in (content or {}).get("parts") or []:
            text = part.get("text") if isinstance(part, dict) else None
            if text:
                chunks.append(str(text))
    return "\n".join(chunk.strip() for chunk in chunks if chunk.strip()).strip()


def _extract_error(response_json: dict[str, Any]) -> str:
    error = response_json.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        status = error.get("status")
        if message and status:
            return f"{status}: {message}"
        if message:
            return str(message)
    return ""


def _extract_json_payload(text: str) -> str:
    cleaned = sanitize_ai_output(text)
    if cleaned.startswith("{") or cleaned.startswith("["):
        return cleaned
    object_start = cleaned.find("{")
    object_end = cleaned.rfind("}")
    if object_start != -1 and object_end != -1 and object_end > object_start:
        return cleaned[object_start : object_end + 1]
    list_start = cleaned.find("[")
    list_end = cleaned.rfind("]")
    if list_start != -1 and list_end != -1 and list_end > list_start:
        return cleaned[list_start : list_end + 1]
    return cleaned


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self) -> None:
        super().__init__()
        self.model = settings.gemini_model
        if settings.ai_provider != "gemini":
            self.unavailable_reason = "Gemini is not the selected AI_PROVIDER."
        elif not settings.ai_allow_external_calls:
            self.unavailable_reason = "External Gemini calls are disabled by AI_ALLOW_EXTERNAL_CALLS=false."
        elif not settings.gemini_api_key:
            self.unavailable_reason = "GEMINI_API_KEY is not configured."

    def is_available(self) -> bool:
        return settings.ai_provider == "gemini" and settings.ai_allow_external_calls and bool(settings.gemini_api_key)

    def generate_text(self, task: str, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = dict(context or {})
        action = normalize_api_action(str(context.get("api_action") or task))
        if settings.ai_provider != "gemini":
            return self.build_result(
                success=False,
                task=task,
                warnings=["Gemini was not called because AI_PROVIDER is not set to gemini."],
                safety_notes=["Only the selected AI_PROVIDER may be used."],
                raw={"api_used": False, "blocked_reason": "provider_not_selected", "api_action": action, "provider": "gemini"},
            )
        guard = require_ai_allowed(
            action=action,
            user_enabled=bool(context.get("user_enabled", False)),
            user_triggered=bool(context.get("user_triggered", False)),
        )
        if not guard.get("allowed"):
            return self.build_result(
                success=False,
                task=task,
                warnings=[str(guard.get("message") or "External Gemini call blocked by policy.")],
                safety_notes=["No external Gemini request was made."],
                raw={"api_used": False, "blocked_reason": guard.get("reason"), "api_action": action, "provider": "gemini"},
            )
        if not self.is_available():
            return self.build_result(
                success=False,
                task=task,
                warnings=[self.unavailable_reason or "GeminiProvider is unavailable."],
                safety_notes=["Falling back to deterministic generation is recommended."],
                raw={"api_used": False, "blocked_reason": "provider_unavailable", "api_action": action, "provider": "gemini"},
            )

        try:
            max_output_tokens = int(context.get("max_output_tokens") or 800)
            response = requests.post(
                f"{GEMINI_API_BASE}/{self.model}:generateContent",
                params={"key": settings.gemini_api_key},
                json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": max(16, min(max_output_tokens, 4000)),
                        "temperature": 0.4,
                    },
                },
                timeout=30,
            )
            response_json = response.json()
            if not response.ok:
                error_text = _extract_error(response_json) or response.text
                raise RuntimeError(error_text)
            content = sanitize_ai_output(_extract_text(response_json))
            if not content:
                raise RuntimeError("Gemini returned an empty response.")
            return self.build_result(
                success=True,
                task=task,
                content=content,
                warnings=[],
                safety_notes=["Gemini output is a draft and must be reviewed manually."],
                raw={
                    "api_used": True,
                    "provider": "gemini",
                    "api_action": action,
                    "model": self.model,
                    "user_triggered": True,
                    "max_output_tokens": max(16, min(max_output_tokens, 4000)),
                },
            )
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            return self.build_result(
                success=False,
                task=task,
                warnings=[f"Gemini request failed: {exc}"],
                safety_notes=["Falling back to deterministic generation is recommended."],
                raw={
                    "api_used": False,
                    "blocked_reason": "gemini_request_failed",
                    "api_action": action,
                    "provider": "gemini",
                    "model": self.model,
                },
            )

    def parse_json(self, task: str, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = dict(context or {})
        structured_prompt = "\n\n".join(
            [
                prompt,
                "Return only valid JSON. Do not wrap the response in markdown code fences.",
            ]
        )
        text_result = self.generate_text(task, structured_prompt, context=context)
        if not text_result.get("success"):
            return text_result

        raw_text = str(text_result.get("content") or "")
        try:
            parsed_json = json.loads(_extract_json_payload(raw_text))
            return self.build_result(
                success=True,
                task=task,
                content=raw_text,
                parsed_json=parsed_json,
                warnings=list(text_result.get("warnings") or []),
                safety_notes=list(text_result.get("safety_notes") or []),
                raw=text_result.get("raw"),
            )
        except Exception as exc:
            return self.build_result(
                success=False,
                task=task,
                content=raw_text,
                warnings=[f"Gemini returned text that could not be parsed as JSON: {exc}"],
                safety_notes=["Falling back to deterministic parsing is recommended."],
                raw=text_result.get("raw"),
            )
