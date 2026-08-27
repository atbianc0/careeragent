"""Failure-state clarity for the Playwright autofill path (fill-application /
start-autofill).

Covers two gaps found while auditing this path:

1. An unclassified Playwright error or an unexpected internal exception
   during a live session used to be raised as AutofillError/
   AutofillUnavailableError, which the API routes turned into a bare
   HTTPException(detail=str(exc)). That drops the status/warnings/
   recommended_next_action contract every other failure case returns, so the
   frontend fell back to a flat error banner instead of its normal
   per-status UI. It must now come back as a structured summary with an
   explicit status distinct from playwright_chromium_missing.
2. A visible or headless session whose browser dies mid-fill used to keep
   looping over the remaining fields, recording each as a generic
   "Browser interaction failed" skip, and could end up reporting
   "no_fields_filled" (or worse, a phantom successful session) instead of
   the accurate browser_closed status.
"""

from __future__ import annotations

import app.services.browser_agent.autofill as autofill_module
from app.models.job import Job


def _make_job(db_session) -> Job:
    job = Job(
        company="Acme Corp",
        title="Backend Engineer",
        location="Remote",
        url="https://example.com/jobs/1/apply",
        source="manual",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


class _FakePlaywrightError(Exception):
    pass


class _FakePlaywrightTimeoutError(Exception):
    pass


class _FakeResponse:
    status = 200


class _FakePage:
    url = "https://example.com/jobs/1/apply"

    def goto(self, *args, **kwargs):
        return _FakeResponse()

    def locator(self, *args, **kwargs):
        return self

    def inner_text(self, *args, **kwargs):
        return ""

    def evaluate(self, *args, **kwargs):
        return []

    def screenshot(self, *args, **kwargs):
        return None

    def wait_for_timeout(self, *args, **kwargs):
        return None

    @property
    def frames(self):
        return []

    @property
    def main_frame(self):
        return self


class _FakeContext:
    def new_page(self):
        return _FakePage()

    def close(self):
        return None


class _FakeBrowser:
    def new_context(self):
        return _FakeContext()

    def close(self):
        return None


class _FakeChromium:
    def launch(self, **kwargs):
        return _FakeBrowser()


class _FakePlaywright:
    def __init__(self):
        self.chromium = _FakeChromium()


class _FakeSyncPlaywrightManager:
    def __init__(self):
        self._playwright = _FakePlaywright()

    def start(self):
        return self._playwright

    def stop(self):
        return None

    def __enter__(self):
        return self._playwright

    def __exit__(self, exc_type, exc, tb):
        return False


def _patch_playwright_launch(monkeypatch):
    monkeypatch.setattr(autofill_module, "_get_playwright_support_status", lambda: {"playwright_installed": True})
    monkeypatch.setattr(
        autofill_module,
        "_load_playwright",
        lambda: (_FakeSyncPlaywrightManager, _FakePlaywrightError, _FakePlaywrightTimeoutError),
    )
    monkeypatch.setattr(autofill_module, "detect_form_fields", lambda page: [])


def test_unclassified_exception_during_headless_session_returns_structured_status(db_session, monkeypatch):
    job = _make_job(db_session)
    _patch_playwright_launch(monkeypatch)

    def _boom(*args, **kwargs):
        raise RuntimeError("unexpected tracker failure")

    monkeypatch.setattr(autofill_module, "log_event", _boom)

    summary = autofill_module.start_autofill_session(db_session, job.id, options={"mode": "headless_test"})

    assert summary["success"] is False
    assert summary["status"] == "autofill_session_failed"
    assert summary["status"] != "playwright_chromium_missing"
    assert "unexpected tracker failure" in summary["details"]
    assert summary["manual_review_required"] is True
    assert summary["message"]


def test_unclassified_playwright_error_during_visible_session_returns_structured_status(db_session, monkeypatch):
    job = _make_job(db_session)
    _patch_playwright_launch(monkeypatch)
    monkeypatch.setattr(autofill_module.settings, "playwright_headless", False)
    monkeypatch.setattr(autofill_module.settings, "playwright_use_xvfb", False)

    def _boom(*args, **kwargs):
        raise _FakePlaywrightError("some odd condition the classifiers do not recognize")

    monkeypatch.setattr(autofill_module, "create_session", _boom)

    summary = autofill_module.start_autofill_session(db_session, job.id, options={"mode": "visible_review"})

    assert summary["success"] is False
    assert summary["status"] == "autofill_session_failed"
    assert summary["status"] != "browser_closed"
    assert "odd condition" in summary["details"]


def _sample_fields() -> list[dict]:
    return [
        {
            "field_key": "first_name",
            "label": "First Name",
            "question_text": "First Name",
            "selector": "#first_name",
            "confidence": 0.95,
            "safe_to_fill": True,
            "tag": "input",
            "input_type": "text",
        },
        {
            "field_key": "last_name",
            "label": "Last Name",
            "question_text": "Last Name",
            "selector": "#last_name",
            "confidence": 0.95,
            "safe_to_fill": True,
            "tag": "input",
            "input_type": "text",
        },
    ]


def test_fill_safe_fields_stops_and_reports_browser_closed(monkeypatch):
    values = {"first_name": "Ada", "last_name": "Lovelace"}

    def _closed(*args, **kwargs):
        raise _FakePlaywrightError("Target page, context or browser has been closed")

    monkeypatch.setattr(autofill_module, "_apply_value_to_field", _closed)

    field_results, fields_filled, fields_attempted, files_uploaded, browser_closed = autofill_module._fill_safe_fields(
        page=object(),
        fields_detected=_sample_fields(),
        values=values,
        job=Job(company="Acme", title="x", location="Remote", url="https://x", source="manual"),
        profile={},
        warnings=[],
        allow_sensitive_optional=False,
        ai_assisted_apply=False,
        user_triggered=True,
        headless=False,
        playwright_error_type=_FakePlaywrightError,
    )

    assert browser_closed is True
    assert fields_attempted == 1
    assert fields_filled == 0
    assert len(field_results) == 1
    assert "Browser session closed" in field_results[0]["reason"]


def test_fill_safe_fields_continues_after_non_browser_closed_error(monkeypatch):
    values = {"first_name": "Ada", "last_name": "Lovelace"}

    def _generic_fail(*args, **kwargs):
        raise _FakePlaywrightError("locator.fill: strict mode violation")

    monkeypatch.setattr(autofill_module, "_apply_value_to_field", _generic_fail)

    field_results, fields_filled, fields_attempted, files_uploaded, browser_closed = autofill_module._fill_safe_fields(
        page=object(),
        fields_detected=_sample_fields(),
        values=values,
        job=Job(company="Acme", title="x", location="Remote", url="https://x", source="manual"),
        profile={},
        warnings=[],
        allow_sensitive_optional=False,
        ai_assisted_apply=False,
        user_triggered=True,
        headless=False,
        playwright_error_type=_FakePlaywrightError,
    )

    assert browser_closed is False
    assert fields_attempted == 2
    assert len(field_results) == 2
