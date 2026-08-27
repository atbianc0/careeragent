"""Coverage for app.services.scoring.scoring: skill match, role match,
location match, freshness, verification-driven application ease, and the
overall priority ranking that blends them, against known profile/resume +
job fixtures."""

from datetime import date, timedelta

import pytest

from app.models import Job
from app.services.scoring import scoring


@pytest.fixture
def profile():
    return {
        "personal": {"location": "Remote"},
        "education": {
            "school": "State University",
            "degree": "B.S. Computer Science",
            "graduation": "2026",
        },
        "target_roles": ["Data Scientist", "Data Engineer"],
        "skills": ["Python", "SQL", "Pandas", "scikit-learn"],
        "application_defaults": {"preferred_locations": ["Remote"]},
    }


@pytest.fixture
def resume_text():
    return (
        "Experienced in Python, SQL, and Pandas for data analysis. "
        "B.S. Computer Science, graduating 2026."
    )


def make_job(**overrides) -> Job:
    defaults = dict(
        company="Acme",
        title="Data Scientist",
        location="Remote",
        url="https://example.com/jobs/1",
        source="test",
        job_description="We need a data scientist skilled in Python and SQL.",
        remote_status="remote",
        role_category="Data Scientist",
        seniority_level="entry level",
        required_skills=["Python", "SQL"],
        preferred_skills=["Pandas"],
        verification_status="verified",
        verification_score=90.0,
        posted_date=date.today(),
    )
    defaults.update(overrides)
    return Job(**defaults)


@pytest.fixture
def matching_job():
    return make_job()


class TestCalculateSkillMatchScore:
    def test_no_job_skills_returns_neutral_score(self):
        result = scoring.calculate_skill_match_score([], ["Python"])
        assert result["score"] == 55.0

    def test_full_required_match_scores_100(self):
        result = scoring.calculate_skill_match_score(["Python", "SQL"], ["Python", "SQL", "Docker"])
        assert result["score"] == 100.0
        assert result["missing_required_skills"] == []

    def test_partial_required_match(self):
        result = scoring.calculate_skill_match_score(["Python", "SQL", "Java"], ["Python"])
        assert result["score"] == pytest.approx(round(100 / 3, 2))
        assert result["matched_required_skills"] == ["Python"]
        assert result["missing_required_skills"] == ["SQL", "Java"]

    def test_required_and_preferred_are_weighted_80_20(self):
        result = scoring.calculate_skill_match_score(
            ["Python"], ["Python", "Docker"], preferred_job_skills=["Docker", "AWS"]
        )
        assert result["score"] == 90.0

    def test_skill_aliases_are_canonicalized_before_matching(self):
        result = scoring.calculate_skill_match_score(["js"], ["JavaScript"])
        assert result["matched_required_skills"] == ["JavaScript"]
        assert result["score"] == 100.0


class TestCalculateRoleMatchScore:
    def test_no_target_roles_returns_neutral(self):
        result = scoring.calculate_role_match_score("Data Scientist", [], "Data Scientist")
        assert result["score"] == 60.0

    def test_exact_role_match_scores_highest(self):
        result = scoring.calculate_role_match_score("Data Scientist", ["Data Scientist"], "Data Scientist")
        assert result["score"] == 95.0

    def test_title_keyword_match(self):
        # job_role alone doesn't canonicalize to a target, but the job_title
        # separately contains a target role's keyword.
        result = scoring.calculate_role_match_score(
            "Research Scientist", ["Data Scientist"], "Research Scientist, Data Scientist track"
        )
        assert result["score"] == 90.0

    def test_same_role_family_match(self):
        result = scoring.calculate_role_match_score("Data Engineer", ["Data Scientist"], "Data Engineer")
        assert result["score"] == 80.0

    def test_software_engineer_with_data_keywords_scores_moderately(self):
        result = scoring.calculate_role_match_score(
            "Software Engineer",
            ["Data Scientist"],
            "Software Engineer",
            job_description="Build our machine learning platform.",
        )
        assert result["score"] == 65.0

    def test_unrelated_role_scores_low(self):
        result = scoring.calculate_role_match_score("Sales", ["Data Scientist"], "Account Executive")
        assert result["score"] == 40.0


class TestCalculateLocationScore:
    def test_no_preferences_returns_neutral(self):
        result = scoring.calculate_location_score("San Francisco, CA", "onsite", [])
        assert result["score"] == 50.0

    def test_remote_job_matches_remote_preference(self):
        result = scoring.calculate_location_score("Remote", "remote", ["Remote"])
        assert result["score"] == 100.0

    def test_unknown_location_returns_neutral(self):
        result = scoring.calculate_location_score("Unknown", "onsite", ["Remote"])
        assert result["score"] == 50.0

    def test_exact_location_match(self):
        result = scoring.calculate_location_score("Austin, TX", "onsite", ["Austin, TX"])
        assert result["score"] == 100.0

    def test_bay_area_preference_onsite(self):
        result = scoring.calculate_location_score("San Francisco, CA", "onsite", ["Bay Area"])
        assert result["score"] == 80.0

    def test_bay_area_preference_hybrid_scores_lower(self):
        result = scoring.calculate_location_score("Oakland, CA", "hybrid", ["Bay Area"])
        assert result["score"] == 75.0

    def test_california_preference(self):
        result = scoring.calculate_location_score("Sacramento, CA", "onsite", ["California"])
        assert result["score"] == 80.0

    def test_non_matching_location_scores_low(self):
        result = scoring.calculate_location_score("New York, NY", "onsite", ["Remote"])
        assert result["score"] == 40.0


class TestFreshnessScore:
    @pytest.mark.parametrize(
        "days_old, expected",
        [
            (0, 100.0),
            (7, 100.0),
            (8, 90.0),
            (14, 90.0),
            (15, 75.0),
            (30, 75.0),
            (31, 55.0),
            (60, 55.0),
            (61, 35.0),
            (90, 35.0),
            (91, 20.0),
        ],
    )
    def test_freshness_score_value_buckets_by_age(self, days_old, expected):
        posted = date.today() - timedelta(days=days_old)
        assert scoring.freshness_score_value(posted) == expected

    def test_unknown_age_returns_neutral(self):
        assert scoring.freshness_score_value(None) == 50.0

    def test_falls_back_to_first_seen_date_when_posted_missing(self):
        first_seen = date.today() - timedelta(days=5)
        result = scoring.calculate_freshness_score(None, first_seen)
        assert result["score"] == 100.0
        assert result["age_source"] == "first_seen_date"

    def test_old_job_evidence_mentions_age(self):
        result = scoring.calculate_freshness_score(date.today() - timedelta(days=100))
        assert result["score"] == 20.0
        assert "quite old" in result["evidence"][0]


class TestCalculateApplicationEaseScore:
    def test_missing_url_scores_low(self):
        job = make_job(url="", verification_status="verified")
        assert scoring.calculate_application_ease_score(job)["score"] == 35.0

    def test_closed_status_scores_lowest(self):
        job = make_job(verification_status="closed")
        assert scoring.calculate_application_ease_score(job)["score"] == 20.0

    def test_likely_closed_status_scores_lowest(self):
        job = make_job(verification_status="likely_closed")
        assert scoring.calculate_application_ease_score(job)["score"] == 20.0

    def test_possibly_closed_status_scores_moderate(self):
        job = make_job(verification_status="possibly_closed")
        assert scoring.calculate_application_ease_score(job)["score"] == 40.0

    def test_unknown_status_scores_moderate(self):
        job = make_job(verification_status="unknown")
        assert scoring.calculate_application_ease_score(job)["score"] == 55.0

    def test_verified_status_scores_highest(self):
        job = make_job(verification_status="verified")
        assert scoring.calculate_application_ease_score(job)["score"] == 70.0


class TestCalculateResumeMatchScore:
    def test_weights_components_45_25_15_15(self):
        components = {
            "skill_match_score": 100,
            "role_match_score": 80,
            "experience_fit_score": 60,
            "profile_keyword_score": 40,
        }
        expected = round(0.45 * 100 + 0.25 * 80 + 0.15 * 60 + 0.15 * 40, 2)
        assert scoring.calculate_resume_match_score(components) == expected

    def test_missing_components_default_to_zero(self):
        assert scoring.calculate_resume_match_score({}) == 0.0


class TestPriorityAndOverallScore:
    def test_calculate_priority_score_weights_components(self):
        score = scoring.calculate_priority_score(
            resume_match_score=80,
            verification_score=60,
            freshness_score=100,
            location_score=50,
            application_ease_score=70,
        )
        expected = round(0.40 * 80 + 0.25 * 60 + 0.20 * 100 + 0.10 * 50 + 0.05 * 70, 2)
        assert score == expected

    def test_overall_priority_score_pulls_from_component_dict(self):
        components = {
            "resume_match_score": 80,
            "verification_score": 60,
            "freshness_score": 100,
            "location_score": 50,
            "application_ease_score": 70,
        }
        assert scoring.calculate_overall_priority_score(components) == scoring.calculate_priority_score(
            resume_match_score=80,
            verification_score=60,
            freshness_score=100,
            location_score=50,
            application_ease_score=70,
        )

    def test_overall_priority_score_defaults_missing_components(self):
        result = scoring.calculate_overall_priority_score({})
        expected = scoring.calculate_priority_score(
            resume_match_score=0.0,
            verification_score=0.0,
            freshness_score=50.0,
            location_score=50.0,
            application_ease_score=50.0,
        )
        assert result == expected

    def test_higher_verification_score_increases_priority(self):
        low = scoring.calculate_priority_score(
            resume_match_score=70, verification_score=0, freshness_score=70, location_score=70, application_ease_score=70
        )
        high = scoring.calculate_priority_score(
            resume_match_score=70, verification_score=100, freshness_score=70, location_score=70, application_ease_score=70
        )
        assert high > low


class TestScoreJobAgainstProfile:
    def test_full_pipeline_is_internally_consistent(self, profile, resume_text, matching_job):
        result = scoring.score_job_against_profile(matching_job, profile, resume_text)

        assert result["scoring_status"] == "scored"
        assert 0.0 <= result["overall_priority_score"] <= 100.0
        assert result["resume_match_score"] == scoring.calculate_resume_match_score(
            {
                "skill_match_score": result["skill_match_score"],
                "role_match_score": result["role_match_score"],
                "experience_fit_score": result["experience_fit_score"],
                "profile_keyword_score": result["profile_keyword_score"],
            }
        )
        assert result["overall_priority_score"] == scoring.calculate_overall_priority_score(
            {
                "resume_match_score": result["resume_match_score"],
                "verification_score": result["verification_score"],
                "freshness_score": result["freshness_score"],
                "location_score": result["location_score"],
                "application_ease_score": result["application_ease_score"],
            }
        )
        assert "Python" in result["scoring_raw_data"]["matched_required_skills"]

    def test_strong_fit_outranks_poor_fit(self, profile, resume_text, matching_job):
        poor_fit_job = make_job(
            title="Senior Backend Software Engineer",
            role_category="Software Engineer",
            job_description="Build backend services in Go and Kubernetes.",
            required_skills=["Go", "Kubernetes"],
            preferred_skills=[],
            location="New York, NY",
            remote_status="onsite",
            seniority_level="senior",
            years_experience_min=6,
            verification_status="possibly_closed",
            verification_score=20.0,
            posted_date=date.today() - timedelta(days=100),
        )

        poor_result = scoring.score_job_against_profile(poor_fit_job, profile, resume_text)
        strong_result = scoring.score_job_against_profile(matching_job, profile, resume_text)

        assert poor_result["overall_priority_score"] < strong_result["overall_priority_score"]

    def test_missing_required_skills_are_reported(self, profile, resume_text):
        job = make_job(required_skills=["Go", "Kubernetes"], preferred_skills=[])
        result = scoring.score_job_against_profile(job, profile, resume_text)
        assert "Go" in result["scoring_raw_data"]["missing_required_skills"]
        assert "Kubernetes" in result["scoring_raw_data"]["missing_required_skills"]


class TestKeywordExtraction:
    def test_extract_profile_keywords_canonicalizes_skills_and_roles(self, profile):
        result = scoring.extract_profile_keywords(profile)
        assert result["skills"] == ["Python", "SQL", "Pandas", "scikit-learn"]
        assert result["target_roles"] == ["Data Scientist", "Data Engineer"]

    def test_extract_resume_keywords_detects_skills(self, resume_text):
        result = scoring.extract_resume_keywords(resume_text)
        assert "Python" in result["skills"]
        assert "SQL" in result["skills"]
        assert "Pandas" in result["skills"]
