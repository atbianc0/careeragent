from __future__ import annotations

import re

BLOCKED_FINAL_SUBMIT_WORDS = [
    "submit",
    "apply",
    "apply now",
    "send application",
    "complete application",
    "finish",
    "confirm",
    "finalize",
    "submit application",
    "continue to submit",
    "send",
    "done",
]

SAFE_NAVIGATION_WORDS = {
    "next",
    "continue",
    "continue application",
    "save",
    "save draft",
    "review",
    "back",
    "cancel",
}


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())


def is_blocked_final_action(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False

    if any(blocked == normalized for blocked in BLOCKED_FINAL_SUBMIT_WORDS):
        return True

    for blocked in BLOCKED_FINAL_SUBMIT_WORDS:
        if blocked in normalized:
            if blocked == "apply" and "application" not in normalized and normalized not in {"apply", "apply now"}:
                continue
            return True
    return False


def should_block_element(element_text: str, element_type: str | None = None) -> bool:
    normalized_text = _normalize_text(element_text)
    normalized_type = _normalize_text(element_type)

    if is_blocked_final_action(normalized_text):
        return True

    if normalized_text in SAFE_NAVIGATION_WORDS:
        return False

    if normalized_type == "submit" and not normalized_text:
        return True

    if normalized_type == "submit" and any(token in normalized_text for token in ("application", "submit", "confirm", "finish")):
        return True

    if normalized_text.startswith("complete ") or normalized_text.startswith("submit "):
        return True

    if "final" in normalized_text and any(token in normalized_text for token in ("submit", "review", "step")):
        return True

    return False
