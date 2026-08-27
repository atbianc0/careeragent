"""Coverage for the Job Finder discovery pipeline's deduplication against
existing saved jobs (app.models.job.Job) and previously discovered
candidates (app.models.job_finder.JobCandidate)."""

from app.models.job import Job
from app.models.job_finder import JobCandidate, JobDiscoveryRun
from app.services.job_finder.dedupe import (
    duplicate_key_for_candidate,
    find_duplicate_candidate,
    find_duplicate_job,
)


def test_duplicate_key_matches_across_tracking_params_and_trailing_slash():
    key_with_tracking = duplicate_key_for_candidate(
        {"url": "https://boards.greenhouse.io/acme/jobs/123?utm_source=newsletter&gh_src=abc"}
    )
    key_bare = duplicate_key_for_candidate({"url": "https://BOARDS.greenhouse.io/acme/jobs/123/"})

    assert key_with_tracking == key_bare


def test_duplicate_key_falls_back_to_company_title_location_when_no_url():
    key_a = duplicate_key_for_candidate({"company": "Acme Inc.", "title": "Data Engineer", "location": "SF"})
    key_b = duplicate_key_for_candidate({"company": "acme inc", "title": "data engineer", "location": "sf"})
    key_different = duplicate_key_for_candidate({"company": "Acme Inc.", "title": "Data Scientist", "location": "SF"})

    assert key_a == key_b
    assert key_a != key_different


def test_find_duplicate_job_matches_saved_job_by_normalized_url(db_session):
    saved_job = Job(
        company="Acme",
        title="Data Engineer",
        location="San Francisco, CA",
        url="https://boards.greenhouse.io/acme/jobs/123",
        source="job_finder:greenhouse",
    )
    db_session.add(saved_job)
    db_session.commit()

    candidate = {"url": "https://boards.greenhouse.io/acme/jobs/123?utm_source=newsletter"}
    duplicate_key = duplicate_key_for_candidate(candidate)

    duplicate = find_duplicate_job(db_session, candidate, duplicate_key)

    assert duplicate is not None
    assert duplicate.id == saved_job.id


def test_find_duplicate_job_matches_saved_job_by_company_title_location_when_no_url(db_session):
    saved_job = Job(
        company="Acme",
        title="Data Engineer",
        location="San Francisco, CA",
        url="",
        source="job_finder:manual",
    )
    db_session.add(saved_job)
    db_session.commit()

    candidate = {"company": "acme", "title": "data engineer", "location": "san francisco, ca"}
    duplicate_key = duplicate_key_for_candidate(candidate)

    duplicate = find_duplicate_job(db_session, candidate, duplicate_key)

    assert duplicate is not None
    assert duplicate.id == saved_job.id


def test_find_duplicate_job_returns_none_when_no_saved_job_matches(db_session):
    db_session.add(
        Job(
            company="Acme",
            title="Data Engineer",
            location="San Francisco, CA",
            url="https://boards.greenhouse.io/acme/jobs/123",
            source="job_finder:greenhouse",
        )
    )
    db_session.commit()

    candidate = {"url": "https://boards.greenhouse.io/other-co/jobs/456", "company": "Other Co", "title": "Data Engineer", "location": "Remote"}
    duplicate_key = duplicate_key_for_candidate(candidate)

    assert find_duplicate_job(db_session, candidate, duplicate_key) is None


def test_find_duplicate_candidate_matches_existing_candidate_by_duplicate_key(db_session):
    run = JobDiscoveryRun(source_type="greenhouse")
    db_session.add(run)
    db_session.commit()

    candidate = {"url": "https://boards.greenhouse.io/acme/jobs/123"}
    duplicate_key = duplicate_key_for_candidate(candidate)

    existing_candidate = JobCandidate(
        discovery_run_id=run.id,
        source_type="greenhouse",
        company="Acme",
        title="Data Engineer",
        location="San Francisco, CA",
        url=candidate["url"],
        duplicate_key=duplicate_key,
    )
    db_session.add(existing_candidate)
    db_session.commit()

    duplicate = find_duplicate_candidate(db_session, duplicate_key)

    assert duplicate is not None
    assert duplicate.id == existing_candidate.id


def test_find_duplicate_candidate_returns_none_for_unseen_key(db_session):
    run = JobDiscoveryRun(source_type="greenhouse")
    db_session.add(run)
    db_session.commit()

    db_session.add(
        JobCandidate(
            discovery_run_id=run.id,
            source_type="greenhouse",
            company="Acme",
            title="Data Engineer",
            location="San Francisco, CA",
            url="https://boards.greenhouse.io/acme/jobs/123",
            duplicate_key=duplicate_key_for_candidate({"url": "https://boards.greenhouse.io/acme/jobs/123"}),
        )
    )
    db_session.commit()

    unseen_key = duplicate_key_for_candidate({"url": "https://boards.greenhouse.io/other-co/jobs/456"})

    assert find_duplicate_candidate(db_session, unseen_key) is None
