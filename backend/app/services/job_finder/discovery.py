from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.job_finder import JobCandidate, JobDiscoveryRun, JobSource
from app.services.jobs.job_store import create_job, update_job
from app.services.scoring import build_job_scoring_updates, score_saved_job
from app.services.tracker import log_event, promote_job_status_if_needed
from app.services.verifier.verifier import build_job_verification_updates, verify_job_record

from .dedupe import duplicate_key_for_candidate, find_duplicate_candidate, find_duplicate_job
from .filters import filter_candidate
from .job_normalizer import normalize_raw_job
from .query_builder import build_search_profile, generate_ai_queries, generate_rule_based_queries, load_search_inputs
from .sources import (
    discover_ashby_jobs,
    discover_company_careers_jobs,
    discover_github_company_list_jobs,
    discover_greenhouse_jobs,
    discover_lever_jobs,
    discover_manual_links,
    discover_remote_board_jobs,
    discover_web_search_jobs,
    discover_workday_jobs,
)

IMPLEMENTED_SOURCES = {"greenhouse", "lever", "ashby", "workday", "company_careers", "remote_board"}
MANUAL_SOURCES = {"linkedin_manual", "indeed_manual", "simplify_manual"}
PLACEHOLDER_SOURCES = {"web_search", "github_company_list"}
SAVED_SOURCE_PRIORITY = {"lever": 0, "greenhouse": 1, "ashby": 2, "company_careers": 3, "workday": 4}
WEB_SEARCH_UNCONFIGURED_MESSAGE = "Web search API is not configured. Add a provider later or use source URLs/company pages."
NO_SOURCE_MESSAGE = (
    "Source URLs are required for source-based discovery. Paste a real ATS board URL, company career page, or manual job link."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _source_for_url(url: str, requested: list[str]) -> str:
    host = (urlparse(url).hostname or "").lower()
    if "jobs.lever.co" in host or "lever.co" in host:
        return "lever"
    if "greenhouse.io" in host:
        return "greenhouse"
    if "ashbyhq.com" in host:
        return "ashby"
    if "myworkdayjobs.com" in host or "workdayjobs.com" in host:
        return "workday"
    if "linkedin." in host:
        return "linkedin_manual"
    if "indeed." in host:
        return "indeed_manual"
    if "remote" in host:
        return "remote_board" if "remote_board" in requested else "company_careers"
    return "company_careers"


def _discover_for_source(source_type: str, url: str, query: str, location: str) -> list[dict]:
    if source_type == "lever":
        return discover_lever_jobs(url, query, location)
    if source_type == "greenhouse":
        return discover_greenhouse_jobs(url, query, location)
    if source_type == "ashby":
        return discover_ashby_jobs(url, query, location)
    if source_type == "workday":
        return discover_workday_jobs(url, query, location)
    if source_type == "company_careers":
        return discover_company_careers_jobs(url, query, location)
    if source_type == "remote_board":
        return discover_remote_board_jobs(url, query, location)
    if source_type in {"linkedin_manual", "indeed_manual", "simplify_manual"}:
        return discover_manual_links([url])
    if source_type == "web_search":
        return discover_web_search_jobs(query=query, location=location)
    if source_type == "github_company_list":
        return discover_github_company_list_jobs(url=url, query=query, location=location)
    return []


def _source_result(source_url: str, source_type: str) -> dict[str, Any]:
    return {
        "source_url": source_url,
        "source_type": source_type,
        "status": "success",
        "found": 0,
        "jobs_fetched": 0,
        "saved_candidates": 0,
        "candidates_saved": 0,
        "good_match": 0,
        "weak_match": 0,
        "excluded": 0,
        "duplicate": 0,
        "duplicates": 0,
        "skipped_incomplete": 0,
        "warnings": [],
        "errors": [],
    }


def _mark_source_warning(result: dict[str, Any], warning: str) -> None:
    result["status"] = "warning" if result.get("status") != "error" else "error"
    result.setdefault("warnings", []).append(warning)


def _mark_source_error(result: dict[str, Any], error: str) -> None:
    result["status"] = "error"
    result.setdefault("errors", []).append(error)


def _count_result_status(result: dict[str, Any], status: str) -> None:
    if status == "good_match":
        result["good_match"] += 1
    elif status == "weak_match":
        result["weak_match"] += 1
    elif status == "excluded":
        result["excluded"] += 1
    elif status == "duplicate":
        result["duplicate"] += 1
        result["duplicates"] += 1
    elif status == "incomplete":
        result["skipped_incomplete"] += 1


def _record_reason(reason_counts: dict[str, int], reasons: list[str], *prefixes: str) -> None:
    for reason in reasons:
        clean = " ".join(str(reason or "").split())
        if not clean:
            continue
        if prefixes and not any(clean.startswith(prefix) for prefix in prefixes):
            continue
        reason_counts[clean] = reason_counts.get(clean, 0) + 1
        return


def _top_reasons(reason_counts: dict[str, int], limit: int = 6) -> list[dict[str, Any]]:
    return [
        {"reason": reason, "count": count}
        for reason, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _exclusion_bucket(reasons: list[str]) -> str:
    excluded = [str(reason or "").lower() for reason in reasons if str(reason or "").startswith("Excluded:")]
    combined = " ".join(excluded or [str(reasons[-1] if reasons else "").lower()])
    if "role" in combined or "title" in combined or "skill signal" in combined:
        return "role"
    if "experience" in combined or "senior" in combined or "years" in combined or "level" in combined:
        return "experience"
    if "degree" in combined or "phd" in combined or "master" in combined:
        return "degree"
    if "location" in combined or "outside target" in combined:
        return "location"
    if "low confidence" in combined:
        return "low_confidence"
    return "other"


def _filter_diagnostics(payload_data: dict[str, Any]) -> dict[str, Any]:
    raw_data = payload_data.get("raw_data") if isinstance(payload_data.get("raw_data"), dict) else {}
    diagnostics = raw_data.get("filter_diagnostics") if isinstance(raw_data, dict) else {}
    return diagnostics if isinstance(diagnostics, dict) else {}


def _primary_exclusion_category(payload_data: dict[str, Any]) -> str:
    diagnostics = _filter_diagnostics(payload_data)
    category = str(diagnostics.get("primary_exclusion_category") or "").strip()
    if category:
        return category
    return _exclusion_bucket(list(payload_data.get("filter_reasons") or []))


def _is_hard_excluded(payload_data: dict[str, Any]) -> bool:
    return bool(_filter_diagnostics(payload_data).get("hard_excluded"))


def _would_show_in_broad(payload_data: dict[str, Any]) -> bool:
    diagnostics = _filter_diagnostics(payload_data)
    if "would_show_in_broad" in diagnostics:
        return bool(diagnostics.get("would_show_in_broad"))
    return not _is_hard_excluded(payload_data)


def _sample_excluded(payloads: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for payload_data in payloads[:limit]:
        raw_data = payload_data.get("raw_data") if isinstance(payload_data.get("raw_data"), dict) else {}
        normalizer = raw_data.get("normalizer") if isinstance(raw_data, dict) else {}
        normalizer = normalizer if isinstance(normalizer, dict) else {}
        degree = normalizer.get("degree") if isinstance(normalizer.get("degree"), dict) else {}
        samples.append(
            {
                "company": payload_data.get("company"),
                "title": payload_data.get("title"),
                "location": payload_data.get("location"),
                "role_category": payload_data.get("role_category"),
                "experience_level": payload_data.get("experience_level"),
                "degree_level": degree.get("degree_level"),
                "primary_exclusion_category": _primary_exclusion_category(payload_data),
                "relevance_score": payload_data.get("relevance_score"),
                "reasons": list(payload_data.get("filter_reasons") or []),
            }
        )
    return samples


def _apply_fit_filters(search_profile: dict[str, Any], payload: dict[str, Any]) -> None:
    search_profile["match_mode"] = str(payload.get("match_mode") or "balanced")
    search_profile["target_experience_levels"] = list(payload.get("target_experience_levels") or ["new_grad_entry", "early_career", "unknown"])
    search_profile["excluded_experience_levels"] = list(payload.get("excluded_experience_levels") or ["senior"])
    search_profile["allow_unknown_location"] = bool(payload.get("allow_unknown_location", True))
    search_profile["degree_filter"] = dict(
        payload.get("degree_filter")
        or {
            "allow_no_degree": True,
            "allow_bachelors": True,
            "allow_masters_preferred": True,
            "allow_masters_required": False,
            "allow_phd_preferred": True,
            "allow_phd_required": False,
            "allow_unknown": True,
        }
    )
    search_profile["location_filter"] = dict(
        payload.get("location_filter")
        or {
            "allow_bay_area": True,
            "allow_remote_us": True,
            "allow_unknown": True,
            "allow_non_bay_area_california": False,
            "allow_other_us": False,
            "allow_international": False,
        }
    )


def _save_candidate(db: Session, payload_data: dict[str, Any], result: dict[str, Any] | None = None) -> JobCandidate:
    db_candidate = JobCandidate(**payload_data)
    db.add(db_candidate)
    if result is not None:
        result["saved_candidates"] += 1
        result["candidates_saved"] += 1
        _count_result_status(result, payload_data["filter_status"])
    return db_candidate


def _candidate_payload(
    candidate: dict[str, Any],
    run: JobDiscoveryRun,
    search_profile: dict[str, Any],
    db: Session,
    source: JobSource | dict | None = None,
) -> dict[str, Any]:
    normalized = normalize_raw_job(candidate, source or {})
    if not normalized.get("source_type"):
        source_type = None
        if isinstance(source, dict):
            source_type = source.get("source_type") or source.get("ats_type")
        elif source is not None:
            source_type = getattr(source, "ats_type", None) or getattr(source, "source_type", None)
        normalized["source_type"] = candidate.get("source_type") or source_type
    filtered = filter_candidate(normalized, search_profile, match_mode=str(search_profile.get("match_mode") or "balanced"))
    duplicate_key = duplicate_key_for_candidate(normalized)
    duplicate_job = find_duplicate_job(db, normalized, duplicate_key)
    duplicate_candidate = find_duplicate_candidate(db, duplicate_key)
    filter_status = filtered["filter_status"]
    reasons = list(filtered["filter_reasons"])
    if filter_status not in {"excluded", "incomplete"} and duplicate_job:
        filter_status = "duplicate"
        reasons.append(f"Duplicate of existing job #{duplicate_job.id}.")
    elif filter_status not in {"excluded", "incomplete"} and duplicate_candidate:
        filter_status = "duplicate"
        reasons.append(f"Duplicate of existing candidate #{duplicate_candidate.id}.")

    raw_data = dict(normalized.get("raw_data") or {})
    if candidate.get("_source_url"):
        raw_data["source_url"] = candidate.get("_source_url")
    if candidate.get("_source_warning"):
        raw_data.setdefault("warnings", []).append(candidate.get("_source_warning"))
    raw_data["filter_diagnostics"] = {
        "primary_exclusion_category": filtered.get("primary_exclusion_category"),
        "hard_excluded": bool(filtered.get("hard_excluded")),
        "would_show_in_broad": bool(filtered.get("would_show_in_broad")),
        "all_reasons": list(filtered.get("all_reasons") or filtered.get("filter_reasons") or []),
    }

    return {
        "discovery_run_id": run.id,
        "source_type": candidate.get("source_type") or run.source_type,
        "source_name": candidate.get("source_name"),
        "company": normalized.get("company") or "Unknown Company",
        "title": normalized.get("title") or "Missing title",
        "location": normalized.get("location") or "Location unknown",
        "url": normalized.get("url") or "",
        "description_snippet": normalized.get("description_snippet"),
        "job_description": normalized.get("job_description"),
        "role_category": normalized.get("role_category"),
        "experience_level": normalized.get("experience_level"),
        "seniority_level": normalized.get("seniority_level"),
        "level_confidence": normalized.get("level_confidence"),
        "location_fit": normalized.get("location_fit"),
        "remote_status": normalized.get("remote_status"),
        "required_skills": list(normalized.get("required_skills") or []),
        "preferred_skills": list(normalized.get("preferred_skills") or []),
        "years_experience_min": normalized.get("years_experience_min"),
        "years_experience_max": normalized.get("years_experience_max"),
        "salary_min": normalized.get("salary_min"),
        "salary_max": normalized.get("salary_max"),
        "salary_currency": normalized.get("salary_currency"),
        "education_requirement": normalized.get("education_requirement"),
        "metadata_confidence": normalized.get("metadata_confidence"),
        "missing_fields": list(normalized.get("missing_fields") or []),
        "posted_date": normalized.get("posted_date"),
        "relevance_score": filtered["relevance_score"],
        "filter_status": filter_status,
        "filter_reasons": reasons,
        "duplicate_key": duplicate_key,
        "duplicate_of_job_id": duplicate_job.id if duplicate_job else None,
        "raw_data": raw_data,
    }


def job_finder_status() -> dict[str, Any]:
    sources = [
        ("greenhouse", "Greenhouse", True, True, False, "Uses public Greenhouse board API when available."),
        ("lever", "Lever", True, True, False, "Uses public Lever postings API when available."),
        ("ashby", "Ashby", True, True, False, "Uses public Ashby posting API or board links when available."),
        ("workday", "Workday", True, True, False, "Conservative URL/slug fallback; full Workday crawling is limited."),
        ("company_careers", "Company career pages", True, True, False, "Fetches one page and follows a small set of job-like links."),
        ("web_search", "Web search", False, False, False, "Web search API is not configured in Stage 12."),
        ("remote_board", "Remote job boards", True, True, False, "Generic source URL support with conservative link extraction."),
        ("linkedin_manual", "LinkedIn pasted links", True, True, True, "Manual links only; CareerAgent does not scrape LinkedIn."),
        ("indeed_manual", "Indeed pasted links", True, True, True, "Manual links only; CareerAgent does not scrape Indeed."),
        ("simplify_manual", "Simplify manual", False, True, True, "Placeholder/manual support."),
        ("github_company_list", "GitHub/company lists", False, False, False, "Placeholder; paste source URLs for now."),
    ]
    return {
        "stage": "Stage 12 - Job Finder + Source Discovery",
        "message": "Safe source-based discovery is available for reviewable candidates. Nothing is auto-imported or auto-applied.",
        "sources": [
            {"source_type": key, "label": label, "implemented": implemented, "configured": configured, "manual_only": manual, "notes": notes}
            for key, label, implemented, configured, manual, notes in sources
        ],
        "safety_rules": [
            "CareerAgent does not scrape LinkedIn or Indeed automatically.",
            "CareerAgent uses small source-based fetches with timeouts and a normal user agent.",
            "CareerAgent does not bypass login walls, CAPTCHAs, or anti-bot protections.",
            "CareerAgent never imports discovered candidates unless the user chooses Import.",
            "CareerAgent never applies or submits applications.",
        ],
    }


def generate_queries(
    *,
    use_ai: bool = False,
    user_enabled: bool = False,
    user_triggered: bool = False,
) -> dict[str, Any]:
    profile, resume_text, warnings = load_search_inputs()
    search_profile = build_search_profile(profile, resume_text)
    api_metadata: dict[str, Any] = {"api_used": False, "api_action": "generate_job_search_queries", "provider": "rule_based"}
    if use_ai:
        ai_result = generate_ai_queries(
            profile,
            resume_text,
            user_enabled=user_enabled,
            user_triggered=user_triggered,
        )
        queries = list(ai_result.get("queries") or [])
        warnings = warnings + list(ai_result.get("warnings") or [])
        api_metadata.update({key: value for key, value in ai_result.items() if key != "queries" and key != "warnings"})
    else:
        queries = generate_rule_based_queries(profile, resume_text)
    return {
        "search_profile": search_profile,
        "queries": queries,
        "default_queries": generate_rule_based_queries({}, "")[:8],
        "warnings": warnings,
        **api_metadata,
    }


def run_discovery(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    source_types = list(payload.get("source_types") or [])
    source_urls = list(payload.get("source_urls") or [])
    manual_links = list(payload.get("manual_links") or [])
    queries = list(payload.get("queries") or [])
    location = str(payload.get("location") or "Bay Area")
    max_jobs = int(payload.get("max_jobs") or 50)
    profile, resume_text, profile_warnings = load_search_inputs()
    search_profile = build_search_profile(profile, resume_text)
    _apply_fit_filters(search_profile, payload)
    if not queries:
        queries = generate_rule_based_queries(profile, resume_text)[:8]

    run = JobDiscoveryRun(
        source_type=",".join(source_types) or "manual",
        query=" | ".join(queries[:6]),
        location=location,
        status="running",
        errors=[],
        metadata_json={
            "source_urls": source_urls,
            "manual_links_count": len(manual_links),
            "profile_warnings": profile_warnings,
            "match_mode": search_profile.get("match_mode"),
            "target_experience_levels": search_profile.get("target_experience_levels"),
            "excluded_experience_levels": search_profile.get("excluded_experience_levels"),
            "degree_filter": search_profile.get("degree_filter"),
            "location_filter": search_profile.get("location_filter"),
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    errors: list[str] = []
    source_results: list[dict[str, Any]] = []
    raw_candidates: list[dict[str, Any]] = []
    urls_to_fetch = [url for url in source_urls if url.strip()] + [url for url in manual_links if url.strip()]
    if not urls_to_fetch and not any(source in {"web_search", "github_company_list"} for source in source_types):
        errors.append(NO_SOURCE_MESSAGE)
        source_results.append(_source_result("", "none"))
        _mark_source_error(source_results[-1], "No source URLs or manual links were provided.")

    for url in urls_to_fetch:
        source_type = _source_for_url(url, source_types)
        result = _source_result(url, source_type)
        source_results.append(result)
        if source_type not in source_types:
            _mark_source_warning(result, f"Source type inferred from URL as {source_type}.")
        for query in queries[:8]:
            if len(raw_candidates) >= max_jobs:
                break
            try:
                discovered = _discover_for_source(source_type, url, query, location)
                result["found"] += len(discovered)
                result["jobs_fetched"] += len(discovered)
                for candidate in discovered:
                    candidate["_source_url"] = url
                    if source_type not in source_types:
                        candidate["_source_warning"] = "Source type inferred from URL."
                raw_candidates.extend(discovered)
            except Exception as exc:
                message = f"{source_type} source failed for {url}: {exc}"
                errors.append(message)
                _mark_source_error(result, str(exc))
        if result["found"] == 0 and not result["errors"]:
            _mark_source_warning(
                result,
                "The source returned no postings for the current queries, blocked simple fetches, or requires browser rendering.",
            )

    for source_type in source_types:
        if source_type in PLACEHOLDER_SOURCES:
            try:
                _discover_for_source(source_type, "", queries[0] if queries else "", location)
            except Exception as exc:
                message = WEB_SEARCH_UNCONFIGURED_MESSAGE if source_type == "web_search" else str(exc)
                errors.append(message)
                result = _source_result("", source_type)
                _mark_source_error(result, message)
                source_results.append(result)

    saved: list[JobCandidate] = []
    seen_keys: set[str] = set()
    for candidate in raw_candidates[:max_jobs]:
        payload_data = _candidate_payload(
            candidate,
            run,
            search_profile,
            db,
            {"base_url": candidate.get("_source_url"), "source_type": candidate.get("source_type"), "name": candidate.get("source_name")},
        )
        if payload_data["duplicate_key"] in seen_keys:
            payload_data["filter_status"] = "duplicate"
            payload_data["filter_reasons"] = list(payload_data["filter_reasons"]) + ["Duplicate within this discovery run."]
        seen_keys.add(payload_data["duplicate_key"])
        source_url = str(candidate.get("_source_url") or "")
        matching_result = None
        for result in source_results:
            if result.get("source_url") == source_url:
                matching_result = result
                break
        if payload_data["filter_status"] == "incomplete":
            if matching_result is not None:
                _count_result_status(matching_result, "incomplete")
                _mark_source_warning(matching_result, "Skipped incomplete candidate because title/description or URL was missing.")
            continue
        db_candidate = _save_candidate(db, payload_data, matching_result)
        saved.append(db_candidate)

    run.status = "completed" if not errors else "completed_with_errors"
    run.completed_at = _now()
    run.total_found = len(raw_candidates)
    run.total_candidates = len(saved)
    run.errors = errors
    db.commit()
    db.refresh(run)
    for candidate in saved:
        db.refresh(candidate)

    if not saved and not errors:
        errors.append("No candidates were saved. The sources may have returned no matching postings, all postings may have been filtered out, or the pages may require browser rendering.")
    message = (
        NO_SOURCE_MESSAGE
        if not urls_to_fetch and not any(source in {"web_search", "github_company_list"} for source in source_types)
        else f"Discovery run #{run.id} completed with {len(saved)} candidate{'s' if len(saved) != 1 else ''}."
    )
    return {
        "run": run,
        "candidates": saved,
        "summary": summarize_candidates(saved),
        "source_results": source_results,
        "message": message,
        "errors": errors,
    }


def summarize_candidates(candidates: list[JobCandidate]) -> dict[str, int]:
    counts = {
        "total": len(candidates),
        "total_candidates": len(candidates),
        "good_match": 0,
        "weak_match": 0,
        "excluded": 0,
        "duplicate": 0,
        "duplicates": 0,
        "incomplete": 0,
        "skipped_incomplete": 0,
        "imported": 0,
        "candidate": 0,
    }
    for candidate in candidates:
        if candidate.filter_status in counts:
            counts[candidate.filter_status] += 1
        if candidate.filter_status == "duplicate":
            counts["duplicates"] += 1
    return counts


def _reviewable_candidate_query(db: Session, run_id: int):
    return (
        db.query(JobCandidate)
        .filter(JobCandidate.discovery_run_id == run_id)
        .filter(JobCandidate.filter_status.in_(("good_match", "candidate", "weak_match", "imported")))
    )


def get_run_candidate_page(db: Session, run_id: int, *, limit: int = 5, offset: int = 0) -> dict[str, Any] | None:
    run = get_run(db, run_id)
    if run is None:
        return None
    query = _reviewable_candidate_query(db, run_id)
    total_matches = query.count()
    candidates = (
        query.order_by(JobCandidate.relevance_score.desc(), JobCandidate.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    next_offset = offset + limit
    return {
        "success": True,
        "run_id": run_id,
        "limit": limit,
        "offset": offset,
        "next_offset": next_offset if next_offset < total_matches else None,
        "has_more": next_offset < total_matches,
        "total_matches": total_matches,
        "candidates": candidates,
    }


def _saved_source_result(source: JobSource) -> dict[str, Any]:
    return {
        "source_id": source.id,
        "company": source.name,
        "ats_type": source.ats_type or source.source_type,
        "base_url": source.base_url,
        "status": "success",
        "jobs_fetched": 0,
        "matches": 0,
        "candidates_saved": 0,
        "good_match": 0,
        "weak_match": 0,
        "excluded": 0,
        "duplicate": 0,
        "duplicates": 0,
        "skipped_incomplete": 0,
        "warnings": [],
        "errors": [],
    }


def _source_type_for_saved_source(source: JobSource) -> str:
    return source.ats_type or source.source_type or _source_for_url(source.base_url, [])


def search_saved_sources(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    ats_types = [str(item).strip().lower() for item in payload.get("ats_types") or [] if str(item).strip()]
    source_ids = [int(item) for item in payload.get("source_ids") or []]
    limit = int(payload.get("limit") or 5)
    offset = int(payload.get("offset") or 0)
    max_sources = int(payload.get("max_sources") or 25)
    match_mode = str(payload.get("match_mode") or "balanced")
    location = str(payload.get("location") or "Bay Area")
    exclude_duplicates = bool(payload.get("exclude_duplicates", True))
    exclude_imported = bool(payload.get("exclude_imported", True))
    use_enabled_sources = bool(payload.get("use_enabled_sources", True))
    queries = list(payload.get("queries") or [])

    profile, resume_text, profile_warnings = load_search_inputs()
    search_profile = build_search_profile(profile, resume_text)
    _apply_fit_filters(search_profile, payload)
    if not queries:
        queries = generate_rule_based_queries(profile, resume_text)[:8]

    source_query = db.query(JobSource)
    if source_ids:
        source_query = source_query.filter(JobSource.id.in_(source_ids))
    if ats_types:
        source_query = source_query.filter(or_(JobSource.ats_type.in_(ats_types), JobSource.source_type.in_(ats_types)))
    if use_enabled_sources:
        source_query = source_query.filter(JobSource.enabled.is_(True))
    candidate_sources = source_query.order_by(JobSource.id.asc()).limit(200).all()
    sources = sorted(
        candidate_sources,
        key=lambda source: (
            SAVED_SOURCE_PRIORITY.get(_source_type_for_saved_source(source), 99),
            source.id,
        ),
    )[:max_sources]

    run = JobDiscoveryRun(
        source_type="saved_sources:" + (",".join(ats_types) if ats_types else "all"),
        query=" | ".join(queries[:6]),
        location=location,
        status="running",
        errors=[],
        metadata_json={
            "saved_source_ids": [source.id for source in sources],
            "ats_types": ats_types,
            "max_sources": max_sources,
            "match_mode": match_mode,
            "target_experience_levels": search_profile.get("target_experience_levels"),
            "excluded_experience_levels": search_profile.get("excluded_experience_levels"),
            "degree_filter": search_profile.get("degree_filter"),
            "location_filter": search_profile.get("location_filter"),
            "profile_warnings": profile_warnings,
            "source_database": True,
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    errors: list[str] = []
    source_results: list[dict[str, Any]] = []
    saved: list[JobCandidate] = []
    seen_keys: set[str] = set()
    total_fetched = 0
    exclusion_reasons: dict[str, int] = {}
    incomplete_reasons: dict[str, int] = {}
    duplicate_reasons: dict[str, int] = {}
    exclusion_buckets = {"experience": 0, "degree": 0, "location": 0, "role": 0, "low_confidence": 0, "other": 0}
    location_counts = {
        "bay_area": 0,
        "remote_us": 0,
        "unknown": 0,
        "non_bay_area_california": 0,
        "other_us": 0,
        "international": 0,
    }
    soft_excluded: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    hard_excluded_payloads: list[dict[str, Any]] = []

    if not sources:
        errors.append("No saved sources matched the selected filters. Import the source CSV/JSON or enable sources first.")

    for source in sources:
        source_type = _source_type_for_saved_source(source)
        result = _saved_source_result(source)
        source_results.append(result)
        try:
            discovered = _discover_for_source(source_type, source.base_url, "", "")
            result["jobs_fetched"] = len(discovered)
            total_fetched += len(discovered)
            source.last_checked_at = _now()
        except Exception as exc:
            message = f"{source_type} source failed for {source.base_url}: {exc}"
            errors.append(message)
            result["status"] = "error"
            result["errors"].append(str(exc))
            source.last_checked_at = _now()
            source.last_error = str(exc)
            continue

        if not discovered:
            result["status"] = "warning"
            if source_type == "workday":
                result["warnings"].append("Workday board did not expose job postings through the current connector.")
            else:
                result["warnings"].append("The source returned no public postings or requires browser rendering.")

        for candidate in discovered:
            candidate["_source_url"] = source.base_url
            candidate.setdefault("source_type", source_type)
            candidate.setdefault("source_name", source.name)
            payload_data = _candidate_payload(candidate, run, search_profile, db, source)
            location_fit = str(payload_data.get("location_fit") or "unknown")
            location_counts[location_fit] = location_counts.get(location_fit, 0) + 1
            if payload_data["duplicate_key"] in seen_keys:
                payload_data["filter_status"] = "duplicate"
                payload_data["filter_reasons"] = list(payload_data["filter_reasons"]) + ["Duplicate within this discovery run."]
            seen_keys.add(payload_data["duplicate_key"])

            status = payload_data["filter_status"]
            if status == "incomplete":
                result["skipped_incomplete"] += 1
                _record_reason(incomplete_reasons, list(payload_data.get("filter_reasons") or []), "Incomplete:")
                if source_type == "workday":
                    _mark_source_warning(result, "Skipped incomplete Workday result because a real job title and URL were not both available.")
                else:
                    _mark_source_warning(result, "Skipped incomplete candidate because title/description or URL was missing.")
                continue
            if status == "excluded":
                result["excluded"] += 1
                reasons = list(payload_data.get("filter_reasons") or [])
                _record_reason(exclusion_reasons, reasons, "Excluded:")
                category = _primary_exclusion_category(payload_data)
                exclusion_buckets[category] = exclusion_buckets.get(category, 0) + 1
                if _is_hard_excluded(payload_data) or not _would_show_in_broad(payload_data):
                    hard_excluded_payloads.append(payload_data)
                else:
                    soft_excluded.append((payload_data, result))
                continue
            if status == "duplicate":
                result["duplicate"] += 1
                result["duplicates"] += 1
                _record_reason(duplicate_reasons, list(payload_data.get("filter_reasons") or []), "Duplicate")
                if exclude_duplicates or (exclude_imported and payload_data.get("duplicate_of_job_id")):
                    continue

            db_candidate = _save_candidate(db, payload_data)
            saved.append(db_candidate)
            result["matches"] += 1
            result["candidates_saved"] += 1
            if status == "good_match":
                result["good_match"] += 1
            elif status == "weak_match":
                result["weak_match"] += 1

    near_match_fallback_used = False
    if not saved and total_fetched > 0 and soft_excluded:
        near_match_fallback_used = True
        fallback_limit = max(limit, 10)
        for payload_data, result in sorted(
            soft_excluded,
            key=lambda item: (float(item[0].get("relevance_score") or 0), str(item[0].get("title") or "")),
            reverse=True,
        )[:fallback_limit]:
            category = _primary_exclusion_category(payload_data)
            payload_data["filter_status"] = "weak_match"
            payload_data["filter_reasons"] = list(payload_data.get("filter_reasons") or []) + [
                "Included as a near match because no stronger matches were found."
            ]
            raw_data = dict(payload_data.get("raw_data") or {})
            diagnostics = dict(raw_data.get("filter_diagnostics") or {})
            diagnostics["near_match_fallback"] = True
            diagnostics["primary_exclusion_category"] = None
            diagnostics["hard_excluded"] = False
            diagnostics["would_show_in_broad"] = True
            raw_data["filter_diagnostics"] = diagnostics
            payload_data["raw_data"] = raw_data
            db_candidate = _save_candidate(db, payload_data)
            saved.append(db_candidate)
            if result is not None:
                result["excluded"] = max(0, int(result.get("excluded", 0)) - 1)
                result["matches"] += 1
                result["candidates_saved"] += 1
                result["weak_match"] += 1
            exclusion_buckets[category] = max(0, exclusion_buckets.get(category, 0) - 1)

    run.status = "completed" if not errors else "completed_with_errors"
    run.completed_at = _now()
    run.total_found = total_fetched
    run.total_candidates = len(saved)
    run.errors = errors
    db.commit()
    db.refresh(run)
    for candidate in saved:
        db.refresh(candidate)

    page = get_run_candidate_page(db, run.id, limit=limit, offset=offset)
    saved_summary = summarize_candidates(saved)
    summary = {
        **saved_summary,
        "sources_checked": len(sources),
        "jobs_fetched": total_fetched,
        "matches": len(saved),
        "excluded": sum(int(result.get("excluded", 0)) for result in source_results),
        "duplicates": sum(int(result.get("duplicates", 0)) for result in source_results),
        "duplicate": sum(int(result.get("duplicates", 0)) for result in source_results),
        "incomplete": sum(int(result.get("skipped_incomplete", 0)) for result in source_results),
        "skipped_incomplete": sum(int(result.get("skipped_incomplete", 0)) for result in source_results),
    }
    diagnostics = {
        "match_mode": match_mode,
        "sources_checked": len(sources),
        "jobs_fetched": total_fetched,
        "jobs_excluded": summary["excluded"],
        "duplicates": summary["duplicates"],
        "incomplete": summary["skipped_incomplete"],
        "excluded_by_experience": exclusion_buckets["experience"],
        "excluded_by_degree": exclusion_buckets["degree"],
        "excluded_by_location": exclusion_buckets["location"],
        "excluded_by_role": exclusion_buckets["role"],
        "excluded_by_low_confidence": exclusion_buckets["low_confidence"],
        "excluded_other": exclusion_buckets["other"],
        "bay_area_found": location_counts["bay_area"],
        "remote_us_found": location_counts["remote_us"],
        "unknown_location_found": location_counts["unknown"],
        "non_bay_area_california_found": location_counts["non_bay_area_california"],
        "other_us_found": location_counts["other_us"],
        "international_found": location_counts["international"],
        "top_exclusion_reasons": _top_reasons(exclusion_reasons),
        "top_incomplete_reasons": _top_reasons(incomplete_reasons),
        "top_duplicate_reasons": _top_reasons(duplicate_reasons),
        "source_order": [source.ats_type or source.source_type for source in sources],
        "near_match_fallback_used": near_match_fallback_used,
        "zero_result_diagnostics": {
            "sample_excluded": _sample_excluded(
                sorted(
                    hard_excluded_payloads or [item[0] for item in soft_excluded],
                    key=lambda item: float(item.get("relevance_score") or 0),
                    reverse=True,
                )
            )
            if not saved
            else []
        },
        "suggestions": [
            "Many jobs were outside your selected locations. Try US-wide or Any location.",
            "Many jobs had unknown location. Keep Unknown location selected to review them.",
            "Include Mid-Level stretch roles.",
            "Include unknown experience.",
            "Include Master's required if you want graduate-degree roles.",
            "Switch to Broad Match if Balanced Match returns no reviewable jobs.",
            "Increase max sources or search all enabled sources.",
            "Search Greenhouse or Lever first for richer metadata.",
        ],
    }
    return {
        **(page or {"success": True, "run_id": run.id, "limit": limit, "offset": offset, "next_offset": None, "has_more": False, "total_matches": 0, "candidates": []}),
        "summary": summary,
        "source_results": source_results,
        "diagnostics": diagnostics,
    }


def list_runs(db: Session) -> list[JobDiscoveryRun]:
    return db.query(JobDiscoveryRun).order_by(JobDiscoveryRun.started_at.desc(), JobDiscoveryRun.id.desc()).limit(50).all()


def get_run(db: Session, run_id: int) -> JobDiscoveryRun | None:
    return db.query(JobDiscoveryRun).filter(JobDiscoveryRun.id == run_id).first()


def list_candidates(
    db: Session,
    *,
    run_id: int | None = None,
    filter_status: str | None = None,
    source_type: str | None = None,
    search: str | None = None,
    min_relevance_score: float | None = None,
) -> list[JobCandidate]:
    query = db.query(JobCandidate)
    if run_id:
        query = query.filter(JobCandidate.discovery_run_id == run_id)
    if filter_status:
        query = query.filter(JobCandidate.filter_status == filter_status)
    if source_type:
        query = query.filter(JobCandidate.source_type == source_type)
    if min_relevance_score is not None:
        query = query.filter(JobCandidate.relevance_score >= min_relevance_score)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(JobCandidate.company.ilike(term), JobCandidate.title.ilike(term), JobCandidate.location.ilike(term)))
    return query.order_by(JobCandidate.relevance_score.desc(), JobCandidate.id.desc()).limit(200).all()


def _candidate_description_for_import(candidate: JobCandidate) -> str:
    primary = str(candidate.job_description or "").strip()
    if primary:
        return primary

    raw_data = candidate.raw_data or {}
    for key in ("job_description", "description", "descriptionPlain", "descriptionHtml"):
        value = raw_data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    raw_source = raw_data.get("source_raw") or raw_data.get("raw_job") or {}
    if isinstance(raw_source, dict):
        for key in ("job_description", "description", "descriptionPlain", "descriptionHtml"):
            value = raw_source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return str(candidate.description_snippet or "").strip()


def import_candidate(db: Session, candidate_id: int, *, auto_verify: bool = True, auto_score: bool = True) -> dict[str, Any]:
    candidate = db.query(JobCandidate).filter(JobCandidate.id == candidate_id).first()
    if candidate is None:
        raise ValueError(f"Candidate {candidate_id} was not found.")
    if candidate.imported_job_id:
        raise ValueError(f"Candidate {candidate_id} was already imported as job {candidate.imported_job_id}.")
    if candidate.filter_status == "duplicate" and candidate.duplicate_of_job_id:
        raise ValueError(f"Candidate {candidate_id} duplicates existing job {candidate.duplicate_of_job_id}.")
    if candidate.filter_status in {"excluded", "incomplete"}:
        raise ValueError(f"Candidate {candidate_id} is {candidate.filter_status} and cannot be imported.")

    job_payload = {
        "company": candidate.company,
        "title": candidate.title,
        "location": candidate.location,
        "url": candidate.url,
        "source": f"job_finder:{candidate.source_type}",
        "job_description": _candidate_description_for_import(candidate),
        "role_category": candidate.role_category,
        "seniority_level": candidate.seniority_level,
        "remote_status": candidate.remote_status,
        "required_skills": candidate.required_skills or [],
        "preferred_skills": candidate.preferred_skills or [],
        "years_experience_min": candidate.years_experience_min,
        "years_experience_max": candidate.years_experience_max,
        "salary_min": candidate.salary_min,
        "salary_max": candidate.salary_max,
        "salary_currency": candidate.salary_currency,
        "posted_date": candidate.posted_date,
        "raw_parsed_data": {
            "job_finder_candidate_id": candidate.id,
            "job_finder_raw_data": candidate.raw_data or {},
            "job_finder_match_reasons": candidate.filter_reasons or [],
            "job_finder_role_category": candidate.role_category,
            "job_finder_experience_level": candidate.experience_level,
            "job_finder_education_requirement": candidate.education_requirement,
        },
        "application_status": "saved",
    }
    job = create_job(db, job_payload)
    candidate.imported_job_id = job.id
    candidate.filter_status = "imported"
    run = get_run(db, candidate.discovery_run_id)
    if run:
        run.total_imported = (run.total_imported or 0) + 1
    db.commit()
    db.refresh(candidate)
    log_event(db, job_id=job.id, event_type="job_imported", notes="Imported from Job Finder candidate.", new_status=job.application_status, metadata_json={"candidate_id": candidate.id})
    log_event(db, job_id=job.id, event_type="job_saved", notes="Saved from Job Finder candidate.", new_status=job.application_status, metadata_json={"candidate_id": candidate.id})

    verified = False
    scored = False
    warnings: list[str] = []
    if auto_verify and job.url:
        try:
            result = verify_job_record(job)
            updated = update_job(db, job.id, build_job_verification_updates(job, result))
            if updated:
                job = updated
                verified = True
                log_event(
                    db,
                    job_id=job.id,
                    event_type="verification_completed",
                    notes=f"Auto-verified saved candidate: {job.verification_status}.",
                    old_status=job.application_status,
                    new_status=job.application_status,
                    metadata_json={
                        "candidate_id": candidate.id,
                        "verification_status": job.verification_status,
                        "verification_score": job.verification_score,
                    },
                )
                if job.verification_status in {"open", "probably_open"}:
                    promote_job_status_if_needed(db, job.id, "verified_open", notes="Promoted after Job Finder import verification.")
                    db.refresh(job)
        except Exception as exc:
            warnings.append(f"Auto-verify failed: {exc}")
    if auto_score:
        try:
            result = score_saved_job(job)
            updated = update_job(db, job.id, build_job_scoring_updates(result))
            if updated:
                job = updated
                scored = True
                log_event(
                    db,
                    job_id=job.id,
                    event_type="scoring_completed",
                    notes="Auto-scored saved candidate.",
                    old_status=job.application_status,
                    new_status=job.application_status,
                    metadata_json={
                        "candidate_id": candidate.id,
                        "resume_match_score": job.resume_match_score,
                        "overall_priority_score": job.overall_priority_score,
                    },
                )
        except Exception as exc:
            warnings.append(f"Auto-score failed: {exc}")
    return {"candidate": candidate, "job": job, "verified": verified, "scored": scored, "warnings": warnings}
