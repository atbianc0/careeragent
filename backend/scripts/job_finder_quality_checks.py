from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.job_finder.filters import build_candidate_match_reasons, filter_candidate
from app.services.job_finder.level_classifier import classify_experience_level
from app.services.job_finder.location_classifier import classify_location_fit
from app.services.job_finder.role_classifier import classify_role_category


def assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def main() -> None:
    level_cases = [
        ("Software Engineer, New College Grad", "", "new_grad_entry"),
        ("Data Scientist Intern", "", "intern"),
        ("Senior Machine Learning Engineer", "", "advanced_senior"),
        ("Data Engineer", "3+ years experience", "mid_level"),
        ("Machine Learning Engineer", "0-2 years", "new_grad_entry"),
    ]
    for title, description, expected in level_cases:
        result = classify_experience_level(title, description)
        assert_equal(result["experience_level"], expected, f"level {title}")

    location_cases = [
        ("Foster City, CA", "bay_area"),
        ("Santa Clara, CA, US", "bay_area"),
        ("Remote - United States", "remote_us"),
        ("Remote (Poland)", "outside_target"),
        ("New York, NY", "outside_target"),
        ("Canada", "outside_target"),
        ("Unknown", "unknown"),
    ]
    for location, expected in location_cases:
        result = classify_location_fit(location, "")
        assert_equal(result["location_fit"], expected, f"location {location}")

    candidate = {
        "title": "Machine Learning Engineer",
        "location": "",
        "job_description": "Build models with Python and SQL.",
        "role_category": classify_role_category("Machine Learning Engineer")["role_category"],
        "experience_level": "unknown",
        "location_fit": "unknown",
        "metadata_confidence": 70,
        "missing_fields": ["location"],
        "raw_data": {
            "normalizer": {
                "role": classify_role_category("Machine Learning Engineer"),
                "level": classify_experience_level("Machine Learning Engineer", ""),
                "location": classify_location_fit("", ""),
            }
        },
    }
    profile = {"skills": ["r", "Python", "SQL"]}
    reasons = build_candidate_match_reasons(candidate, profile)
    if "Skills overlap: r" in " ".join(reasons):
        raise AssertionError("reason builder included one-letter skill r")
    if any(reason.startswith("Good match") for reason in reasons):
        raise AssertionError("weak reasons should not say Good match")
    if not any("Location is missing" in reason or "Missing location" in reason for reason in reasons):
        raise AssertionError("missing location reason not present")
    filtered = filter_candidate(candidate, profile)
    assert_equal(filtered["filter_status"], "weak_match", "weak candidate status")

    off_target = {
        "title": "Application Security Engineer",
        "location": "Remote (Poland)",
        "job_description": "Build secure services with Python and SQL.",
        "role_category": "Other",
        "experience_level": "mid_level",
        "location_fit": "outside_target",
        "metadata_confidence": 90,
        "missing_fields": [],
        "raw_data": {
            "normalizer": {
                "role": classify_role_category("Application Security Engineer", "Build secure services with Python and SQL."),
                "level": classify_experience_level("Application Security Engineer", "3+ years experience"),
                "location": classify_location_fit("Remote (Poland)", ""),
            }
        },
    }
    filtered_off_target = filter_candidate(off_target, profile)
    assert_equal(filtered_off_target["filter_status"], "excluded", "off-target role status")
    print("Job Finder quality checks passed.")


if __name__ == "__main__":
    main()
