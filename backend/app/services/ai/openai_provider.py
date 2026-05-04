from __future__ import annotations

import json
from typing import Any

from app.core.config import settings

from .base import AIProvider
from .safety import sanitize_ai_output

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - dependency can be absent locally
    OpenAI = None  # type: ignore[assignment]


def _extract_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    output = getattr(response, "output", None) or []
    chunks: list[str] = []
    for item in output:
        for content in getattr(item, "content", None) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(str(text))
    return "\n".join(chunk.strip() for chunk in chunks if str(chunk).strip()).strip()


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


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self) -> None:
        super().__init__()
        self.model = settings.openai_model
        if OpenAI is None:
            self.unavailable_reason = "The openai package is not installed in the current backend environment."
        elif not settings.openai_api_key:
            self.unavailable_reason = "OPENAI_API_KEY is not configured."

    def is_available(self) -> bool:
        return OpenAI is not None and bool(settings.openai_api_key)

    def _client(self) -> Any:
        if not self.is_available():
            raise RuntimeError(self.unavailable_reason or "OpenAIProvider is unavailable.")
        return OpenAI(api_key=settings.openai_api_key)

    def generate_text(self, task: str, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        del context
        if not self.is_available():
            return self.build_result(
                success=False,
                task=task,
                warnings=[self.unavailable_reason or "OpenAIProvider is unavailable."],
                safety_notes=["Falling back to deterministic generation is recommended."],
            )
        try:
            client = self._client()
            response = client.responses.create(
                model=self.model,
                input=prompt,
            )
            content = sanitize_ai_output(_extract_output_text(response))
            return self.build_result(
                success=True,
                task=task,
                content=content,
                warnings=[],
                safety_notes=["OpenAI output is a draft and must be reviewed manually."],
                raw={"model": self.model},
            )
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            return self.build_result(
                success=False,
                task=task,
                warnings=[f"OpenAI request failed: {exc}"],
                safety_notes=["Falling back to deterministic generation is recommended."],
            )

    def parse_json(self, task: str, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        del context
        structured_prompt = "\n\n".join(
            [
                prompt,
                "Return only valid JSON. Do not wrap the response in markdown code fences.",
            ]
        )
        text_result = self.generate_text(task, structured_prompt)
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
                warnings=[f"OpenAI returned text that could not be parsed as JSON: {exc}"],
                safety_notes=["Falling back to deterministic parsing is recommended."],
                raw=text_result.get("raw"),
            )
