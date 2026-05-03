from collections import Counter
from datetime import date

from sqlalchemy.orm import Session

from app.models.application_packet import ApplicationPacket
from app.models.job import Job
from app.services.jobs.job_store import calculate_freshness_score


def get_market_summary(db: Session) -> dict:
    jobs = db.query(Job).all()
    packets = db.query(ApplicationPacket).all()
    jobs_found = len(jobs)
    sample_job_count = sum(1 for job in jobs if job.source == "sample_seed")
    locations = [job.location for job in jobs if job.location and job.location != "Unknown"]
    top_locations = [location for location, _ in Counter(locations).most_common(5)] or ["No saved jobs yet"]
    verification_counts = {
        "open": 0,
        "probably_open": 0,
        "unknown": 0,
        "possibly_closed": 0,
        "likely_closed": 0,
        "closed": 0,
    }
    verification_scores = [job.verification_score for job in jobs]
    likely_closed_scores = [job.likely_closed_score for job in jobs]
    checked_recently_count = 0
    stale_jobs_count = 0
    scored_jobs = [job for job in jobs if job.scoring_status == "scored"]
    requested_skills_counter: Counter[str] = Counter()
    role_scores: dict[str, list[float]] = {}

    for job in jobs:
        verification_counts[job.verification_status] = verification_counts.get(job.verification_status, 0) + 1
        if job.last_checked_date is not None and (date.today() - job.last_checked_date).days <= 7:
            checked_recently_count += 1
        if calculate_freshness_score(job.posted_date, job.first_seen_date) <= 35:
            stale_jobs_count += 1
        requested_skills_counter.update((job.required_skills or []) + (job.preferred_skills or []))
        if job.role_category and job.scoring_status == "scored":
            role_scores.setdefault(job.role_category, []).append(job.overall_priority_score or 0.0)

    recommendation_jobs = sorted(
        [
            job
            for job in scored_jobs
            if job.verification_status not in {"closed", "likely_closed"}
        ],
        key=lambda job: (job.overall_priority_score, job.resume_match_score, job.verification_score),
        reverse=True,
    )
    top_recommended_jobs = [
        {
            "id": job.id,
            "company": job.company,
            "title": job.title,
            "overall_priority_score": round(job.overall_priority_score, 2),
            "resume_match_score": round(job.resume_match_score, 2),
            "verification_status": job.verification_status,
        }
        for job in recommendation_jobs[:5]
    ]
    top_priority_job = top_recommended_jobs[0] if top_recommended_jobs else None
    top_role_categories = [
        {
            "role_category": role_category,
            "average_overall_priority_score": round(sum(scores) / len(scores), 2),
            "count": len(scores),
        }
        for role_category, scores in sorted(
            role_scores.items(),
            key=lambda item: (sum(item[1]) / len(item[1]), len(item[1])),
            reverse=True,
        )[:5]
        if scores
    ]
    top_requested_skills = [
        {"skill": skill, "count": count}
        for skill, count in requested_skills_counter.most_common(10)
    ]

    ready_packet_job_ids = {
        packet.job_id
        for packet in packets
        if packet.generation_status in {"completed", "completed_with_warnings"}
    }
    applications_opened_count = sum(
        1
        for job in jobs
        if job.application_status in {"application_opened", "autofill_started", "autofill_completed"}
    )

    note = "Market analytics are still a later-stage feature. Stage 7 now adds tracker-aware summaries alongside verification, scoring, and packet generation."
    if sample_job_count:
        note += f" {sample_job_count} saved jobs are optional sample/demo records."

    return {
        "status": "stage7_summary",
        "jobs_found": jobs_found,
        "total_jobs": jobs_found,
        "applications_opened": applications_opened_count,
        "packets_ready": len(ready_packet_job_ids),
        "verified_open_jobs": verification_counts["open"] + verification_counts["probably_open"],
        "verified_checked_jobs": checked_recently_count,
        "open_jobs": verification_counts["open"],
        "probably_open_jobs": verification_counts["probably_open"],
        "unknown_jobs": verification_counts["unknown"],
        "possibly_closed_jobs": verification_counts["possibly_closed"],
        "likely_closed_jobs": verification_counts["likely_closed"],
        "closed_jobs": verification_counts["closed"],
        "risky_jobs": verification_counts["possibly_closed"] + verification_counts["likely_closed"] + verification_counts["closed"],
        "verification_counts": verification_counts,
        "average_verification_score": round(sum(verification_scores) / jobs_found, 2) if jobs_found else 0.0,
        "average_likely_closed_score": round(sum(likely_closed_scores) / jobs_found, 2) if jobs_found else 0.0,
        "scored_jobs_count": len(scored_jobs),
        "average_resume_match_score": round(sum(job.resume_match_score for job in scored_jobs) / len(scored_jobs), 2)
        if scored_jobs
        else 0.0,
        "average_overall_priority_score": round(sum(job.overall_priority_score for job in scored_jobs) / len(scored_jobs), 2)
        if scored_jobs
        else 0.0,
        "checked_recently_count": checked_recently_count,
        "stale_jobs_count": stale_jobs_count,
        "recommendation_count": len(recommendation_jobs),
        "top_priority_job": top_priority_job,
        "top_recommended_jobs": top_recommended_jobs,
        "top_role_categories": top_role_categories,
        "top_requested_skills": top_requested_skills,
        "top_locations": top_locations,
        "note": note,
    }
