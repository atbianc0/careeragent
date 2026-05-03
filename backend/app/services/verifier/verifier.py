from __future__ import annotations

from datetime import date, datetime, timezone
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.models.job import Job
from app.services.jobs.job_store import calculate_freshness_score, calculate_placeholder_priority_score
from app.utils.text import normalize_whitespace

DEFAULT_HEADERS = {
    "User-Agent": (
        "CareerAgent/0.4 Stage4 Job Verifier "
        "(safe rule-based verification; no browser automation)"
    )
}
FETCH_TIMEOUT_SECONDS = 10
APPLY_PHRASES = [
    "apply",
    "apply now",
    "apply for this job",
    "apply for this position",
    "submit application",
    "start application",
    "join our team",
    "easy apply",
    "continue application",
    "begin application",
]
CLOSED_PHRASES = [
    "no longer accepting applications",
    "this job is no longer available",
    "job is closed",
    "position has been filled",
    "posting has expired",
    "applications are closed",
    "this position is no longer available",
    "this role is no longer available",
    "no longer available",
    "job expired",
    "requisition closed",
    "vacancy closed",
    "we are not accepting applications",
    "this opening is closed",
    "page not found",
]
BLOCKED_PHRASES = [
    "access denied",
    "forbidden",
    "captcha",
    "cloudflare",
    "bot detection",
    "not authorized",
]
GENERIC_REDIRECT_SEGMENTS = {
    "",
    "careers",
    "career",
    "jobs",
    "job-search",
    "open-positions",
    "positions",
}
STRONG_CLOSED_MARKERS = {"http 404", "http 410"} | set(CLOSED_PHRASES)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().isoformat()


def _clean_text(text: str) -> str:
    return normalize_whitespace(text.replace("\xa0", " "))


def _get_visible_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return "\n".join(line for line in (_clean_text(part) for part in soup.get_text("\n", strip=True).splitlines()) if line)


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        lowered = normalized.lower()
        if not normalized or lowered in seen:
            continue
        seen.add(lowered)
        result.append(normalized)
    return result


def _days_since(reference_date: date | None) -> int | None:
    if reference_date is None:
        return None
    return max((date.today() - reference_date).days, 0)


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"


def _looks_like_blocked_page(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in BLOCKED_PHRASES)


def _extract_text_candidates(soup: BeautifulSoup | None) -> list[str]:
    if soup is None:
        return []
    candidates: list[str] = []
    for element in soup.find_all(["a", "button", "input"]):
        parts = [
            element.get_text(" ", strip=True),
            element.get("value", ""),
            element.get("aria-label", ""),
            element.get("title", ""),
        ]
        combined = _clean_text(" ".join(part for part in parts if part))
        if combined:
            candidates.append(combined)
    return candidates


def _is_suspicious_redirect(original_url: str, final_url: str) -> bool:
    original = urlparse(original_url)
    final = urlparse(final_url)
    if original.netloc.lower() != final.netloc.lower():
        return False

    original_segments = [segment for segment in original.path.lower().split("/") if segment]
    final_segments = [segment for segment in final.path.lower().split("/") if segment]
    if not final_segments:
        return True
    if len(final_segments) <= 1 and "/".join(final_segments) in GENERIC_REDIRECT_SEGMENTS:
        return True

    original_tail = next(
        (segment for segment in reversed(original_segments) if segment not in GENERIC_REDIRECT_SEGMENTS),
        "",
    )
    final_path = "/".join(final_segments)
    return bool(original_tail and original_tail not in final_path)


def _has_strong_closed_signal(closed_signals: list[str]) -> bool:
    lowered_signals = [signal.lower() for signal in closed_signals]
    return any(
        marker in signal
        for signal in lowered_signals
        for marker in STRONG_CLOSED_MARKERS
    )


def _has_request_failure(closed_signals: list[str]) -> bool:
    lowered_signals = [signal.lower() for signal in closed_signals]
    failure_markers = [
        "request failed",
        "request timed out",
        "access blocked",
        "forbidden",
        "server error",
        "could not verify",
    ]
    return any(marker in signal for signal in lowered_signals for marker in failure_markers)


def detect_apply_signals(text: str, soup: BeautifulSoup | None = None) -> list[str]:
    signals: list[str] = []
    lowered_text = text.lower()
    for phrase in APPLY_PHRASES:
        if phrase in lowered_text:
            signals.append(phrase.title())

    for candidate in _extract_text_candidates(soup):
        lowered_candidate = candidate.lower()
        if any(phrase in lowered_candidate for phrase in APPLY_PHRASES):
            signals.append(candidate[:120])

    return _unique(signals)


def detect_closed_signals(
    text: str,
    status_code: int | None = None,
    final_url: str | None = None,
    original_url: str | None = None,
) -> list[str]:
    signals: list[str] = []
    lowered_text = text.lower()

    if status_code in {404, 410}:
        signals.append(f"HTTP {status_code}")
    elif status_code == 403:
        signals.append("Access blocked or forbidden (HTTP 403)")
    elif status_code is not None and status_code >= 500:
        signals.append(f"Server error (HTTP {status_code})")

    for phrase in CLOSED_PHRASES:
        if phrase in lowered_text:
            signals.append(phrase)

    if _looks_like_blocked_page(text):
        signals.append("Access blocked or anti-bot page detected")

    if original_url and final_url and _normalize_url(original_url) != _normalize_url(final_url):
        if _is_suspicious_redirect(original_url, final_url):
            signals.append("Redirect appears generic; job may be closed")

    return _unique(signals)


def calculate_verification_scores(
    page_loaded: bool,
    apply_signals: list[str],
    closed_signals: list[str],
    days_since_posted: int | None,
    days_since_first_seen: int | None,
    redirected: bool,
) -> dict:
    verification_score = 50
    likely_closed_score = 0
    strong_closed_signal = _has_strong_closed_signal(closed_signals)
    request_failed = _has_request_failure(closed_signals)
    http_gone = any(signal.lower() in {"http 404", "http 410"} for signal in closed_signals)

    age_days = days_since_posted if days_since_posted is not None else days_since_first_seen

    if page_loaded:
        verification_score += 25
    if apply_signals:
        verification_score += 25
    else:
        verification_score -= 20
        likely_closed_score += 25

    if not strong_closed_signal:
        verification_score += 15
    if age_days is not None and age_days <= 30:
        verification_score += 10
    if not redirected:
        verification_score += 5
    else:
        verification_score -= 15
        likely_closed_score += 20

    if http_gone:
        verification_score -= 50
        likely_closed_score += 50
    if strong_closed_signal:
        verification_score -= 35
        likely_closed_score += 40
    if request_failed:
        verification_score -= 25
        likely_closed_score += 20

    if age_days is not None:
        if age_days > 90:
            verification_score -= 20
            likely_closed_score += 25
        elif age_days > 60:
            verification_score -= 10
            likely_closed_score += 15

    return {
        "verification_score": max(0, min(100, round(verification_score))),
        "likely_closed_score": max(0, min(100, round(likely_closed_score))),
    }


def infer_verification_status(
    verification_score: int,
    likely_closed_score: int,
    closed_signals: list[str],
) -> str:
    if _has_strong_closed_signal(closed_signals):
        return "closed"
    if _has_request_failure(closed_signals):
        return "unknown"
    if verification_score >= 80 and likely_closed_score <= 20:
        return "open"
    if verification_score >= 60:
        return "probably_open"
    if likely_closed_score >= 75:
        return "likely_closed"
    if likely_closed_score >= 50:
        return "possibly_closed"
    return "unknown"


def _verify_job_url(
    url: str,
    *,
    first_seen_date: date | None = None,
    posted_date: date | None = None,
) -> dict:
    checked_at = _now_iso()
    if not url.strip():
        return {
            "verification_status": "unknown",
            "verification_score": 0,
            "likely_closed_score": 0,
            "evidence": ["No job URL is stored for this job."],
            "checked_at": checked_at,
            "http_status": None,
            "final_url": "",
            "redirected": False,
            "page_title": "",
            "days_since_posted": _days_since(posted_date),
            "days_since_first_seen": _days_since(first_seen_date),
            "apply_signals": [],
            "closed_signals": [],
            "page_loaded": False,
            "suspicious_redirect": False,
            "verification_raw_data": {},
            "last_verification_error": "No job URL is stored for this job.",
        }

    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        return {
            "verification_status": "unknown",
            "verification_score": 0,
            "likely_closed_score": 0,
            "evidence": ["The saved job URL is invalid and must start with http:// or https://."],
            "checked_at": checked_at,
            "http_status": None,
            "final_url": url,
            "redirected": False,
            "page_title": "",
            "days_since_posted": _days_since(posted_date),
            "days_since_first_seen": _days_since(first_seen_date),
            "apply_signals": [],
            "closed_signals": [],
            "page_loaded": False,
            "suspicious_redirect": False,
            "verification_raw_data": {},
            "last_verification_error": "Invalid URL format.",
        }

    evidence: list[str] = []
    apply_signals: list[str] = []
    closed_signals: list[str] = []
    page_title = ""
    final_url = url.strip()
    http_status: int | None = None
    page_loaded = False
    suspicious_redirect = False
    visible_text = ""
    low_text = False
    last_verification_error: str | None = None

    try:
        response = requests.get(
            url.strip(),
            headers=DEFAULT_HEADERS,
            timeout=FETCH_TIMEOUT_SECONDS,
            allow_redirects=True,
        )
        http_status = response.status_code
        final_url = response.url or url.strip()
        redirected = _normalize_url(final_url) != _normalize_url(url.strip())

        soup = BeautifulSoup(response.text, "html.parser")
        visible_text = _get_visible_text(soup)
        page_title = _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
        low_text = len(visible_text) < 200
        blocked_or_failed = response.status_code in {403, 500, 502, 503, 504} or _looks_like_blocked_page(visible_text)
        page_loaded = 200 <= response.status_code < 300 and not blocked_or_failed

        apply_signals = detect_apply_signals(visible_text, soup if page_loaded else None)
        closed_signals = detect_closed_signals(
            visible_text,
            status_code=http_status,
            final_url=final_url,
            original_url=url.strip(),
        )
        suspicious_redirect = redirected and _is_suspicious_redirect(url.strip(), final_url)

        if page_loaded:
            evidence.append("Job page loaded successfully")
        elif blocked_or_failed:
            evidence.append("Could not verify the job page because the request was blocked or failed.")
            last_verification_error = "The site blocked access or returned an error while verifying the job."
        else:
            evidence.append("Job page did not load successfully.")
            last_verification_error = "The job page did not load successfully."

        if redirected:
            evidence.append("Page redirected from original job URL")
            if suspicious_redirect:
                evidence.append("Redirect appears generic; job may be closed")
        else:
            evidence.append("Page did not redirect away from the original URL")

        for signal in apply_signals:
            evidence.append(f"Apply signal found: {signal}")
        if page_loaded and not apply_signals:
            evidence.append("No apply signals were found on the page")

        strong_closed_signal = False
        for signal in closed_signals:
            lowered_signal = signal.lower()
            if any(marker in lowered_signal for marker in STRONG_CLOSED_MARKERS):
                evidence.append(f"Closed signal found: {signal}")
                strong_closed_signal = True
            elif "redirect appears generic" in lowered_signal:
                # Redirect evidence is already added above.
                continue
            else:
                evidence.append(f"Verification warning: {signal}")

        if page_loaded and not strong_closed_signal:
            evidence.append("No closed-job phrases found")
        if low_text:
            evidence.append("Page exposed very little visible text; verification confidence is limited.")

    except requests.Timeout:
        last_verification_error = "Verification request timed out."
        closed_signals = ["Request timed out while loading the job page"]
        evidence.append("Could not verify the job page because the request timed out.")
        redirected = False
    except requests.RequestException as exc:
        last_verification_error = f"Verification request failed: {exc}"
        closed_signals = [f"Request failed: {exc}"]
        evidence.append("Could not verify the job page because the request failed.")
        redirected = False
    else:
        redirected = _normalize_url(final_url) != _normalize_url(url.strip())

    days_since_posted = _days_since(posted_date)
    days_since_first_seen = _days_since(first_seen_date)
    scores = calculate_verification_scores(
        page_loaded=page_loaded,
        apply_signals=apply_signals,
        closed_signals=closed_signals,
        days_since_posted=days_since_posted,
        days_since_first_seen=days_since_first_seen,
        redirected=suspicious_redirect,
    )
    verification_status = infer_verification_status(
        verification_score=scores["verification_score"],
        likely_closed_score=scores["likely_closed_score"],
        closed_signals=closed_signals,
    )

    return {
        "verification_status": verification_status,
        "verification_score": scores["verification_score"],
        "likely_closed_score": scores["likely_closed_score"],
        "evidence": _unique(evidence),
        "checked_at": checked_at,
        "http_status": http_status,
        "final_url": final_url,
        "redirected": _normalize_url(final_url) != _normalize_url(url.strip()) if final_url else False,
        "page_title": page_title,
        "days_since_posted": days_since_posted,
        "days_since_first_seen": days_since_first_seen,
        "apply_signals": apply_signals,
        "closed_signals": closed_signals,
        "page_loaded": page_loaded,
        "suspicious_redirect": suspicious_redirect,
        "verification_raw_data": {
            "original_url": url.strip(),
            "http_status": http_status,
            "final_url": final_url,
            "page_title": page_title,
            "page_loaded": page_loaded,
            "apply_signals": apply_signals,
            "closed_signals": closed_signals,
            "redirected": _normalize_url(final_url) != _normalize_url(url.strip()) if final_url else False,
            "suspicious_redirect": suspicious_redirect,
            "days_since_posted": days_since_posted,
            "days_since_first_seen": days_since_first_seen,
            "checked_at": checked_at,
        },
        "last_verification_error": last_verification_error,
    }


def verify_job_url(url: str, first_seen_date=None, posted_date=None) -> dict:
    return _verify_job_url(url, first_seen_date=first_seen_date, posted_date=posted_date)


def verify_job_record(job: Job) -> dict:
    return _verify_job_url(
        job.url,
        first_seen_date=job.first_seen_date,
        posted_date=job.posted_date,
    )


def build_job_verification_updates(job: Job, verification_result: dict) -> dict:
    verification_status = verification_result["verification_status"]
    page_loaded = bool(verification_result.get("page_loaded"))
    freshness_score = calculate_freshness_score(job.posted_date, job.first_seen_date)
    overall_priority_score = calculate_placeholder_priority_score(
        resume_match_score=job.resume_match_score,
        verification_score=float(verification_result["verification_score"]),
        freshness_score=freshness_score,
        location_score=job.location_score,
        application_ease_score=job.application_ease_score,
    )

    updates = {
        "verification_status": verification_status,
        "verification_score": float(verification_result["verification_score"]),
        "likely_closed_score": float(verification_result["likely_closed_score"]),
        "verification_evidence": verification_result["evidence"],
        "verification_raw_data": verification_result["verification_raw_data"],
        "last_verification_error": verification_result.get("last_verification_error"),
        "last_checked_date": _now_utc().date(),
        "freshness_score": freshness_score,
        "overall_priority_score": overall_priority_score,
    }

    if page_loaded and verification_status not in {"closed", "likely_closed"}:
        updates["last_seen_date"] = _now_utc().date()

    if verification_status in {"closed", "likely_closed"} and job.closed_date is None:
        updates["closed_date"] = _now_utc().date()

    return updates
