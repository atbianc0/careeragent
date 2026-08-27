"""Failure-state clarity for the AI-assisted apply path (POST /apply/start-ai-assisted).

Covers the gaps found while auditing this path: a provider that is
available/allowed but whose actual call fails must not be reported the same
way as a provider that was never configured, and an unexpected exception
during packet generation must not surface as a bare, detail-less 500.
"""

from __future__ import annotations

from typing import Any

from app.models.job import Job
import app.services.generator.packet_generator as packet_generator


def _make_job(db_session) -> Job:
    job = Job(
        company="Acme Corp",
        title="Backend Engineer",
        location="Remote",
        url="https://example.com/jobs/1",
        source="manual",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


class _FailingProvider:
    """Reports available/allowed but every generate_text call fails, like a
    real provider hitting a network error or invalid API key at call time."""

    name = "openai"

    def __init__(self) -> None:
        self.unavailable_reason: str | None = None

    def is_available(self) -> bool:
        return True

    def generate_text(self, task: str, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "provider": self.name,
            "success": False,
            "task": task,
            "content": "",
            "parsed_json": None,
            "warnings": [f"OpenAI request failed: connection timed out ({task})."],
            "safety_notes": [],
            "raw": {"api_used": False},
        }


def test_provider_call_failure_is_not_reported_as_disabled(client, db_session, monkeypatch):
    job = _make_job(db_session)
    monkeypatch.setattr(packet_generator, "get_ai_provider", lambda *a, **k: _FailingProvider())

    response = client.post(f"/api/jobs/{job.id}/apply/start-ai-assisted", json={"user_triggered": True})

    assert response.status_code == 200
    body = response.json()
    assert body["ai_used"] is False
    # The old message ("AI is disabled or unavailable...") falsely implies
    # nothing was attempted; the provider was available and was called.
    assert "disabled or unavailable" not in body["message"]
    assert "did not return usable output" in body["message"]
    assert any("request failed" in warning.lower() for warning in body["warnings"])


def test_unexpected_generation_error_returns_explicit_detail(client, db_session, monkeypatch):
    job = _make_job(db_session)

    def _boom(*args, **kwargs):
        raise RuntimeError("LaTeX toolchain is missing pdflatex")

    monkeypatch.setattr(
        "app.api.routes.jobs.generate_application_packet",
        lambda *a, **k: _boom(),
    )

    response = client.post(f"/api/jobs/{job.id}/apply/start-ai-assisted", json={"user_triggered": True})

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "AI-assisted apply failed while generating the application packet" in detail
    assert "LaTeX toolchain is missing pdflatex" in detail
