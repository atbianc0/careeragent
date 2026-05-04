from __future__ import annotations

from collections import deque
from copy import deepcopy
from typing import Any

_RECENT_SESSION_SUMMARIES: deque[dict[str, Any]] = deque(maxlen=10)


def save_session_summary(summary: dict[str, Any]) -> None:
    _RECENT_SESSION_SUMMARIES.appendleft(deepcopy(summary))


def get_recent_session_summaries(limit: int = 5) -> list[dict[str, Any]]:
    return [deepcopy(item) for item in list(_RECENT_SESSION_SUMMARIES)[: max(limit, 0)]]
