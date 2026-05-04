from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    name = "base"

    def __init__(self) -> None:
        self.unavailable_reason: str | None = None

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate_text(self, task: str, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def parse_json(self, task: str, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def build_result(
        self,
        *,
        success: bool,
        task: str,
        content: str = "",
        parsed_json: dict[str, Any] | list[Any] | None = None,
        warnings: list[str] | None = None,
        safety_notes: list[str] | None = None,
        raw: Any = None,
    ) -> dict[str, Any]:
        return {
            "provider": self.name,
            "success": success,
            "task": task,
            "content": content,
            "parsed_json": parsed_json,
            "warnings": list(warnings or []),
            "safety_notes": list(safety_notes or []),
            "raw": raw,
        }
