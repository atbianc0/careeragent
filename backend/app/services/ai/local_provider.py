from __future__ import annotations

from typing import Any

from .base import AIProvider


class LocalLLMProvider(AIProvider):
    name = "local"

    def __init__(self) -> None:
        super().__init__()
        self.unavailable_reason = "LocalLLMProvider is a placeholder for a future local-model integration."

    def is_available(self) -> bool:
        return False

    def generate_text(self, task: str, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        del prompt, context
        return self.build_result(
            success=False,
            task=task,
            warnings=[self.unavailable_reason or "Local provider is unavailable."],
            safety_notes=["Use MockProvider or configure OpenAI instead."],
        )

    def parse_json(self, task: str, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        del prompt, context
        return self.build_result(
            success=False,
            task=task,
            warnings=[self.unavailable_reason or "Local provider is unavailable."],
            safety_notes=["Use MockProvider or configure OpenAI instead."],
        )
