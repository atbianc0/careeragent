"""Coverage for the rule-based job parser's text-based entry point
(`parse_job_description`) and its pure helper functions.

These are characterization tests: they pin down what the parser actually
does today, including a few sharp-edged quirks (noted inline) that are not
necessarily "correct" but must not change silently. A future ticket may
decide to fix these; this ticket only makes them visible.
"""

import pytest

from app.services.jobs.parser import (
    _format_company_from_host,
    _get_non_empty_lines,
    _infer_location,
    clean_workday_location,
    clean_workday_title,
    extract_application_questions,
    extract_salary,
    extract_skills,
    extract_years_experience,
    infer_remote_status,
    infer_role_category,
    infer_seniority,
    is_workday_url,
    parse_job_description,
    parse_workday_url_slug,
)

FREEFORM_JOB_TEXT = """Data Engineer at Northwind Analytics

Austin, TX

Salary range: $130,000 - $160,000 USD

What You'll Do:
- Build and maintain ETL pipelines for the analytics warehouse
- Own data quality checks across ingestion pipelines
- Collaborate with analysts on reporting pipelines

Minimum Qualifications:
- 3-5 years of experience with SQL and Python
- Experience with Airflow and dbt
- Familiarity with AWS and Snowflake

Nice to Have:
- Experience with Spark or Databricks
- Exposure to Kubernetes

Education requirements:
Bachelor's degree in Computer Science or related field.
"""


def test_parse_job_description_infers_core_fields_from_freeform_text():
    result = parse_job_description(FREEFORM_JOB_TEXT)

    assert result["company"] == "Northwind Analytics"
    assert result["title"] == "Data Engineer at Northwind Analytics"
    # Quirk: the location regex's `\s+` matches across blank lines, so it
    # greedily spans from the first capitalized word in the text through
    # the real "City, ST" match instead of stopping at line boundaries.
    assert result["location"] == "Northwind Analytics\n\nAustin, TX"
    assert result["remote_status"] == "Unknown"
    assert result["employment_type"] is None
    assert result["role_category"] == "Data Engineer"
    assert result["seniority_level"] == "Mid Level"
    assert result["years_experience_min"] == 3
    assert result["years_experience_max"] == 5
    assert result["salary_min"] == 130000.0
    assert result["salary_max"] == 160000.0
    assert result["salary_currency"] == "USD"
    assert result["required_skills"] == [
        "Python",
        "SQL",
        "Airflow",
        "dbt",
        "AWS",
        "Snowflake",
        "analytics",
        "ETL",
    ]
    assert result["preferred_skills"] == ["Spark", "Databricks", "Kubernetes"]
    assert result["responsibilities"] == [
        "Build and maintain ETL pipelines for the analytics warehouse",
        "Own data quality checks across ingestion pipelines",
        "Collaborate with analysts on reporting pipelines",
    ]
    assert result["requirements"] == [
        "3-5 years of experience with SQL and Python",
        "Experience with Airflow and dbt",
        "Familiarity with AWS and Snowflake",
    ]
    assert result["education_requirements"] == [
        "Bachelor's degree in Computer Science or related field."
    ]
    assert result["application_questions"] == []
    assert result["source"] == "manual"
    assert result["parsing_status"] == "full"
    assert result["parse_mode"] == "rule_based"
    assert result["parsing_warnings"] == []


def test_parse_job_description_empty_text_raises():
    with pytest.raises(ValueError, match="Job content is empty"):
        parse_job_description("   ")


@pytest.mark.parametrize(
    ("title", "description", "expected"),
    [
        ("Summer Intern", "Join us as a summer intern", "Internship"),
        ("New Grad Software Engineer", "For recent graduates", "New Grad"),
        ("Junior Analyst", "entry-level role", "Entry Level"),
        ("Senior Engineer", "seasoned professional", "Senior"),
        ("Software Engineer", "You should have 4+ years of experience.", "Mid Level"),
        ("Software Engineer", "Join our team.", "Unknown"),
    ],
)
def test_infer_seniority_buckets(title, description, expected):
    assert infer_seniority(title, description) == expected


def test_infer_seniority_prioritizes_title_over_body_mentions():
    # Regression: mentioning "junior" elsewhere in the text (e.g. a
    # *junior colleague* being mentored) must not override an explicitly
    # Senior-titled posting. The title is checked first and is
    # unambiguous, so it wins over the incidental body-text keyword.
    result = infer_seniority(
        "Senior Data Scientist",
        "You will mentor junior data scientists on the team.",
    )
    assert result == "Senior"


def test_infer_seniority_falls_back_to_body_when_title_inconclusive():
    # When the title itself gives no seniority signal, body-text keywords
    # still apply as a fallback.
    result = infer_seniority(
        "Data Scientist",
        "This role is entry level and great for early-career candidates.",
    )
    assert result == "Entry Level"


def test_infer_role_category_prioritizes_title_over_body_mentions():
    # Regression: a "Data Engineer" role that merely mentions "data
    # scientists" in a responsibility bullet must not be miscategorized,
    # even though "data scientist" is a substring of "data scientists" and
    # is checked first in the rule list. The title is checked in isolation
    # first, so the unambiguous "Data Engineer" title wins.
    clean = infer_role_category("Data Engineer", "Build ETL pipelines.")
    collided = infer_role_category(
        "Data Engineer",
        "You will collaborate with data scientists on feature pipelines.",
    )
    assert clean == "Data Engineer"
    assert collided == "Data Engineer"


def test_infer_role_category_falls_back_to_body_when_title_inconclusive():
    # When the title itself gives no role-category signal, body-text
    # keywords still apply as a fallback.
    result = infer_role_category(
        "Team Member",
        "You will build and maintain ETL pipelines as a data engineer.",
    )
    assert result == "Data Engineer"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("This is a fully remote position.", "Remote"),
        ("This is a hybrid role, 3 days in office.", "Hybrid"),
        ("This is an on-site position in our HQ.", "Onsite"),
        ("Join our growing team.", "Unknown"),
    ],
)
def test_infer_remote_status(text, expected):
    assert infer_remote_status(text) == expected


@pytest.mark.parametrize(
    ("text", "expected_min", "expected_max"),
    [
        ("You should have 3-5 years of experience.", 3, 5),
        ("At least 4 years of experience required.", 4, 4),
        ("6+ years of professional experience.", 6, 6),
        ("No specific experience requirement listed.", None, None),
    ],
)
def test_extract_years_experience(text, expected_min, expected_max):
    result = extract_years_experience(text)
    assert result["years_experience_min"] == expected_min
    assert result["years_experience_max"] == expected_max


def test_extract_salary_plain_dollar_range():
    result = extract_salary("The salary for this role is $120,000 - $150,000.")
    assert result == {
        "salary_min": 120000.0,
        "salary_max": 150000.0,
        "salary_currency": "USD",
    }


def test_extract_salary_k_suffix_with_currency():
    result = extract_salary("Pay band: 120k-150k USD")
    assert result == {
        "salary_min": 120000.0,
        "salary_max": 150000.0,
        "salary_currency": "USD",
    }


def test_extract_salary_no_salary_present():
    result = extract_salary("This role requires 2-4 years of relevant experience.")
    assert result == {"salary_min": None, "salary_max": None, "salary_currency": None}


def test_extract_salary_masked_by_earlier_year_range_quirk():
    # Quirk: extract_salary tries its patterns in order and only advances
    # to the next pattern on a rejected match, it doesn't keep searching
    # for a later match with the *same* pattern. A "3-5 years" phrase
    # earlier in the text matches (and is correctly rejected by) the first
    # pattern, but that consumes the attempt — the real dollar amount
    # further down the text is never found because the stricter,
    # mandatory-USD second pattern doesn't tolerate the "$" before each
    # number.
    result = extract_salary(
        "Requirements: 3-5 years of experience.\n"
        "Compensation: $130,000 - $160,000 USD."
    )
    assert result == {"salary_min": None, "salary_max": None, "salary_currency": None}


def test_extract_application_questions():
    text = (
        "Are you authorized to work in the United States?\n"
        "Do you require sponsorship now or in the future?\n"
        "We are an equal opportunity employer."
    )
    assert extract_application_questions(text) == [
        "Are you authorized to work in the United States?",
        "Do you require sponsorship now or in the future?",
    ]


def test_extract_skills_required_vs_preferred_split():
    text = (
        "Requirements:\n"
        "- Proficiency in Python and SQL\n"
        "- Experience with Docker\n"
        "\n"
        "Nice to Have:\n"
        "- Experience with Kubernetes and AWS\n"
    )
    result = extract_skills(text)
    assert result["required_skills"] == ["Python", "SQL", "Docker"]
    assert result["preferred_skills"] == ["AWS", "Kubernetes"]


def test_extract_skills_preferred_qualifications_heading_collision_quirk():
    # Quirk: "qualifications" is itself one of REQUIREMENT_HEADINGS, so a
    # "Preferred Qualifications:" heading is treated as *another* instance
    # of the Requirements heading rather than a section boundary. The two
    # sections bleed together and a preferred-only skill (Kubernetes) leaks
    # into required_skills.
    text = (
        "Requirements:\n"
        "- Proficiency in Python and SQL\n"
        "\n"
        "Preferred Qualifications:\n"
        "- Experience with Kubernetes\n"
    )
    result = extract_skills(text)
    assert result["required_skills"] == ["Python", "SQL", "Kubernetes"]
    assert result["preferred_skills"] == ["Kubernetes"]


def test_infer_location_regex_spans_blank_lines_quirk():
    text = "Data Engineer at Northwind Analytics\n\nAustin, TX\n\nJoin our team."
    lines = _get_non_empty_lines(text)
    assert _infer_location(lines, text, "Unknown") == "Northwind Analytics\n\nAustin, TX"


def test_is_workday_url():
    assert is_workday_url(
        "https://acmecorp.wd1.myworkdayjobs.com/AcmeCareers/job/US-CA-Santa-Clara/x"
    )
    assert is_workday_url("https://acme.workdayjobs.com/job/x")
    assert not is_workday_url("https://boards.greenhouse.io/acme/jobs/1")


def test_parse_workday_url_slug_extracts_site_tenant_and_slugs():
    url = (
        "https://acmecorp.wd1.myworkdayjobs.com/AcmeCareers/job/"
        "US-CA-Santa-Clara/Senior-Software-Engineer_JR1988517-1"
    )
    result = parse_workday_url_slug(url)
    assert result["company"] == "Acmecorp"
    assert result["title"] == "Senior Software Engineer"
    assert result["location"] == "Santa Clara, CA, US"
    assert result["site"] == "AcmeCareers"
    assert result["tenant"] == "acmecorp"
    assert result["source"] == "workday"
    assert result["source_type"] == "workday_url_slug_fallback"
    assert result["inferred_fields"] == ["company", "title", "location"]


def test_parse_workday_url_slug_returns_empty_without_job_segment():
    assert parse_workday_url_slug("https://acmecorp.wd1.myworkdayjobs.com/AcmeCareers") == {}


def test_clean_workday_title_strips_requisition_code_suffix():
    assert clean_workday_title("Senior-Software-Engineer_JR1988517-1") == "Senior Software Engineer"


def test_clean_workday_location_country_region_city():
    assert clean_workday_location("US-CA-Santa-Clara") == "Santa Clara, CA, US"


def test_clean_workday_location_single_remote_segment():
    assert clean_workday_location("Remote") == "Remote"


def test_clean_workday_location_two_segment_quirk_does_not_shortcut_to_remote():
    # Quirk: the "Remote" shortcut only checks parts[0], so a two-segment
    # slug like "USA-Remote" (only one part, "USA", ahead of "Remote")
    # falls through to generic slug title-casing instead of being
    # recognized as remote.
    assert clean_workday_location("USA-Remote") == "Usa Remote"


def test_format_company_from_host_uses_known_alias():
    assert _format_company_from_host("nvidia.wd5.myworkdayjobs.com") == "NVIDIA"


def test_format_company_from_host_title_cases_unknown_tenant():
    assert _format_company_from_host("acmecorp.wd1.myworkdayjobs.com") == "Acmecorp"
