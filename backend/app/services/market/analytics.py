from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timedelta, timezone
from io import StringIO
import json
from statistics import median
from typing import Any

from sqlalchemy.orm import Session

from app.services.ai import build_market_insights_prompt, check_no_unsupported_claims, get_ai_provider
from app.models.application_event import ApplicationEvent
from app.models.application_packet import ApplicationPacket
from app.models.job import Job

VERIFICATION_STATUS_ORDER = [
    "open",
    "probably_open",
    "unknown",
    "possibly_closed",
    "likely_closed",
    "closed",
]
APPLICATION_STATUS_ORDER = [
    "found",
    "saved",
    "verified_open",
    "packet_ready",
    "application_opened",
    "autofill_started",
    "autofill_completed",
    "applied_manual",
    "follow_up",
    "interview",
    "rejected",
    "offer",
    "withdrawn",
    "closed_before_apply",
]
APPLIED_OR_LATER_STATUSES = {"applied_manual", "follow_up", "interview", "rejected", "offer"}
RESPONSE_STATUSES = {"interview", "rejected", "offer"}
STALE_VERIFICATION_STATUSES = {"possibly_closed", "likely_closed", "closed"}
STALE_EXCLUDED_APPLICATION_STATUSES = {
    "applied_manual",
    "follow_up",
    "interview",
    "rejected",
    "offer",
    "withdrawn",
    "closed_before_apply",
}
ACTIVITY_EVENT_MAP = {
    "job_verified": "jobs_verified",
    "job_scored": "jobs_scored",
    "packet_generated": "packets_generated",
    "application_link_opened": "application_links_opened",
    "manual_applied": "applications_marked_applied",
    "interview_received": "interviews",
    "rejected": "rejections",
    "offer_received": "offers",
}
SKILL_ALIAS_MAP = {
    "sql": "SQL",
    "aws": "AWS",
    "gcp": "GCP",
    "dbt": "dbt",
    "etl": "ETL",
    "api": "API",
    "apis": "APIs",
    "ml": "ML",
    "ai": "AI",
    "scikit learn": "scikit-learn",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "postgresql": "PostgreSQL",
}
SCORE_BUCKETS = [
    (0, 20, "0-20"),
    (21, 40, "21-40"),
    (41, 60, "41-60"),
    (61, 80, "61-80"),
    (81, 100, "81-100"),
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return _now().date()


def _normalize_group_name(value: Any, *, fallback: str = "Unknown") -> str:
    if value is None:
        return fallback
    normalized = str(value).strip()
    return normalized or fallback


def _normalize_skill_name(skill: Any) -> str:
    normalized = _normalize_group_name(skill, fallback="").lower().replace("/", " ").replace("-", " ")
    normalized = " ".join(normalized.split())
    if not normalized:
        return ""
    if normalized in SKILL_ALIAS_MAP:
        return SKILL_ALIAS_MAP[normalized]
    if normalized.upper() in {"SQL", "AWS", "GCP", "API", "APIS", "ML", "AI"}:
        return normalized.upper()
    return " ".join(part.capitalize() for part in normalized.split())


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


def _score_distribution(values: list[float]) -> list[dict[str, Any]]:
    distribution: list[dict[str, Any]] = []
    for minimum, maximum, label in SCORE_BUCKETS:
        count = sum(1 for value in values if minimum <= value <= maximum)
        distribution.append({"bucket": label, "count": count})
    return distribution


def _group_sort_key(entry: dict[str, Any]) -> tuple[Any, ...]:
    return (
        entry.get("count", 0),
        entry.get("applied_count", 0),
        entry.get("average_priority_score", 0.0),
        entry.get("name", ""),
    )


def _job_was_verified(job: Job) -> bool:
    return bool(
        job.last_checked_date
        or job.verification_status != "unknown"
        or job.verification_evidence
        or job.verification_raw_data
        or job.last_verification_error
    )


def _job_was_scored(job: Job) -> bool:
    return bool(job.scoring_status == "scored" or job.scored_at is not None)


def _job_has_completed_packet(job: Job) -> bool:
    return bool(job.packet_generated_at is not None or job.application_status in {"packet_ready", "application_opened", "autofill_started", "autofill_completed"} | APPLIED_OR_LATER_STATUSES)


def _job_has_application_opened(job: Job) -> bool:
    return bool(
        job.application_link_opened_at is not None
        or job.application_status in {"application_opened", "autofill_started", "autofill_completed"} | APPLIED_OR_LATER_STATUSES
    )


def _job_has_applied(job: Job) -> bool:
    return bool(job.applied_at is not None or job.application_status in APPLIED_OR_LATER_STATUSES)


def _job_is_follow_up(job: Job) -> bool:
    return bool(job.follow_up_at is not None or job.application_status == "follow_up")


def _job_is_interview(job: Job) -> bool:
    return job.application_status == "interview"


def _job_is_rejected(job: Job) -> bool:
    return job.application_status == "rejected"


def _job_is_offer(job: Job) -> bool:
    return job.application_status == "offer"


def _job_is_withdrawn(job: Job) -> bool:
    return bool(job.withdrawn_at is not None or job.application_status == "withdrawn")


def _job_is_closed_before_apply(job: Job) -> bool:
    return bool(job.closed_before_apply_at is not None or job.application_status == "closed_before_apply")


def _group_jobs(jobs: list[Job], key_getter: Any) -> list[dict[str, Any]]:
    grouped: dict[str, list[Job]] = defaultdict(list)
    for job in jobs:
        grouped[_normalize_group_name(key_getter(job))].append(job)

    rows: list[dict[str, Any]] = []
    for name, grouped_jobs in grouped.items():
        scored_jobs = [job for job in grouped_jobs if _job_was_scored(job)]
        rows.append(
            {
                "name": name,
                "count": len(grouped_jobs),
                "average_resume_match_score": _average([job.resume_match_score for job in scored_jobs]),
                "average_priority_score": _average([job.overall_priority_score for job in scored_jobs]),
                "applied_count": sum(1 for job in grouped_jobs if _job_has_applied(job)),
                "interview_count": sum(1 for job in grouped_jobs if _job_is_interview(job)),
            }
        )

    return sorted(rows, key=_group_sort_key, reverse=True)


def _completed_packet_job_ids(packets: list[ApplicationPacket]) -> set[int]:
    return {
        packet.job_id
        for packet in packets
        if packet.generation_status in {"completed", "completed_with_warnings"}
    }


def get_pipeline_summary(db: Session) -> dict[str, Any]:
    jobs = db.query(Job).all()
    packets = db.query(ApplicationPacket).all()
    completed_packet_job_ids = _completed_packet_job_ids(packets)

    total_jobs = len(jobs)
    verified_jobs = sum(1 for job in jobs if _job_was_verified(job))
    scored_jobs = sum(1 for job in jobs if _job_was_scored(job))
    packet_ready_jobs = sum(
        1
        for job in jobs
        if job.application_status == "packet_ready" or job.id in completed_packet_job_ids or job.packet_generated_at is not None
    )
    application_opened_jobs = sum(1 for job in jobs if _job_has_application_opened(job))
    applied_jobs = sum(1 for job in jobs if _job_has_applied(job))
    follow_up_jobs = sum(1 for job in jobs if _job_is_follow_up(job))
    interview_jobs = sum(1 for job in jobs if _job_is_interview(job))
    rejected_jobs = sum(1 for job in jobs if _job_is_rejected(job))
    offer_jobs = sum(1 for job in jobs if _job_is_offer(job))
    withdrawn_jobs = sum(1 for job in jobs if _job_is_withdrawn(job))
    closed_before_apply_jobs = sum(1 for job in jobs if _job_is_closed_before_apply(job))

    return {
        "total_jobs": total_jobs,
        "verified_jobs": verified_jobs,
        "scored_jobs": scored_jobs,
        "packet_ready_jobs": packet_ready_jobs,
        "application_opened_jobs": application_opened_jobs,
        "applied_jobs": applied_jobs,
        "follow_up_jobs": follow_up_jobs,
        "interview_jobs": interview_jobs,
        "rejected_jobs": rejected_jobs,
        "offer_jobs": offer_jobs,
        "withdrawn_jobs": withdrawn_jobs,
        "closed_before_apply_jobs": closed_before_apply_jobs,
        "application_rate": _safe_rate(applied_jobs, total_jobs),
        "interview_rate": _safe_rate(interview_jobs, applied_jobs),
        "offer_rate": _safe_rate(offer_jobs, applied_jobs),
        "rejection_rate": _safe_rate(rejected_jobs, applied_jobs),
        "application_rate_explanation": None if total_jobs else "Import jobs to see pipeline conversion rates.",
        "response_rate_explanation": None if applied_jobs else "Mark applications applied to calculate interview, offer, and rejection rates.",
    }


def get_jobs_by_role(db: Session) -> list[dict[str, Any]]:
    return _group_jobs(db.query(Job).all(), lambda job: job.role_category)


def get_jobs_by_company(db: Session) -> list[dict[str, Any]]:
    return _group_jobs(db.query(Job).all(), lambda job: job.company)


def get_jobs_by_location(db: Session) -> list[dict[str, Any]]:
    return _group_jobs(db.query(Job).all(), lambda job: job.location)


def get_jobs_by_source(db: Session) -> list[dict[str, Any]]:
    return _group_jobs(db.query(Job).all(), lambda job: job.source)


def get_jobs_by_verification_status(db: Session) -> list[dict[str, Any]]:
    jobs = db.query(Job).all()
    counts = Counter(_normalize_group_name(job.verification_status) for job in jobs)
    rows = [{"name": status, "count": counts.get(status, 0)} for status in VERIFICATION_STATUS_ORDER]
    extra_statuses = sorted(set(counts) - set(VERIFICATION_STATUS_ORDER))
    rows.extend({"name": status, "count": counts[status]} for status in extra_statuses)
    return [row for row in rows if row["count"] > 0 or not jobs]


def get_jobs_by_application_status(db: Session) -> list[dict[str, Any]]:
    jobs = db.query(Job).all()
    counts = Counter(_normalize_group_name(job.application_status) for job in jobs)
    rows = [{"name": status, "count": counts.get(status, 0)} for status in APPLICATION_STATUS_ORDER]
    extra_statuses = sorted(set(counts) - set(APPLICATION_STATUS_ORDER))
    rows.extend({"name": status, "count": counts[status]} for status in extra_statuses)
    return [row for row in rows if row["count"] > 0 or not jobs]


def get_top_requested_skills(db: Session, limit: int = 20) -> list[dict[str, Any]]:
    skill_counts: dict[str, dict[str, int]] = {}
    for job in db.query(Job).all():
        for skill in job.required_skills or []:
            normalized = _normalize_skill_name(skill)
            if not normalized:
                continue
            entry = skill_counts.setdefault(normalized, {"count": 0, "required_count": 0, "preferred_count": 0})
            entry["count"] += 1
            entry["required_count"] += 1
        for skill in job.preferred_skills or []:
            normalized = _normalize_skill_name(skill)
            if not normalized:
                continue
            entry = skill_counts.setdefault(normalized, {"count": 0, "required_count": 0, "preferred_count": 0})
            entry["count"] += 1
            entry["preferred_count"] += 1

    rows = [
        {
            "skill": skill,
            "count": values["count"],
            "required_count": values["required_count"],
            "preferred_count": values["preferred_count"],
        }
        for skill, values in skill_counts.items()
    ]
    return sorted(rows, key=lambda row: (row["count"], row["required_count"], row["skill"]), reverse=True)[:limit]


def get_top_missing_skills(db: Session, limit: int = 20) -> list[dict[str, Any]]:
    missing_counts: dict[str, dict[str, int]] = {}

    for job in db.query(Job).all():
        scoring_source = dict(job.scoring_raw_data or {})
        if not scoring_source:
            skill_match = dict((job.scoring_evidence or {}).get("skill_match") or {})
            scoring_source = {
                "missing_required_skills": list(skill_match.get("missing_required_skills") or []),
                "missing_preferred_skills": list(skill_match.get("missing_preferred_skills") or []),
            }

        for skill in scoring_source.get("missing_required_skills") or []:
            normalized = _normalize_skill_name(skill)
            if not normalized:
                continue
            entry = missing_counts.setdefault(
                normalized,
                {"count": 0, "missing_required_count": 0, "missing_preferred_count": 0},
            )
            entry["count"] += 1
            entry["missing_required_count"] += 1

        for skill in scoring_source.get("missing_preferred_skills") or []:
            normalized = _normalize_skill_name(skill)
            if not normalized:
                continue
            entry = missing_counts.setdefault(
                normalized,
                {"count": 0, "missing_required_count": 0, "missing_preferred_count": 0},
            )
            entry["count"] += 1
            entry["missing_preferred_count"] += 1

    rows = [
        {
            "skill": skill,
            "count": values["count"],
            "missing_required_count": values["missing_required_count"],
            "missing_preferred_count": values["missing_preferred_count"],
        }
        for skill, values in missing_counts.items()
    ]
    return sorted(
        rows,
        key=lambda row: (row["count"], row["missing_required_count"], row["skill"]),
        reverse=True,
    )[:limit]


def get_score_summary(db: Session) -> dict[str, Any]:
    scored_jobs = [job for job in db.query(Job).all() if _job_was_scored(job)]
    if not scored_jobs:
        return {
            "average_resume_match_score": 0.0,
            "median_resume_match_score": 0.0,
            "average_overall_priority_score": 0.0,
            "average_skill_match_score": 0.0,
            "average_role_match_score": 0.0,
            "average_location_score": 0.0,
            "top_scored_jobs": [],
            "low_scored_jobs": [],
            "score_distribution": _score_distribution([]),
            "message": "Score jobs to see match analytics.",
        }

    sorted_by_priority = sorted(
        scored_jobs,
        key=lambda job: (job.overall_priority_score, job.resume_match_score, job.verification_score),
        reverse=True,
    )
    sorted_by_low_priority = sorted(
        scored_jobs,
        key=lambda job: (job.overall_priority_score, job.resume_match_score, job.verification_score),
    )

    def _job_score_row(job: Job) -> dict[str, Any]:
        return {
            "job_id": job.id,
            "company": job.company,
            "title": job.title,
            "role_category": _normalize_group_name(job.role_category),
            "resume_match_score": _round_number(job.resume_match_score),
            "overall_priority_score": _round_number(job.overall_priority_score),
            "verification_status": job.verification_status,
        }

    priority_scores = [float(job.overall_priority_score or 0.0) for job in scored_jobs]
    resume_scores = [float(job.resume_match_score or 0.0) for job in scored_jobs]

    return {
        "average_resume_match_score": _average(resume_scores),
        "median_resume_match_score": _round_number(median(resume_scores)),
        "average_overall_priority_score": _average(priority_scores),
        "average_skill_match_score": _average([job.skill_match_score for job in scored_jobs]),
        "average_role_match_score": _average([job.role_match_score for job in scored_jobs]),
        "average_location_score": _average([job.location_score for job in scored_jobs]),
        "top_scored_jobs": [_job_score_row(job) for job in sorted_by_priority[:5]],
        "low_scored_jobs": [_job_score_row(job) for job in sorted_by_low_priority[:5]],
        "score_distribution": _score_distribution(priority_scores),
        "message": None,
    }


def get_verification_summary(db: Session) -> dict[str, Any]:
    jobs = db.query(Job).all()
    verification_scores = [float(job.verification_score or 0.0) for job in jobs]
    likely_closed_scores = [float(job.likely_closed_score or 0.0) for job in jobs]
    counts = Counter(_normalize_group_name(job.verification_status) for job in jobs)
    stale_jobs = get_stale_jobs(db)

    return {
        "average_verification_score": _average(verification_scores),
        "average_likely_closed_score": _average(likely_closed_scores),
        "counts_by_verification_status": {
            status: counts.get(status, 0)
            for status in VERIFICATION_STATUS_ORDER
        },
        "jobs_checked_recently": sum(
            1
            for job in jobs
            if job.last_checked_date is not None and (_today() - job.last_checked_date).days <= 7
        ),
        "stale_jobs_count": len(stale_jobs),
        "likely_closed_jobs_count": counts.get("likely_closed", 0),
        "closed_jobs_count": counts.get("closed", 0),
    }


def get_outcome_summary(db: Session) -> dict[str, Any]:
    jobs = db.query(Job).all()
    applied_count = sum(1 for job in jobs if _job_has_applied(job))
    interview_count = sum(1 for job in jobs if _job_is_interview(job))
    rejected_count = sum(1 for job in jobs if _job_is_rejected(job))
    offer_count = sum(1 for job in jobs if _job_is_offer(job))
    follow_up_count = sum(1 for job in jobs if _job_is_follow_up(job))
    response_count = interview_count + rejected_count + offer_count

    return {
        "applied_count": applied_count,
        "interview_count": interview_count,
        "rejected_count": rejected_count,
        "offer_count": offer_count,
        "follow_up_count": follow_up_count,
        "response_count": response_count,
        "response_rate": _safe_rate(response_count, applied_count),
        "interview_rate": _safe_rate(interview_count, applied_count),
        "offer_rate": _safe_rate(offer_count, applied_count),
        "message": None if applied_count else "Apply to more jobs to calculate meaningful response rates.",
    }


def _response_rows_for_groups(grouped_jobs: dict[str, list[Job]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, jobs in grouped_jobs.items():
        applied_count = sum(1 for job in jobs if _job_has_applied(job))
        interview_count = sum(1 for job in jobs if _job_is_interview(job))
        rejected_count = sum(1 for job in jobs if _job_is_rejected(job))
        offer_count = sum(1 for job in jobs if _job_is_offer(job))
        response_count = interview_count + rejected_count + offer_count
        if applied_count == 0:
            continue
        rows.append(
            {
                "name": name,
                "applied_count": applied_count,
                "response_count": response_count,
                "response_rate": _safe_rate(response_count, applied_count),
                "interview_count": interview_count,
                "interview_rate": _safe_rate(interview_count, applied_count),
                "offer_count": offer_count,
                "offer_rate": _safe_rate(offer_count, applied_count),
                "rejected_count": rejected_count,
                "sample_size_warning": applied_count < 2,
            }
        )
    return sorted(rows, key=lambda row: (row["response_rate"] or 0.0, row["applied_count"], row["name"]), reverse=True)


def get_response_rates(db: Session) -> dict[str, Any]:
    jobs = db.query(Job).all()
    grouped: dict[str, dict[str, list[Job]]] = {
        "by_role": defaultdict(list),
        "by_source": defaultdict(list),
        "by_company": defaultdict(list),
        "by_location": defaultdict(list),
    }
    for job in jobs:
        grouped["by_role"][_normalize_group_name(job.role_category)].append(job)
        grouped["by_source"][_normalize_group_name(job.source)].append(job)
        grouped["by_company"][_normalize_group_name(job.company)].append(job)
        grouped["by_location"][_normalize_group_name(job.location)].append(job)

    by_role = _response_rows_for_groups(grouped["by_role"])
    by_source = _response_rows_for_groups(grouped["by_source"])
    by_company = _response_rows_for_groups(grouped["by_company"])
    by_location = _response_rows_for_groups(grouped["by_location"])
    sample_size_warning = any(row["sample_size_warning"] for row in by_role + by_source + by_company + by_location)

    return {
        "by_role": by_role,
        "by_source": by_source,
        "by_company": by_company,
        "by_location": by_location,
        "sample_size_warning": sample_size_warning,
        "message": None if (by_role or by_source or by_company or by_location) else "Response rate needs applied jobs and outcomes.",
    }


def _activity_date_range(days: int) -> list[date]:
    safe_days = max(days, 1)
    start_day = _today() - timedelta(days=safe_days - 1)
    return [start_day + timedelta(days=offset) for offset in range(safe_days)]


def _activity_timestamp_to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def get_activity_over_time(db: Session, days: int = 30) -> dict[str, Any]:
    range_days = _activity_date_range(days)
    start_day = range_days[0]
    series_by_day: dict[date, dict[str, Any]] = {
        day: {
            "date": day.isoformat(),
            "jobs_imported": 0,
            "jobs_verified": 0,
            "jobs_scored": 0,
            "packets_generated": 0,
            "application_links_opened": 0,
            "applications_marked_applied": 0,
            "interviews": 0,
            "rejections": 0,
            "offers": 0,
        }
        for day in range_days
    }
    metric_event_pairs: set[tuple[int, str, date]] = set()

    jobs = db.query(Job).all()
    events = db.query(ApplicationEvent).all()

    for job in jobs:
        import_day = _activity_timestamp_to_date(job.created_at) or job.first_seen_date
        if import_day and import_day >= start_day and import_day in series_by_day:
            series_by_day[import_day]["jobs_imported"] += 1

    for event in events:
        metric_key = ACTIVITY_EVENT_MAP.get(event.event_type)
        event_day = _activity_timestamp_to_date(event.event_time)
        if metric_key is None or event_day is None or event_day < start_day or event_day not in series_by_day:
            continue
        series_by_day[event_day][metric_key] += 1
        metric_event_pairs.add((event.job_id, metric_key, event_day))

    timestamp_metric_pairs = [
        ("jobs_verified", lambda job: _activity_timestamp_to_date(job.last_checked_date)),
        ("jobs_scored", lambda job: _activity_timestamp_to_date(job.scored_at)),
        ("packets_generated", lambda job: _activity_timestamp_to_date(job.packet_generated_at)),
        ("application_links_opened", lambda job: _activity_timestamp_to_date(job.application_link_opened_at)),
        ("applications_marked_applied", lambda job: _activity_timestamp_to_date(job.applied_at)),
        ("interviews", lambda job: _activity_timestamp_to_date(job.interview_at)),
        ("rejections", lambda job: _activity_timestamp_to_date(job.rejected_at)),
        ("offers", lambda job: _activity_timestamp_to_date(job.offer_at)),
    ]
    for job in jobs:
        for metric_key, getter in timestamp_metric_pairs:
            metric_day = getter(job)
            if metric_day is None or metric_day < start_day or metric_day not in series_by_day:
                continue
            if (job.id, metric_key, metric_day) in metric_event_pairs:
                continue
            series_by_day[metric_day][metric_key] += 1

    return {
        "days": len(range_days),
        "series": [series_by_day[day] for day in range_days],
    }


def get_stale_jobs(db: Session) -> list[dict[str, Any]]:
    stale_jobs: list[dict[str, Any]] = []
    today = _today()

    for job in db.query(Job).all():
        if job.application_status in STALE_EXCLUDED_APPLICATION_STATUSES:
            continue

        days_since_first_seen = (today - job.first_seen_date).days if job.first_seen_date else None
        days_since_last_checked = (today - job.last_checked_date).days if job.last_checked_date else None
        likely_closed_score = float(job.likely_closed_score or 0.0)

        stale_reasons = [
            job.verification_status in STALE_VERIFICATION_STATUSES,
            likely_closed_score >= 70,
            days_since_first_seen is not None and days_since_first_seen >= 90,
            days_since_first_seen is not None and days_since_first_seen >= 60 and (days_since_last_checked is None or days_since_last_checked >= 21),
        ]
        if not any(stale_reasons):
            continue

        if job.verification_status in {"closed", "likely_closed"} or likely_closed_score >= 85:
            recommendation = "mark closed_before_apply"
        elif days_since_last_checked is None or days_since_last_checked >= 21:
            recommendation = "reverify"
        else:
            recommendation = "deprioritize"

        stale_jobs.append(
            {
                "job_id": job.id,
                "company": job.company,
                "title": job.title,
                "verification_status": job.verification_status,
                "likely_closed_score": _round_number(likely_closed_score),
                "days_since_first_seen": days_since_first_seen,
                "recommendation": recommendation,
            }
        )

    return sorted(
        stale_jobs,
        key=lambda row: (row["likely_closed_score"], row["days_since_first_seen"] or 0, row["company"], row["title"]),
        reverse=True,
    )


def _rule_based_recommended_insights(db: Session) -> list[dict[str, Any]]:
    pipeline = get_pipeline_summary(db)
    requested_skills = get_top_requested_skills(db, limit=1)
    missing_skills = get_top_missing_skills(db, limit=1)
    score_summary = get_score_summary(db)
    stale_jobs = get_stale_jobs(db)
    response_rates = get_response_rates(db)
    insights: list[dict[str, Any]] = []

    total_jobs = int(pipeline["total_jobs"])
    if total_jobs == 0:
        return [
            {
                "title": "Import jobs to see market analytics",
                "detail": "CareerAgent will start building pipeline, skill, and outcome analytics after you save job records.",
                "category": "getting_started",
            }
        ]

    if pipeline["verified_jobs"] < total_jobs:
        insights.append(
            {
                "title": "More jobs need verification",
                "detail": f"You have {total_jobs} jobs saved but only {pipeline['verified_jobs']} verified. Verify the rest to improve availability analytics.",
                "category": "pipeline",
            }
        )

    if pipeline["scored_jobs"] < total_jobs:
        insights.append(
            {
                "title": "Score more jobs for better ranking",
                "detail": f"You have {total_jobs} jobs saved but only {pipeline['scored_jobs']} scored. Score the remaining jobs to improve recommendations.",
                "category": "scoring",
            }
        )

    if requested_skills:
        top_skill = requested_skills[0]
        insights.append(
            {
                "title": "Top requested skill",
                "detail": f"{top_skill['skill']} appears in {top_skill['count']} saved job requirements or preferences.",
                "category": "skills",
            }
        )

    if missing_skills:
        top_missing = missing_skills[0]
        insights.append(
            {
                "title": "Most common missing skill",
                "detail": f"{top_missing['skill']} is the most common missing skill in the current scored jobs.",
                "category": "skills",
            }
        )

    if stale_jobs:
        insights.append(
            {
                "title": "Some jobs may be stale",
                "detail": f"{len(stale_jobs)} saved jobs look stale or likely closed. Reverify or deprioritize them before spending more time.",
                "category": "verification",
            }
        )

    if pipeline["packet_ready_jobs"] > pipeline["applied_jobs"]:
        insights.append(
            {
                "title": "Packet-ready jobs are waiting",
                "detail": f"You have {pipeline['packet_ready_jobs']} packet-ready jobs but only {pipeline['applied_jobs']} jobs marked applied.",
                "category": "pipeline",
            }
        )

    top_role_rows = [row for row in get_jobs_by_role(db) if row["count"] >= 2]
    if top_role_rows:
        best_role = max(top_role_rows, key=lambda row: row["average_resume_match_score"])
        insights.append(
            {
                "title": "Observed strongest role fit",
                "detail": f"In your collected data so far, {best_role['name']} roles show the highest average resume-match score.",
                "category": "scoring",
            }
        )

    if response_rates["message"]:
        insights.append(
            {
                "title": "Response rate needs more data",
                "detail": response_rates["message"],
                "category": "outcomes",
            }
        )
    else:
        comparable_roles = [row for row in response_rates["by_role"] if row["applied_count"] >= 2]
        if comparable_roles:
            best_role = max(comparable_roles, key=lambda row: row["response_rate"] or 0.0)
            insights.append(
                {
                    "title": "Observed response-rate leader",
                    "detail": f"In your current data, {best_role['name']} roles have the highest observed response rate. This is descriptive, not predictive.",
                    "category": "outcomes",
                }
            )

    if score_summary["message"]:
        insights.append(
            {
                "title": "Score jobs to unlock match analytics",
                "detail": score_summary["message"],
                "category": "scoring",
            }
        )

    return insights[:8]


def _parse_ai_insight_text(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in str(text or "").splitlines():
        cleaned = line.strip().lstrip("-* ").strip()
        if not cleaned or cleaned.lower().startswith("ai draft") or cleaned.lower().startswith("mockprovider"):
            continue
        title = "AI Insight"
        detail = cleaned
        if ": " in cleaned:
            maybe_title, maybe_detail = cleaned.split(": ", 1)
            if len(maybe_title) <= 60:
                title = maybe_title.strip().rstrip(".")
                detail = maybe_detail.strip()
        rows.append({"title": title, "detail": detail, "category": "ai_draft"})
    return rows[:6]


def get_recommended_insights(
    db: Session,
    *,
    use_ai: bool = False,
    provider_name: str | None = None,
) -> list[dict[str, Any]]:
    rule_based = _rule_based_recommended_insights(db)
    if not use_ai:
        return rule_based

    provider = get_ai_provider(provider_name)
    if not provider.is_available():
        return rule_based + [
            {
                "title": "AI provider unavailable",
                "detail": provider.unavailable_reason or "Falling back to rule-based insights.",
                "category": "ai_fallback",
            }
        ]

    market_data = {
        "pipeline_summary": get_pipeline_summary(db),
        "score_summary": get_score_summary(db),
        "outcome_summary": get_outcome_summary(db),
        "response_rates": get_response_rates(db),
        "top_requested_skills": get_top_requested_skills(db, limit=5),
        "top_missing_skills": get_top_missing_skills(db, limit=5),
        "stale_jobs": get_stale_jobs(db)[:5],
    }
    ai_response = provider.generate_text(
        "market_insights",
        build_market_insights_prompt(market_data),
        context={"market_data": market_data},
    )
    if not ai_response.get("success"):
        return rule_based + [
            {
                "title": "AI insights fell back to rule-based mode",
                "detail": "; ".join(list(ai_response.get("warnings") or [])) or "The AI provider did not return usable insights.",
                "category": "ai_fallback",
            }
        ]

    safety = check_no_unsupported_claims(str(ai_response.get("content") or ""), {}, json.dumps(market_data, default=str))
    ai_rows = _parse_ai_insight_text(str(safety.get("content") or ""))
    if not ai_rows:
        return rule_based

    warnings = list(ai_response.get("warnings") or []) + list(safety.get("warnings") or [])
    if warnings:
        ai_rows.append(
            {
                "title": "AI review note",
                "detail": "; ".join(warnings[:3]),
                "category": "ai_warning",
            }
        )
    return ai_rows


def _safe_export_jobs(db: Session) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for job in db.query(Job).order_by(Job.created_at.desc(), Job.id.desc()).all():
        rows.append(
            {
                "job_id": job.id,
                "company": job.company,
                "title": job.title,
                "location": job.location,
                "source": job.source,
                "role_category": job.role_category,
                "seniority_level": job.seniority_level,
                "verification_status": job.verification_status,
                "verification_score": _round_number(job.verification_score),
                "likely_closed_score": _round_number(job.likely_closed_score),
                "resume_match_score": _round_number(job.resume_match_score),
                "overall_priority_score": _round_number(job.overall_priority_score),
                "skill_match_score": _round_number(job.skill_match_score),
                "role_match_score": _round_number(job.role_match_score),
                "location_score": _round_number(job.location_score),
                "application_status": job.application_status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                "first_seen_date": job.first_seen_date.isoformat() if job.first_seen_date else None,
                "last_checked_date": job.last_checked_date.isoformat() if job.last_checked_date else None,
                "packet_generated_at": job.packet_generated_at.isoformat() if job.packet_generated_at else None,
                "applied_at": job.applied_at.isoformat() if job.applied_at else None,
                "interview_at": job.interview_at.isoformat() if job.interview_at else None,
                "rejected_at": job.rejected_at.isoformat() if job.rejected_at else None,
                "offer_at": job.offer_at.isoformat() if job.offer_at else None,
                "required_skills": list(job.required_skills or []),
                "preferred_skills": list(job.preferred_skills or []),
            }
        )
    return rows


def export_market_data(db: Session, format: str = "json") -> dict[str, Any] | str:
    normalized_format = (format or "json").strip().lower()
    jobs = _safe_export_jobs(db)
    dashboard = get_market_dashboard(db)

    if normalized_format == "json":
        return {
            "exported_at": _now().isoformat(),
            "format": "json",
            "dashboard": dashboard,
            "jobs": jobs,
        }

    if normalized_format == "csv":
        output = StringIO()
        fieldnames = [
            "job_id",
            "company",
            "title",
            "location",
            "source",
            "role_category",
            "seniority_level",
            "verification_status",
            "verification_score",
            "likely_closed_score",
            "resume_match_score",
            "overall_priority_score",
            "skill_match_score",
            "role_match_score",
            "location_score",
            "application_status",
            "created_at",
            "updated_at",
            "first_seen_date",
            "last_checked_date",
            "packet_generated_at",
            "applied_at",
            "interview_at",
            "rejected_at",
            "offer_at",
            "required_skills",
            "preferred_skills",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in jobs:
            writer.writerow(
                {
                    **row,
                    "required_skills": "; ".join(row["required_skills"]),
                    "preferred_skills": "; ".join(row["preferred_skills"]),
                }
            )
        return output.getvalue()

    raise ValueError("Unsupported export format. Use json or csv.")


def get_market_dashboard(db: Session) -> dict[str, Any]:
    requested_skills = get_top_requested_skills(db)
    missing_skills = get_top_missing_skills(db)
    return {
        "status": "stage9_dashboard",
        "generated_at": _now().isoformat(),
        "pipeline_summary": get_pipeline_summary(db),
        "jobs_by_role": get_jobs_by_role(db),
        "jobs_by_company": get_jobs_by_company(db),
        "jobs_by_location": get_jobs_by_location(db),
        "jobs_by_source": get_jobs_by_source(db),
        "jobs_by_verification_status": get_jobs_by_verification_status(db),
        "jobs_by_application_status": get_jobs_by_application_status(db),
        "skills": {
            "requested_skills": requested_skills,
            "missing_skills": missing_skills,
            "message": None if (requested_skills or missing_skills) else "Import and score more jobs to see skill analytics.",
        },
        "score_summary": get_score_summary(db),
        "verification_summary": get_verification_summary(db),
        "outcome_summary": get_outcome_summary(db),
        "response_rates": get_response_rates(db),
        "activity_over_time": get_activity_over_time(db, days=30),
        "stale_jobs": get_stale_jobs(db),
        "insights": get_recommended_insights(db),
        "export_formats": ["json", "csv"],
        "note": "Analytics are descriptive and based on your collected CareerAgent data only. Prediction estimates live on the Predictions page.",
    }


def get_market_summary(db: Session) -> dict[str, Any]:
    dashboard = get_market_dashboard(db)
    pipeline = dashboard["pipeline_summary"]
    score_summary = dashboard["score_summary"]
    verification_summary = dashboard["verification_summary"]
    requested_skills = dashboard["skills"]["requested_skills"]
    top_requested_skills = requested_skills[:5]

    return {
        "status": "stage9_summary",
        "jobs_found": pipeline["total_jobs"],
        "total_jobs": pipeline["total_jobs"],
        "verified_jobs": pipeline["verified_jobs"],
        "scored_jobs": pipeline["scored_jobs"],
        "scored_jobs_count": pipeline["scored_jobs"],
        "packets_ready": pipeline["packet_ready_jobs"],
        "packet_ready_jobs": pipeline["packet_ready_jobs"],
        "applications_opened": pipeline["application_opened_jobs"],
        "application_opened_jobs": pipeline["application_opened_jobs"],
        "applied_jobs": pipeline["applied_jobs"],
        "interview_jobs": pipeline["interview_jobs"],
        "offer_jobs": pipeline["offer_jobs"],
        "response_rate": dashboard["outcome_summary"]["response_rate"],
        "average_resume_match_score": score_summary["average_resume_match_score"],
        "average_overall_priority_score": score_summary["average_overall_priority_score"],
        "average_verification_score": verification_summary["average_verification_score"],
        "stale_jobs_count": verification_summary["stale_jobs_count"],
        "top_requested_skills": top_requested_skills,
        "note": dashboard["note"],
    }
