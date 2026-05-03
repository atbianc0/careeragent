BLOCKED_FINAL_SUBMIT_WORDS = [
    "submit",
    "apply",
    "send application",
    "complete application",
    "finish",
    "confirm",
    "finalize",
]


def is_blocked_final_action(text: str) -> bool:
    normalized = text.strip().lower()
    return any(blocked in normalized for blocked in BLOCKED_FINAL_SUBMIT_WORDS)

