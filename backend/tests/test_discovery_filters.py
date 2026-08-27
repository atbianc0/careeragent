"""Coverage for the Job Finder discovery pipeline's relevance filtering
(app.services.job_finder.filters.filter_candidate), exercised through the
same normalize_raw_job() step run_discovery() uses so titles/descriptions
drive real role/experience/degree/location classification rather than
hand-set fields.
"""

import pytest

from app.services.job_finder.job_normalizer import normalize_raw_job
from app.services.job_finder.filters import filter_candidate

# Mirrors the defaults _apply_fit_filters() applies in discovery.py when a
# discovery request doesn't override fit filters.
DEFAULT_SEARCH_PROFILE = {
    "match_mode": "balanced",
    "target_experience_levels": ["new_grad_entry", "early_career", "unknown"],
    "excluded_experience_levels": ["senior"],
    "allow_unknown_location": True,
    "degree_filter": {
        "allow_no_degree": True,
        "allow_bachelors": True,
        "allow_masters_preferred": True,
        "allow_masters_required": False,
        "allow_phd_preferred": True,
        "allow_phd_required": False,
        "allow_unknown": True,
    },
    "location_filter": {
        "allow_bay_area": True,
        "allow_remote_us": True,
        "allow_unknown": True,
        "allow_non_bay_area_california": False,
        "allow_other_us": False,
        "allow_international": False,
    },
}


def _candidate(title: str, location: str, description: str = "Growing data team looking for a driven engineer.") -> dict:
    raw_job = {
        "title": title,
        "location": location,
        "job_description": description,
        "url": "https://boards.greenhouse.io/acme/jobs/1",
        "source_type": "greenhouse",
    }
    return normalize_raw_job(raw_job, {"name": "Acme"})


def _filter(title: str, location: str, description: str = "Growing data team looking for a driven engineer.") -> dict:
    return filter_candidate(_candidate(title, location, description), DEFAULT_SEARCH_PROFILE, match_mode="balanced")


KEEP_CASES = [
    pytest.param("New Grad Data Scientist", "San Francisco, CA", "Growing data team looking for a driven engineer.", id="bay_area_new_grad"),
    pytest.param("Entry Level Data Analyst", "San Francisco, CA", "Growing data team looking for a driven engineer.", id="bay_area_entry_level"),
    pytest.param("New Grad Machine Learning Engineer", "Remote - United States", "Growing data team looking for a driven engineer.", id="remote_us_new_grad"),
]


@pytest.mark.parametrize("title, location, description", KEEP_CASES)
def test_keeps_bay_area_and_remote_us_new_grad_roles(title, location, description):
    result = _filter(title, location, description)

    assert result["filter_status"] in {"good_match", "weak_match"}
    assert result["primary_exclusion_category"] is None


EXCLUDE_CASES = [
    pytest.param("Senior Data Scientist", "San Francisco, CA", "Growing data team looking for a driven engineer.", "experience", id="senior_title"),
    pytest.param("Staff Machine Learning Engineer", "San Francisco, CA", "Growing data team looking for a driven engineer.", "experience", id="staff_title"),
    pytest.param("Principal Data Engineer", "San Francisco, CA", "Growing data team looking for a driven engineer.", "experience", id="principal_title"),
    pytest.param("Data Science Manager", "San Francisco, CA", "Growing data team looking for a driven engineer.", "experience", id="manager_title"),
    pytest.param("Applied Scientist", "San Francisco, CA", "This role requires a Ph.D. in a relevant field.", "degree", id="phd_required"),
    pytest.param("Data Engineer", "San Francisco, CA", "Master's degree required for this role.", "degree", id="masters_required"),
    pytest.param(
        "Data Engineer",
        "San Francisco, CA",
        "8+ years of professional software engineering experience required.",
        "experience",
        id="high_years_required",
    ),
]


@pytest.mark.parametrize("title, location, description, expected_category", EXCLUDE_CASES)
def test_excludes_senior_and_advanced_degree_roles(title, location, description, expected_category):
    result = _filter(title, location, description)

    assert result["filter_status"] == "excluded"
    assert result["primary_exclusion_category"] == expected_category
