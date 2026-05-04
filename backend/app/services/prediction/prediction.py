from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timezone
from io import StringIO
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.models.job import Job

APPLIED_OR_LATER_STATUSES = {"applied_manual", "follow_up", "interview", "rejected", "offer"}
RESPONSE_STATUSES = {"interview", "rejected", "offer"}
NO_LONGER_APPLYING_STATUSES = {
    "applied_manual",
    "follow_up",
    "interview",
    "rejected",
    "offer",
    "withdrawn",
    "closed_before_apply",
}
PACKET_READY_OR_LATER_STATUSES = {
    "packet_ready",
    "application_opened",
    "autofill_started",
    "autofill_completed",
} | APPLIED_OR_LATER_STATUSES
CLOSED_VERIFICATION_STATUSES = {"closed", "likely_closed"}
UNSTABLE_VERIFICATION_STATUSES = {"possibly_closed", "likely_closed", "closed"}
MIN_MEANINGFUL_APPLIED_SAMPLE = 3
MIN_RESPONSE_HISTORY_SAMPLE = 5
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return _now().date()


def _clamp_score(value: float | int | None) -> float:
    if value is None:
        return 0.0
    return round(max(0.0, min(100.0, float(value))), 2)


def _clamp_confidence(value: float | int | None) -> float:
    if value is None:
        return 0.0
    return round(max(0.0, min(1.0, float(value))), 2)


def _round_number(value: float | int | None, digits: int = 2) -> float:
    if value is None:
        return 0.0
    return round(float(value), digits)


def _average(values: list[float]) -> float:
    return _round_number(sum(values) / len(values)) if values else 0.0


def _safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return _round_number((numerator / denominator) * 100)


def _normalize_group_name(value: Any, *, fallback: str = "Unknown") -> str:
    if value is None:
        return fallback
    normalized = str(value).strip()
    return normalized or fallback


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _days_since(value: Any) -> int | None:
    value_date = _as_date(value)
    if value_date is None:
        return None
    return max((_today() - value_date).days, 0)


def _confidence_label(confidence: float | int | None) -> str:
    confidence_value = float(confidence or 0.0)
    if confidence_value >= 0.7:
        return "high"
    if confidence_value >= 0.4:
        return "medium"
    return "low"


def _job_was_scored(job: Job) -> bool:
    return bool(job.scoring_status == "scored" or job.scored_at is not None)


def _job_was_verified(job: Job) -> bool:
    return bool(
        job.last_checked_date
        or job.verification_status != "unknown"
        or job.verification_evidence
        or job.verification_raw_data
        or job.last_verification_error
    )


def _job_has_packet(job: Job) -> bool:
    return bool(job.packet_generated_at is not None or job.application_status in PACKET_READY_OR_LATER_STATUSES)


def _job_has_application_opened(job: Job) -> bool:
    return bool(
        job.application_link_opened_at is not None
        or job.application_status in {"application_opened", "autofill_started", "autofill_completed"} | APPLIED_OR_LATER_STATUSES
    )


def _job_has_applied(job: Job) -> bool:
    return bool(job.applied_at is not None or job.application_status in APPLIED_OR_LATER_STATUSES)


def _job_is_interview(job: Job) -> bool:
    return bool(job.interview_at is not None or job.application_status == "interview")


def _job_is_rejected(job: Job) -> bool:
    return bool(job.rejected_at is not None or job.application_status == "rejected")


def _job_is_offer(job: Job) -> bool:
    return bool(job.offer_at is not None or job.application_status == "offer")


def _job_has_response(job: Job) -> bool:
    return bool(_job_is_interview(job) or _job_is_rejected(job) or _job_is_offer(job))


def _is_closed_for_apply(job: Job) -> bool:
    return bool(
        job.verification_status in CLOSED_VERIFICATION_STATUSES
        or job.application_status == "closed_before_apply"
        or float(job.likely_closed_score or 0.0) >= 85
    )


def _suggest_action(priority_score: float, close_risk: dict[str, Any], job: Job) -> str:
    status = job.application_status
    risk_label = str(close_risk.get("risk_label") or "unknown")
    close_action = str(close_risk.get("suggested_action") or "manual_review")

    if status in {"interview", "offer"}:
        return "track_outcome"
    if status in {"applied_manual", "follow_up", "rejected", "withdrawn"}:
        return "already_in_pipeline"
    if status == "closed_before_apply" or risk_label == "closed":
        return "mark_closed_before_apply"
    if risk_label == "high":
        return close_action if close_action != "manual_review" else "reverify"
    if risk_label == "unknown":
        return "reverify"
    if priority_score >= 75 and not _job_has_packet(job):
        return "generate_packet"
    if priority_score >= 70:
        return "apply_soon"
    if priority_score >= 50:
        return "review_next"
    return "deprioritize"


def _prediction_context(db: Session) -> dict[str, Any]:
    jobs = db.query(Job).all()
    source_quality = _estimate_group_quality(
        jobs,
        key_getter=lambda job: job.source,
        label_key="source",
        score_key="source_quality_score",
    )
    role_quality = _estimate_group_quality(
        jobs,
        key_getter=lambda job: job.role_category,
        label_key="role_category",
        score_key="role_quality_score",
    )
    company_quality = _estimate_group_quality(
        jobs,
        key_getter=lambda job: job.company,
        label_key="company",
        score_key="company_quality_score",
    )
    applied_jobs = [job for job in jobs if _job_has_applied(job)]
    response_jobs = [job for job in applied_jobs if _job_has_response(job)]

    return {
        "jobs": jobs,
        "source_quality": source_quality,
        "role_quality": role_quality,
        "company_quality": company_quality,
        "applied_count": len(applied_jobs),
        "response_count": len(response_jobs),
        "global_response_rate": _safe_rate(len(response_jobs), len(applied_jobs)),
    }


def _estimate_group_quality(
    jobs: list[Job],
    *,
    key_getter: Callable[[Job], Any],
    label_key: str,
    score_key: str,
) -> dict[str, Any]:
    grouped: dict[str, list[Job]] = defaultdict(list)
    for job in jobs:
        grouped[_normalize_group_name(key_getter(job))].append(job)

    rows: list[dict[str, Any]] = []
    for name, grouped_jobs in grouped.items():
        applied_jobs = [job for job in grouped_jobs if _job_has_applied(job)]
        response_jobs = [job for job in applied_jobs if _job_has_response(job)]
        interview_jobs = [job for job in applied_jobs if _job_is_interview(job)]
        offer_jobs = [job for job in applied_jobs if _job_is_offer(job)]
        rejected_jobs = [job for job in applied_jobs if _job_is_rejected(job)]
        scored_jobs = [job for job in grouped_jobs if _job_was_scored(job)]

        total_jobs = len(grouped_jobs)
        applied_count = len(applied_jobs)
        response_count = len(response_jobs)
        interview_count = len(interview_jobs)
        offer_count = len(offer_jobs)
        rejected_count = len(rejected_jobs)
        average_priority_score = _average([float(job.overall_priority_score or 0.0) for job in scored_jobs])
        average_resume_match_score = _average([float(job.resume_match_score or 0.0) for job in scored_jobs])
        response_rate = _safe_rate(response_count, applied_count)
        interview_rate = _safe_rate(interview_count, applied_count)
        offer_rate = _safe_rate(offer_count, applied_count)

        score_component_priority = average_priority_score if scored_jobs else 50.0
        score_component_match = average_resume_match_score if scored_jobs else 50.0
        outcome_component = (
            50.0
            if applied_count == 0
            else (
                0.55 * float(response_rate or 0.0)
                + 0.35 * float(interview_rate or 0.0)
                + 0.10 * float(offer_rate or 0.0)
            )
        )
        raw_quality = (
            0.35 * score_component_priority
            + 0.25 * score_component_match
            + 0.40 * outcome_component
        )
        reliability = min(applied_count / 5, 1.0) if applied_count else min(total_jobs / 10, 0.35)
        quality_score = _clamp_score((50.0 * (1 - reliability)) + (raw_quality * reliability))
        sample_size_warning = applied_count < MIN_MEANINGFUL_APPLIED_SAMPLE

        rows.append(
            {
                label_key: name,
                "name": name,
                "total_jobs": total_jobs,
                "applied_jobs": applied_count,
                "response_count": response_count,
                "interview_count": interview_count,
                "offer_count": offer_count,
                "rejected_count": rejected_count,
                "response_rate": response_rate,
                "interview_rate": interview_rate,
                "offer_rate": offer_rate,
                "average_priority_score": average_priority_score,
                "average_resume_match_score": average_resume_match_score,
                score_key: quality_score,
                "sample_size_warning": sample_size_warning,
                "evidence": [
                    f"{name} has {total_jobs} saved jobs and {applied_count} applied jobs in the current dataset.",
                    "Quality is shrunk toward neutral when applied-job history is small.",
                ],
            }
        )

    sorted_rows = sorted(
        rows,
        key=lambda row: (
            float(row.get(score_key) or 0.0),
            int(row.get("applied_jobs") or 0),
            int(row.get("total_jobs") or 0),
            str(row.get(label_key) or ""),
        ),
        reverse=True,
    )
    return {
        "minimum_meaningful_applied_jobs": MIN_MEANINGFUL_APPLIED_SAMPLE,
        "sample_size_warning": any(row["sample_size_warning"] for row in sorted_rows),
        "message": None if sorted_rows else "Import jobs before quality estimates become useful.",
        "rows": sorted_rows,
    }


def _lookup_quality_score(
    quality_table: dict[str, Any],
    *,
    value: Any,
    label_key: str,
    score_key: str,
) -> tuple[float, dict[str, Any] | None]:
    normalized = _normalize_group_name(value)
    for row in quality_table.get("rows") or []:
        if _normalize_group_name(row.get(label_key)) == normalized:
            return _clamp_score(row.get(score_key, 50.0)), row
    return 50.0, None


def _predict_close_risk(job: Job) -> dict[str, Any]:
    verification_status = _normalize_group_name(job.verification_status, fallback="unknown").lower()
    likely_closed_score = float(job.likely_closed_score or 0.0)
    days_since_first_seen = _days_since(job.first_seen_date)
    days_since_posted = _days_since(job.posted_date)
    days_since_last_checked = _days_since(job.last_checked_date)
    days_since_last_seen = _days_since(job.last_seen_date)
    raw_verification = dict(job.verification_raw_data or {})
    http_status = raw_verification.get("http_status")
    redirected = bool(raw_verification.get("redirected", False))

    evidence: list[str] = []

    if verification_status == "closed":
        score = 100.0
        evidence.append("Verification status is closed.")
    elif verification_status == "likely_closed":
        score = max(85.0, likely_closed_score)
        evidence.append("Verification status is likely_closed.")
    elif verification_status == "possibly_closed":
        score = max(62.0, likely_closed_score)
        evidence.append("Verification status is possibly_closed.")
    elif verification_status == "probably_open":
        score = 18.0 + (likely_closed_score * 0.15)
        evidence.append("Verification status is probably_open.")
    elif verification_status == "open":
        score = 12.0 + (likely_closed_score * 0.10)
        evidence.append("Verification status is open.")
    else:
        score = 42.0 + (likely_closed_score * 0.25)
        evidence.append("Verification status is unknown, so close-risk confidence is limited.")

    age_reference = days_since_posted if days_since_posted is not None else days_since_first_seen
    if age_reference is not None:
        evidence.append(f"Job age is about {age_reference} days based on posted or first-seen data.")
        if age_reference >= 120:
            score += 28
        elif age_reference >= 90:
            score += 22
        elif age_reference >= 60:
            score += 14
        elif age_reference >= 30:
            score += 7
        elif age_reference <= 10:
            score -= 6
    else:
        evidence.append("No posted or first-seen date is available.")

    if days_since_last_checked is None:
        score += 8
        evidence.append("The job has not been checked yet.")
    elif days_since_last_checked <= 7:
        score -= 8
        evidence.append("The job was checked within the last week.")
    elif days_since_last_checked >= 21:
        score += 10
        evidence.append(f"The last verification check is {days_since_last_checked} days old.")

    if days_since_last_seen is not None and days_since_last_seen >= 30:
        score += 6
        evidence.append(f"The posting has not been seen for {days_since_last_seen} days.")

    if not str(job.url or "").strip():
        score += 10
        evidence.append("No job URL is stored, so availability is harder to confirm.")

    if isinstance(http_status, int) and http_status >= 400:
        score += 25
        evidence.append(f"Last verification saw HTTP status {http_status}.")
    if redirected:
        score += 7
        evidence.append("Last verification observed a redirect, which can be a weak closure signal.")

    score = _clamp_score(score)
    if verification_status == "closed" or score >= 95:
        risk_label = "closed"
        suggested_action = "mark_closed_before_apply"
    elif score >= 75:
        risk_label = "high"
        suggested_action = "reverify" if verification_status not in CLOSED_VERIFICATION_STATUSES else "mark_closed_before_apply"
    elif score >= 40:
        risk_label = "medium"
        suggested_action = "reverify" if days_since_last_checked is None or (days_since_last_checked or 0) >= 14 else "apply_soon"
    elif verification_status == "unknown" and not _job_was_verified(job):
        risk_label = "unknown"
        suggested_action = "manual_review"
    else:
        risk_label = "low"
        suggested_action = "apply_soon"

    confidence = 0.25
    if _job_was_verified(job):
        confidence += 0.3
    if days_since_last_checked is not None and days_since_last_checked <= 14:
        confidence += 0.2
    if age_reference is not None:
        confidence += 0.1
    if verification_status in {"open", "probably_open", "possibly_closed", "likely_closed", "closed"}:
        confidence += 0.1
    if not str(job.url or "").strip():
        confidence -= 0.15
    confidence = _clamp_confidence(confidence)

    return {
        "predicted_close_risk_score": score,
        "risk_label": risk_label,
        "confidence": confidence,
        "confidence_label": _confidence_label(confidence),
        "evidence": evidence,
        "suggested_action": suggested_action,
        "days_since_first_seen": days_since_first_seen,
        "days_since_posted": days_since_posted,
        "days_since_last_checked": days_since_last_checked,
    }


def _predict_response_likelihood(job: Job, context: dict[str, Any]) -> dict[str, Any]:
    source_score, source_row = _lookup_quality_score(
        context["source_quality"],
        value=job.source,
        label_key="source",
        score_key="source_quality_score",
    )
    role_score, role_row = _lookup_quality_score(
        context["role_quality"],
        value=job.role_category,
        label_key="role_category",
        score_key="role_quality_score",
    )
    company_score, company_row = _lookup_quality_score(
        context["company_quality"],
        value=job.company,
        label_key="company",
        score_key="company_quality_score",
    )
    close_risk = _predict_close_risk(job)
    applied_count = int(context.get("applied_count") or 0)
    response_count = int(context.get("response_count") or 0)
    sample_warning = applied_count < MIN_RESPONSE_HISTORY_SAMPLE

    score = (
        0.32 * float(job.resume_match_score or 0.0)
        + 0.24 * float(job.overall_priority_score or 0.0)
        + 0.14 * float(job.verification_score or 0.0)
        + 0.12 * source_score
        + 0.12 * role_score
        + 0.06 * company_score
    )

    if _job_has_packet(job):
        score += 4
    if not str(job.url or "").strip():
        score -= 5
    if close_risk["risk_label"] in {"high", "closed"}:
        score -= 12
    elif close_risk["risk_label"] == "medium":
        score -= 5

    if applied_count >= MIN_RESPONSE_HISTORY_SAMPLE and context.get("global_response_rate") is not None:
        global_rate = float(context["global_response_rate"] or 0.0)
        score = 0.82 * score + 0.18 * global_rate

    score = _clamp_score(score)
    confidence = 0.2
    if _job_was_scored(job):
        confidence += 0.18
    if _job_was_verified(job):
        confidence += 0.12
    confidence += min(applied_count / 25, 0.28)
    if source_row and int(source_row.get("applied_jobs") or 0) >= MIN_MEANINGFUL_APPLIED_SAMPLE:
        confidence += 0.08
    if role_row and int(role_row.get("applied_jobs") or 0) >= MIN_MEANINGFUL_APPLIED_SAMPLE:
        confidence += 0.08
    if company_row and int(company_row.get("applied_jobs") or 0) >= MIN_MEANINGFUL_APPLIED_SAMPLE:
        confidence += 0.04
    if sample_warning:
        confidence = min(confidence, 0.45)
    confidence = _clamp_confidence(confidence)

    evidence = [
        "Response estimate blends match score, existing priority, verification, and historical source/role/company outcomes.",
        f"Current applied-job history has {applied_count} applied jobs and {response_count} recorded responses.",
        f"Source quality input: {source_score}/100. Role quality input: {role_score}/100.",
    ]
    if _job_has_packet(job):
        evidence.append("A packet appears ready, which slightly improves readiness.")
    if close_risk["risk_label"] in {"medium", "high", "closed"}:
        evidence.append(f"Close-risk label is {close_risk['risk_label']}, so response likelihood is discounted.")

    warning = (
        "Not enough applied-job history for reliable response estimates."
        if sample_warning
        else None
    )

    return {
        "predicted_response_score": score,
        "confidence": confidence,
        "confidence_label": _confidence_label(confidence),
        "evidence": evidence,
        "sample_size": applied_count,
        "response_count": response_count,
        "warning": warning,
        "source_quality_score": source_score,
        "role_quality_score": role_score,
        "company_quality_score": company_score,
    }


def _predict_job_priority(job: Job, context: dict[str, Any]) -> dict[str, Any]:
    source_score, source_row = _lookup_quality_score(
        context["source_quality"],
        value=job.source,
        label_key="source",
        score_key="source_quality_score",
    )
    role_score, role_row = _lookup_quality_score(
        context["role_quality"],
        value=job.role_category,
        label_key="role_category",
        score_key="role_quality_score",
    )
    response = _predict_response_likelihood(job, context)
    close_risk = _predict_close_risk(job)

    base_priority = float(job.overall_priority_score or 0.0)
    score = (
        0.50 * base_priority
        + 0.20 * source_score
        + 0.15 * role_score
        + 0.15 * float(response["predicted_response_score"])
    )
    evidence = [
        "Priority estimate blends existing Stage 5 priority, source quality, role quality, and response likelihood.",
        f"Base priority input: {round(base_priority, 2)}/100.",
        f"Source quality input: {source_score}/100. Role quality input: {role_score}/100.",
    ]
    warnings: list[str] = []

    if _is_closed_for_apply(job) or close_risk["risk_label"] == "closed":
        score = min(score, 5.0)
        evidence.append("Job appears closed or likely closed, so application priority is capped very low.")
    elif close_risk["risk_label"] == "high":
        score -= 28
        evidence.append("High close risk substantially lowers priority until the job is reverified.")
    elif close_risk["risk_label"] == "medium":
        score -= 10
        evidence.append("Medium close risk slightly lowers priority.")

    if job.application_status in NO_LONGER_APPLYING_STATUSES:
        score = min(score, 25.0)
        evidence.append(f"Application status is {job.application_status}, so this is not a fresh apply-first job.")

    age_reference = _days_since(job.posted_date) if job.posted_date else _days_since(job.first_seen_date)
    if age_reference is not None and age_reference >= 90:
        score -= 15
        evidence.append("Job is at least 90 days old, so priority is reduced.")
    elif age_reference is not None and age_reference >= 60:
        score -= 8
        evidence.append("Job is at least 60 days old, so priority is reduced slightly.")

    if not str(job.url or "").strip():
        score -= 5
        evidence.append("No URL is stored, so the application path needs manual review.")

    if not _job_has_packet(job) and job.application_status not in NO_LONGER_APPLYING_STATUSES:
        score -= 4
        evidence.append("No generated packet is recorded yet, so readiness is slightly lower.")

    if _job_has_application_opened(job) and job.application_status not in APPLIED_OR_LATER_STATUSES:
        score -= 3
        evidence.append("Application was opened but not marked applied, so CareerAgent suggests review before further action.")

    if not _job_was_scored(job):
        warnings.append("Score this job before treating the prediction as useful.")
    if response.get("warning"):
        warnings.append(str(response["warning"]))

    score = _clamp_score(score)

    applied_count = int(context.get("applied_count") or 0)
    confidence = 0.22
    if _job_was_scored(job):
        confidence += 0.22
    if _job_was_verified(job):
        confidence += 0.14
    if _job_has_packet(job):
        confidence += 0.06
    confidence += min(applied_count / 30, 0.18)
    if source_row and int(source_row.get("applied_jobs") or 0) >= MIN_MEANINGFUL_APPLIED_SAMPLE:
        confidence += 0.06
    if role_row and int(role_row.get("applied_jobs") or 0) >= MIN_MEANINGFUL_APPLIED_SAMPLE:
        confidence += 0.06
    if close_risk["confidence"] < 0.35:
        confidence -= 0.06
    confidence = _clamp_confidence(confidence)

    suggested_action = _suggest_action(score, close_risk, job)

    return {
        "predicted_priority_score": score,
        "score": score,
        "confidence": confidence,
        "confidence_label": _confidence_label(confidence),
        "evidence": evidence,
        "warnings": warnings,
        "suggested_action": suggested_action,
        "components": {
            "base_priority_score": _round_number(base_priority),
            "source_quality_score": source_score,
            "role_quality_score": role_score,
            "response_likelihood_score": response["predicted_response_score"],
            "close_risk_score": close_risk["predicted_close_risk_score"],
        },
    }


def _job_prediction_bundle(job: Job, context: dict[str, Any]) -> dict[str, Any]:
    close_risk = _predict_close_risk(job)
    response = _predict_response_likelihood(job, context)
    priority = _predict_job_priority(job, context)
    return {
        "priority": priority,
        "close_risk": close_risk,
        "response_likelihood": response,
    }


def _prediction_job_row(job: Job, context: dict[str, Any]) -> dict[str, Any]:
    bundle = _job_prediction_bundle(job, context)
    priority = bundle["priority"]
    close_risk = bundle["close_risk"]
    response = bundle["response_likelihood"]

    return {
        "job_id": job.id,
        "id": job.id,
        "company": job.company,
        "title": job.title,
        "location": job.location,
        "url": job.url,
        "source": _normalize_group_name(job.source, fallback="manual"),
        "role_category": _normalize_group_name(job.role_category, fallback="Other"),
        "application_status": job.application_status,
        "verification_status": job.verification_status,
        "overall_priority_score": _round_number(job.overall_priority_score),
        "resume_match_score": _round_number(job.resume_match_score),
        "packet_ready": _job_has_packet(job),
        "predicted_priority_score": priority["predicted_priority_score"],
        "predicted_close_risk_score": close_risk["predicted_close_risk_score"],
        "predicted_response_score": response["predicted_response_score"],
        "prediction_confidence": priority["confidence"],
        "prediction_confidence_label": priority["confidence_label"],
        "prediction_updated_at": job.prediction_updated_at.isoformat() if job.prediction_updated_at else None,
        "risk_label": close_risk["risk_label"],
        "suggested_action": priority["suggested_action"],
        "priority_prediction": priority,
        "close_risk_prediction": close_risk,
        "response_likelihood_prediction": response,
    }


def predict_job_priority(db: Session, job: Job) -> dict[str, Any]:
    return _predict_job_priority(job, _prediction_context(db))


def predict_close_risk(db: Session, job: Job) -> dict[str, Any]:
    return _predict_close_risk(job)


def predict_response_likelihood(db: Session, job: Job) -> dict[str, Any]:
    return _predict_response_likelihood(job, _prediction_context(db))


def estimate_source_quality(db: Session) -> dict[str, Any]:
    quality = _prediction_context(db)["source_quality"]
    return {
        "sources": quality["rows"],
        "minimum_meaningful_applied_jobs": quality["minimum_meaningful_applied_jobs"],
        "sample_size_warning": quality["sample_size_warning"],
        "message": quality["message"],
    }


def estimate_role_quality(db: Session) -> dict[str, Any]:
    quality = _prediction_context(db)["role_quality"]
    return {
        "roles": quality["rows"],
        "minimum_meaningful_applied_jobs": quality["minimum_meaningful_applied_jobs"],
        "sample_size_warning": quality["sample_size_warning"],
        "message": quality["message"],
    }


def _weekday_counts(values: list[Any]) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for value in values:
        value_date = _as_date(value)
        if value_date is None:
            continue
        counter[WEEKDAYS[value_date.weekday()]] += 1
    return [
        {"weekday": weekday, "count": counter.get(weekday, 0)}
        for weekday in WEEKDAYS
        if counter.get(weekday, 0) > 0
    ]


def _top_weekdays(rows: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (row["count"], row["weekday"]), reverse=True)[:limit]


def estimate_best_apply_windows(db: Session) -> dict[str, Any]:
    jobs = db.query(Job).all()
    import_days = _weekday_counts([job.created_at or job.first_seen_date for job in jobs])
    posted_or_seen_days = _weekday_counts([job.posted_date or job.first_seen_date for job in jobs])
    applied_jobs = [job for job in jobs if _job_has_applied(job)]
    application_days = _weekday_counts([job.applied_at for job in applied_jobs])
    response_application_days = _weekday_counts(
        [job.applied_at for job in applied_jobs if _job_has_response(job) and job.applied_at is not None]
    )

    observed_best_import_days = _top_weekdays(import_days)
    busiest_job_days = _top_weekdays(posted_or_seen_days)
    observed_best_application_days = _top_weekdays(response_application_days or application_days)

    warnings: list[str] = []
    recommended_focus_days: list[str]
    confidence_score = 0.2
    confidence_label = "low"
    based_on = "general_heuristic"

    if len(jobs) < 5:
        warnings.append("Not enough job history yet for reliable apply-window estimates.")
    else:
        confidence_score += 0.2
        based_on = "collected_import_history"

    if len(applied_jobs) < MIN_RESPONSE_HISTORY_SAMPLE:
        warnings.append("Track more applied jobs and outcomes before trusting application-day estimates.")
    else:
        confidence_score += 0.25
        based_on = "collected_application_history"

    response_count = sum(1 for job in applied_jobs if _job_has_response(job))
    if response_count >= MIN_MEANINGFUL_APPLIED_SAMPLE:
        confidence_score += 0.2
        based_on = "collected_response_history"

    if len(jobs) < 5 and len(applied_jobs) < MIN_RESPONSE_HISTORY_SAMPLE:
        recommended_focus_days = ["Monday", "Tuesday", "Wednesday", "Thursday"]
    elif observed_best_application_days:
        recommended_focus_days = [row["weekday"] for row in observed_best_application_days]
    elif observed_best_import_days:
        recommended_focus_days = [row["weekday"] for row in observed_best_import_days]
    else:
        recommended_focus_days = ["Monday", "Tuesday", "Wednesday", "Thursday"]

    confidence_score = _clamp_confidence(confidence_score)
    confidence_label = _confidence_label(confidence_score)

    default_guidance = [
        "Apply soon after strong jobs are found.",
        "Prioritize recent, verified-open, high-match jobs.",
        "Review jobs several times per week instead of waiting for one perfect day.",
    ]

    return {
        "observed_best_import_days": observed_best_import_days,
        "observed_best_application_days": observed_best_application_days,
        "busiest_job_days": busiest_job_days,
        "recommended_focus_days": recommended_focus_days,
        "confidence": confidence_label,
        "confidence_score": confidence_score,
        "based_on": based_on,
        "warning": " ".join(warnings) if warnings else None,
        "default_guidance": default_guidance if warnings else [],
        "sample_sizes": {
            "jobs": len(jobs),
            "applied_jobs": len(applied_jobs),
            "response_outcomes": response_count,
        },
    }


def estimate_apply_windows(db: Session) -> dict[str, Any]:
    return estimate_best_apply_windows(db)


def get_prediction_jobs(
    db: Session,
    *,
    include_closed: bool = False,
    min_confidence: float | None = None,
    role_category: str | None = None,
    source: str | None = None,
) -> list[dict[str, Any]]:
    context = _prediction_context(db)
    rows = [_prediction_job_row(job, context) for job in context["jobs"]]

    if not include_closed:
        rows = [
            row
            for row in rows
            if row["verification_status"] not in CLOSED_VERIFICATION_STATUSES
            and row["application_status"] != "closed_before_apply"
            and row["risk_label"] != "closed"
        ]
    if min_confidence is not None:
        rows = [row for row in rows if float(row["prediction_confidence"]) >= float(min_confidence)]
    if role_category:
        rows = [row for row in rows if row["role_category"] == role_category]
    if source:
        rows = [row for row in rows if row["source"] == source]

    return sorted(
        rows,
        key=lambda row: (
            float(row["predicted_priority_score"]),
            float(row["prediction_confidence"]),
            float(row["resume_match_score"]),
            row["company"],
            row["title"],
        ),
        reverse=True,
    )


def generate_prediction_insights(db: Session) -> list[dict[str, Any]]:
    context = _prediction_context(db)
    jobs = context["jobs"]
    if not jobs:
        return [
            {
                "title": "Import jobs before predicting",
                "detail": "Import and score jobs before predictions become useful.",
                "category": "getting_started",
                "confidence": "low",
            }
        ]

    rows = [_prediction_job_row(job, context) for job in jobs]
    insights: list[dict[str, Any]] = []
    unscored_count = sum(1 for job in jobs if not _job_was_scored(job))
    if unscored_count:
        insights.append(
            {
                "title": "Score more jobs",
                "detail": f"{unscored_count} jobs are not scored yet. Score them before relying on predictions.",
                "category": "scoring",
                "confidence": "high",
            }
        )

    high_priority_no_packet = [
        row for row in rows
        if row["predicted_priority_score"] >= 70 and not row["packet_ready"] and row["application_status"] not in NO_LONGER_APPLYING_STATUSES
    ]
    if high_priority_no_packet:
        insights.append(
            {
                "title": "High-priority jobs need packets",
                "detail": f"{len(high_priority_no_packet)} high-priority jobs do not have packets yet. Generate packets for these first.",
                "category": "packet_readiness",
                "confidence": "medium",
            }
        )

    high_close_risk = [row for row in rows if row["predicted_close_risk_score"] >= 70]
    if high_close_risk:
        insights.append(
            {
                "title": "Some jobs may close soon",
                "detail": f"{len(high_close_risk)} jobs have high close-risk. Reverify, apply soon, or mark closed before applying.",
                "category": "availability",
                "confidence": "medium",
            }
        )

    if int(context["applied_count"]) < MIN_RESPONSE_HISTORY_SAMPLE:
        insights.append(
            {
                "title": "Response predictions need more history",
                "detail": "Your data is too small for reliable response-rate predictions. Track more applied jobs and outcomes.",
                "category": "outcomes",
                "confidence": "high",
            }
        )

    source_rows = [row for row in context["source_quality"]["rows"] if row["total_jobs"] > 0]
    if source_rows:
        best_source = source_rows[0]
        caveat = " The sample size is small." if best_source["sample_size_warning"] else ""
        insights.append(
            {
                "title": "Observed strongest source",
                "detail": f"{best_source['source']} currently has the strongest source-quality score in your data.{caveat}",
                "category": "source_quality",
                "confidence": "low" if best_source["sample_size_warning"] else "medium",
            }
        )

    role_rows = [row for row in context["role_quality"]["rows"] if row["total_jobs"] > 0]
    if role_rows:
        best_role = role_rows[0]
        caveat = " The sample size is small." if best_role["sample_size_warning"] else ""
        insights.append(
            {
                "title": "Observed strongest role",
                "detail": f"{best_role['role_category']} roles currently have the strongest role-quality score in your data.{caveat}",
                "category": "role_quality",
                "confidence": "low" if best_role["sample_size_warning"] else "medium",
            }
        )

    apply_windows = estimate_best_apply_windows(db)
    if apply_windows["warning"]:
        insights.append(
            {
                "title": "Apply-window estimate is limited",
                "detail": apply_windows["warning"],
                "category": "apply_windows",
                "confidence": "low",
            }
        )
    else:
        days = ", ".join(apply_windows["recommended_focus_days"])
        insights.append(
            {
                "title": "Observed focus days",
                "detail": f"Based on collected history, consider focusing on: {days}. Treat this as guidance, not a guarantee.",
                "category": "apply_windows",
                "confidence": apply_windows["confidence"],
            }
        )

    return insights[:8]


def recalculate_prediction_scores(db: Session) -> dict[str, Any]:
    context = _prediction_context(db)
    jobs = context["jobs"]
    updated_at = _now()
    updated_jobs = 0
    priority_scores: list[float] = []
    high_priority_count = 0
    high_close_risk_count = 0
    low_confidence_count = 0

    for job in jobs:
        bundle = _job_prediction_bundle(job, context)
        priority = bundle["priority"]
        close_risk = bundle["close_risk"]
        response = bundle["response_likelihood"]

        job.predicted_priority_score = priority["predicted_priority_score"]
        job.predicted_close_risk_score = close_risk["predicted_close_risk_score"]
        job.predicted_response_score = response["predicted_response_score"]
        job.prediction_confidence = priority["confidence"]
        job.prediction_evidence = {
            "priority": priority,
            "close_risk": close_risk,
            "response_likelihood": response,
            "summary": [
                f"Predicted application priority: {priority['predicted_priority_score']}/100.",
                f"Predicted close risk: {close_risk['predicted_close_risk_score']}/100.",
                f"Predicted response likelihood: {response['predicted_response_score']}/100.",
            ],
            "stage": "Stage 11 - Prediction and Improvements",
        }
        job.prediction_updated_at = updated_at
        db.add(job)

        updated_jobs += 1
        priority_scores.append(float(job.predicted_priority_score or 0.0))
        if job.predicted_priority_score >= 70 and job.application_status not in NO_LONGER_APPLYING_STATUSES:
            high_priority_count += 1
        if job.predicted_close_risk_score >= 70:
            high_close_risk_count += 1
        if job.prediction_confidence < 0.4:
            low_confidence_count += 1

    db.commit()

    return {
        "total_jobs": len(jobs),
        "updated_jobs": updated_jobs,
        "average_predicted_priority_score": _average(priority_scores),
        "high_priority_count": high_priority_count,
        "high_close_risk_count": high_close_risk_count,
        "low_confidence_count": low_confidence_count,
        "updated_at": updated_at.isoformat(),
        "message": (
            "Prediction scores recalculated. Treat them as estimates, not guarantees."
            if jobs
            else "No jobs found. Import and score jobs before predictions become useful."
        ),
    }


def get_prediction_dashboard(db: Session) -> dict[str, Any]:
    context = _prediction_context(db)
    jobs = context["jobs"]
    rows = sorted(
        [_prediction_job_row(job, context) for job in jobs],
        key=lambda row: (
            float(row["predicted_priority_score"]),
            float(row["prediction_confidence"]),
            float(row["resume_match_score"]),
        ),
        reverse=True,
    )
    high_priority_jobs = [
        row for row in rows
        if row["predicted_priority_score"] >= 70 and row["application_status"] not in NO_LONGER_APPLYING_STATUSES
    ]
    high_close_risk_jobs = [row for row in rows if row["predicted_close_risk_score"] >= 70]
    low_confidence_predictions = [row for row in rows if row["prediction_confidence"] < 0.4]
    apply_windows = estimate_best_apply_windows(db)
    best_observed_apply_day = None if apply_windows.get("warning") else (
        apply_windows["recommended_focus_days"][0]
        if apply_windows.get("recommended_focus_days")
        else None
    )

    return {
        "status": "stage11_prediction_dashboard",
        "generated_at": _now().isoformat(),
        "summary": {
            "total_jobs": len(jobs),
            "scored_jobs": sum(1 for job in jobs if _job_was_scored(job)),
            "applied_jobs": int(context["applied_count"]),
            "response_count": int(context["response_count"]),
            "average_predicted_priority_score": _average([row["predicted_priority_score"] for row in rows]),
            "high_priority_jobs": len(high_priority_jobs),
            "high_close_risk_jobs": len(high_close_risk_jobs),
            "low_confidence_predictions": len(low_confidence_predictions),
            "best_observed_apply_day": best_observed_apply_day,
            "warning": (
                "Import and score jobs before predictions become useful."
                if not jobs
                else "Track applications and outcomes to improve response estimates."
                if int(context["applied_count"]) < MIN_RESPONSE_HISTORY_SAMPLE
                else None
            ),
        },
        "top_priority_jobs": rows[:10],
        "high_close_risk_jobs": high_close_risk_jobs[:10],
        "response_likelihood_summary": {
            "applied_jobs": int(context["applied_count"]),
            "response_count": int(context["response_count"]),
            "average_predicted_response_score": _average([row["predicted_response_score"] for row in rows]),
            "warning": (
                "Not enough applied-job history for reliable response estimates."
                if int(context["applied_count"]) < MIN_RESPONSE_HISTORY_SAMPLE
                else None
            ),
        },
        "source_quality": estimate_source_quality(db),
        "role_quality": estimate_role_quality(db),
        "apply_windows": apply_windows,
        "insights": generate_prediction_insights(db),
        "export_formats": ["json", "csv"],
        "note": "Predictions are cautious local estimates from stored CareerAgent data, not guarantees.",
    }


def _safe_export_job_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": row["job_id"],
        "company": row["company"],
        "title": row["title"],
        "location": row["location"],
        "url": row["url"],
        "source": row["source"],
        "role_category": row["role_category"],
        "application_status": row["application_status"],
        "verification_status": row["verification_status"],
        "overall_priority_score": row["overall_priority_score"],
        "resume_match_score": row["resume_match_score"],
        "predicted_priority_score": row["predicted_priority_score"],
        "predicted_close_risk_score": row["predicted_close_risk_score"],
        "predicted_response_score": row["predicted_response_score"],
        "prediction_confidence": row["prediction_confidence"],
        "prediction_confidence_label": row["prediction_confidence_label"],
        "risk_label": row["risk_label"],
        "suggested_action": row["suggested_action"],
        "prediction_updated_at": row["prediction_updated_at"],
    }


def get_prediction_data_export(db: Session, format: str = "json") -> dict[str, Any] | str:
    normalized_format = (format or "json").strip().lower()
    rows = [_safe_export_job_row(row) for row in get_prediction_jobs(db, include_closed=True)]

    if normalized_format == "json":
        return {
            "status": "careeragent_prediction_export",
            "exported_at": _now().isoformat(),
            "safe_export_note": "This export excludes profile, resume, notes, packet contents, generated files, and API keys.",
            "jobs": rows,
            "source_quality": estimate_source_quality(db),
            "role_quality": estimate_role_quality(db),
            "apply_windows": estimate_best_apply_windows(db),
            "insights": generate_prediction_insights(db),
        }

    if normalized_format == "csv":
        output = StringIO()
        fieldnames = [
            "job_id",
            "company",
            "title",
            "location",
            "url",
            "source",
            "role_category",
            "application_status",
            "verification_status",
            "overall_priority_score",
            "resume_match_score",
            "predicted_priority_score",
            "predicted_close_risk_score",
            "predicted_response_score",
            "prediction_confidence",
            "prediction_confidence_label",
            "risk_label",
            "suggested_action",
            "prediction_updated_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    raise ValueError("Unsupported export format. Use json or csv.")
