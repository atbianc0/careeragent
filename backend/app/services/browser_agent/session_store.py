from __future__ import annotations

from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

_RECENT_SESSION_SUMMARIES: deque[dict[str, Any]] = deque(maxlen=10)
_ACTIVE_SESSIONS: dict[str, dict[str, Any]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def save_session_summary(summary: dict[str, Any]) -> None:
    _RECENT_SESSION_SUMMARIES.appendleft(deepcopy(summary))


def get_recent_session_summaries(limit: int = 5) -> list[dict[str, Any]]:
    return [deepcopy(item) for item in list(_RECENT_SESSION_SUMMARIES)[: max(limit, 0)]]


def create_session(
    *,
    browser: Any,
    context: Any,
    page: Any,
    job_id: int,
    opened_url: str,
    mode: str = "visible_review",
    playwright_manager: Any | None = None,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    session_id = str(uuid4())
    created = created_at or _now()
    _ACTIVE_SESSIONS[session_id] = {
        "session_id": session_id,
        "job_id": job_id,
        "opened_url": opened_url,
        "mode": mode,
        "created_at": created,
        "browser": browser,
        "context": context,
        "page": page,
        "playwright_manager": playwright_manager,
    }
    return session_public_summary(_ACTIVE_SESSIONS[session_id])


def session_public_summary(session: dict[str, Any]) -> dict[str, Any]:
    created_at = session.get("created_at")
    return {
        "session_id": str(session.get("session_id") or ""),
        "job_id": int(session.get("job_id") or 0),
        "opened_url": str(session.get("opened_url") or ""),
        "mode": str(session.get("mode") or "visible_review"),
        "created_at": _iso(created_at) if isinstance(created_at, datetime) else str(created_at or ""),
    }


def get_session(session_id: str) -> dict[str, Any] | None:
    return _ACTIVE_SESSIONS.get(session_id)


def _session_is_closed(session: dict[str, Any]) -> bool:
    page = session.get("page")
    if page is not None:
        try:
            if page.is_closed():
                return True
        except Exception:
            return True

    browser = session.get("browser")
    if browser is not None:
        try:
            if hasattr(browser, "is_connected") and not browser.is_connected():
                return True
        except Exception:
            return True

    return False


def list_sessions() -> list[dict[str, Any]]:
    cleanup_closed_sessions()
    return [session_public_summary(session) for session in _ACTIVE_SESSIONS.values()]


def close_session(session_id: str) -> dict[str, Any]:
    session = _ACTIVE_SESSIONS.pop(session_id, None)
    if session is None:
        return {
            "session_id": session_id,
            "job_id": 0,
            "opened_url": "",
            "mode": "visible_review",
            "created_at": "",
            "closed": True,
            "already_closed": True,
            "warning": "Autofill session was already closed or no longer active.",
            "errors": [],
        }

    errors: list[str] = []
    for key in ("context", "browser"):
        resource = session.get(key)
        if resource is None:
            continue
        try:
            resource.close()
        except Exception as exc:  # pragma: no cover - defensive cleanup
            errors.append(f"{key}: {exc}")

    manager = session.get("playwright_manager")
    if manager is not None:
        try:
            if hasattr(manager, "stop"):
                manager.stop()
            elif hasattr(manager, "__exit__"):
                manager.__exit__(None, None, None)
        except Exception as exc:  # pragma: no cover - defensive cleanup
            errors.append(f"playwright_manager: {exc}")

    summary = session_public_summary(session)
    summary["closed"] = True
    summary["errors"] = errors
    return summary


def cleanup_closed_sessions() -> list[dict[str, Any]]:
    closed_ids = [
        session_id
        for session_id, session in _ACTIVE_SESSIONS.items()
        if _session_is_closed(session)
    ]
    closed: list[dict[str, Any]] = []
    for session_id in closed_ids:
        closed.append(close_session(session_id))
    return closed


def cleanup_expired_sessions(max_age_seconds: int) -> list[dict[str, Any]]:
    if max_age_seconds <= 0:
        return []

    cutoff = _now().timestamp() - max_age_seconds
    expired_ids = [
        session_id
        for session_id, session in _ACTIVE_SESSIONS.items()
        if isinstance(session.get("created_at"), datetime) and session["created_at"].timestamp() < cutoff
    ]
    closed: list[dict[str, Any]] = []
    for session_id in expired_ids:
        closed.append(close_session(session_id))
    return closed
