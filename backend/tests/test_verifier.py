"""Tests for the job verification service: page-load checks, apply-button
detection, closed-job phrase detection, and the likely_closed_score estimate.

`requests.get` is monkeypatched with a fake response object rather than a
network-mocking library, since the verifier calls it directly and no such
library is already a project dependency.
"""

from datetime import date, timedelta
from pathlib import Path

import pytest
import requests
from bs4 import BeautifulSoup

from app.services.verifier import verifier

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "verifier"


def _load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text()


class _FakeResponse:
    def __init__(self, *, status_code: int, text: str, url: str):
        self.status_code = status_code
        self.text = text
        self.url = url


def _patch_get(monkeypatch, *, response=None, exc=None):
    def fake_get(url, **kwargs):
        if exc is not None:
            raise exc
        return response

    monkeypatch.setattr(verifier.requests, "get", fake_get)


def _refuse_get(monkeypatch):
    def fake_get(*args, **kwargs):
        raise AssertionError("requests.get should not be called")

    monkeypatch.setattr(verifier.requests, "get", fake_get)


# --- apply-button detection --------------------------------------------------


def test_detect_apply_signals_matches_plain_text_phrase():
    signals = verifier.detect_apply_signals("Click here to apply now for this role.")

    assert any("Apply Now" in signal for signal in signals)


def test_detect_apply_signals_matches_button_and_aria_label():
    soup = BeautifulSoup(
        '<a href="/apply" aria-label="Submit Application">Go</a>', "html.parser"
    )

    signals = verifier.detect_apply_signals("", soup)

    assert any("Submit Application" in signal for signal in signals)


def test_detect_apply_signals_empty_when_no_match():
    assert verifier.detect_apply_signals("Welcome to our careers page.") == []


# --- closed-job phrase detection ---------------------------------------------


def test_detect_closed_signals_matches_phrase():
    signals = verifier.detect_closed_signals("Sorry, this position has been filled.")

    assert "position has been filled" in signals


def test_detect_closed_signals_http_404_and_410():
    assert verifier.detect_closed_signals("", status_code=404) == ["HTTP 404"]
    assert verifier.detect_closed_signals("", status_code=410) == ["HTTP 410"]


def test_detect_closed_signals_http_403_is_not_a_strong_closed_signal():
    signals = verifier.detect_closed_signals("", status_code=403)

    assert signals == ["Access blocked or forbidden (HTTP 403)"]
    assert not verifier._has_strong_closed_signal(signals)


def test_detect_closed_signals_flags_suspicious_generic_redirect():
    signals = verifier.detect_closed_signals(
        "",
        final_url="https://example.com/careers",
        original_url="https://example.com/careers/senior-engineer",
    )

    assert "Redirect appears generic; job may be closed" in signals


def test_detect_closed_signals_ignores_redirect_to_same_path():
    signals = verifier.detect_closed_signals(
        "",
        final_url="https://example.com/careers/senior-engineer/",
        original_url="https://example.com/careers/senior-engineer",
    )

    assert signals == []


# --- likely_closed_score estimate --------------------------------------------


def test_calculate_verification_scores_open_job_scores_low_closed_risk():
    scores = verifier.calculate_verification_scores(
        page_loaded=True,
        apply_signals=["Apply Now"],
        closed_signals=[],
        days_since_posted=5,
        days_since_first_seen=5,
        redirected=False,
    )

    assert scores["likely_closed_score"] <= 20
    status = verifier.infer_verification_status(
        scores["verification_score"], scores["likely_closed_score"], []
    )
    assert status in {"open", "probably_open"}


def test_calculate_verification_scores_http_gone_forces_closed():
    closed_signals = ["HTTP 404"]
    scores = verifier.calculate_verification_scores(
        page_loaded=False,
        apply_signals=[],
        closed_signals=closed_signals,
        days_since_posted=None,
        days_since_first_seen=None,
        redirected=False,
    )

    assert scores["likely_closed_score"] >= 75
    status = verifier.infer_verification_status(
        scores["verification_score"], scores["likely_closed_score"], closed_signals
    )
    assert status == "closed"


def test_calculate_verification_scores_stale_no_apply_signal_is_ambiguous():
    scores = verifier.calculate_verification_scores(
        page_loaded=True,
        apply_signals=[],
        closed_signals=[],
        days_since_posted=100,
        days_since_first_seen=100,
        redirected=False,
    )

    status = verifier.infer_verification_status(
        scores["verification_score"], scores["likely_closed_score"], []
    )
    assert status == "possibly_closed"


# --- page-load checks (end-to-end via verify_job_url) ------------------------


def test_verify_job_url_open_job(monkeypatch):
    html = _load_fixture("open_job.html")
    _patch_get(
        monkeypatch,
        response=_FakeResponse(status_code=200, text=html, url="https://example.com/jobs/1"),
    )

    result = verifier.verify_job_url("https://example.com/jobs/1")

    assert result["page_loaded"] is True
    assert result["apply_signals"]
    assert result["closed_signals"] == []
    assert result["verification_status"] in {"open", "probably_open"}
    assert result["likely_closed_score"] < 50


def test_verify_job_url_closed_job_soft_signal(monkeypatch):
    html = _load_fixture("closed_job.html")
    _patch_get(
        monkeypatch,
        response=_FakeResponse(status_code=200, text=html, url="https://example.com/jobs/2"),
    )

    result = verifier.verify_job_url("https://example.com/jobs/2")

    assert result["page_loaded"] is True
    assert result["apply_signals"] == []
    assert result["verification_status"] == "closed"
    assert result["likely_closed_score"] >= 50


def test_verify_job_url_hard_closed_http_404(monkeypatch):
    _patch_get(
        monkeypatch,
        response=_FakeResponse(
            status_code=404, text="<html><body>Not Found</body></html>", url="https://example.com/jobs/3"
        ),
    )

    result = verifier.verify_job_url("https://example.com/jobs/3")

    assert result["http_status"] == 404
    assert result["page_loaded"] is False
    assert "HTTP 404" in result["closed_signals"]
    assert result["verification_status"] == "closed"


def test_verify_job_url_ambiguous_stale_posting_no_apply_signal(monkeypatch):
    html = _load_fixture("ambiguous_job.html")
    _patch_get(
        monkeypatch,
        response=_FakeResponse(status_code=200, text=html, url="https://example.com/jobs/4"),
    )
    posted_100_days_ago = date.today() - timedelta(days=100)

    result = verifier.verify_job_url("https://example.com/jobs/4", posted_date=posted_100_days_ago)

    assert result["page_loaded"] is True
    assert result["apply_signals"] == []
    assert result["closed_signals"] == []
    assert result["verification_status"] == "possibly_closed"


def test_verify_job_url_request_timeout_is_unknown(monkeypatch):
    _patch_get(monkeypatch, exc=requests.Timeout("timed out"))

    result = verifier.verify_job_url("https://example.com/jobs/5")

    assert result["page_loaded"] is False
    assert result["verification_status"] == "unknown"
    assert result["last_verification_error"] == "Verification request timed out."


def test_verify_job_url_request_exception_is_unknown(monkeypatch):
    _patch_get(monkeypatch, exc=requests.ConnectionError("boom"))

    result = verifier.verify_job_url("https://example.com/jobs/6")

    assert result["page_loaded"] is False
    assert result["verification_status"] == "unknown"
    assert "request failed" in result["last_verification_error"].lower()


def test_verify_job_url_blank_url_returns_unknown_without_request(monkeypatch):
    _refuse_get(monkeypatch)

    result = verifier.verify_job_url("   ")

    assert result["verification_status"] == "unknown"
    assert result["evidence"] == ["No job URL is stored for this job."]


def test_verify_job_url_invalid_scheme_returns_unknown_without_request(monkeypatch):
    _refuse_get(monkeypatch)

    result = verifier.verify_job_url("ftp://example.com/jobs/7")

    assert result["verification_status"] == "unknown"
    assert result["last_verification_error"] == "Invalid URL format."
