"""Coverage for the rule-based job parser's URL-based entry point
(`parse_job_url`): the requests_html / json_ld / embedded_json / workday_api
/ url-slug-fallback branches, and its error paths.

`requests.get` is mocked throughout — no real network calls are made. These
are characterization tests: they pin down current behavior, including a few
quirks (noted inline) that are not necessarily "correct" but must not change
silently.
"""

import json
from unittest.mock import Mock, patch

import pytest
import requests

from app.services.jobs import parser as parser_mod

WORKDAY_URL = (
    "https://acmecorp.wd1.myworkdayjobs.com/AcmeCareers/job/"
    "US-CA-Santa-Clara/Senior-Software-Engineer_JR1988517-1"
)


def _mock_response(text, url, status_code=200):
    response = Mock()
    response.text = text
    response.url = url
    response.status_code = status_code
    response.raise_for_status = lambda: None
    return response


def _patched_get(handler):
    return patch.object(parser_mod.requests, "get", side_effect=handler)


GREENHOUSE_HTML = """
<html>
<head><title>Data Engineer - Northwind Analytics</title>
<meta name="description" content="Northwind Analytics is hiring a Data Engineer in Austin, TX.">
</head>
<body>
<h1>Data Engineer</h1>
<p>Northwind Analytics is looking for a Data Engineer to join our team in Austin, TX.</p>
<h2>What You'll Do</h2>
<ul>
<li>Build and maintain ETL pipelines for the analytics warehouse</li>
<li>Own data quality checks across ingestion pipelines</li>
</ul>
<h2>Minimum Qualifications</h2>
<ul>
<li>3-5 years of experience with SQL and Python</li>
<li>Experience with Airflow and dbt</li>
</ul>
</body>
</html>
"""


def test_parse_job_url_full_html_page_uses_requests_html_source():
    url = "https://boards.greenhouse.io/northwind/jobs/12345"

    with _patched_get(lambda u, headers=None, timeout=None: _mock_response(GREENHOUSE_HTML, u)):
        result = parser_mod.parse_job_url(url)

    assert result["title"] == "Data Engineer"
    # Greenhouse is a known hosting domain, so the company-from-hostname
    # fallback is deliberately skipped and nothing else on the page names
    # the employer explicitly.
    assert result["company"] == "Unknown Company"
    assert result["location"] == "Austin, TX"
    assert result["role_category"] == "Data Engineer"
    assert result["seniority_level"] == "Mid Level"
    assert result["years_experience_min"] == 3
    assert result["years_experience_max"] == 5
    assert result["required_skills"] == ["Python", "SQL", "Airflow", "dbt", "analytics", "ETL"]
    assert result["responsibilities"] == [
        "Build and maintain ETL pipelines for the analytics warehouse",
        "Own data quality checks across ingestion pipelines",
    ]
    # Quirk: URL-sourced parses only get source="url" for pages the parser
    # recognizes as Workday; every other URL source silently stays at the
    # "manual" default set deep inside `_build_parse_result`.
    assert result["source"] == "manual"
    assert result["parsing_status"] == "full"
    assert result["parsing_warnings"] == []
    assert result["raw_parsed_data"]["source_type"] == "requests_html"


def _json_ld_html(description, *, title="Senior Backend Engineer", company="Vector Systems"):
    payload = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": title,
        "description": description,
        "hiringOrganization": {"@type": "Organization", "name": company},
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Denver",
                "addressRegion": "CO",
                "addressCountry": "US",
            },
        },
    }
    return f"""
<html><head><title>Loading... - Vector Systems Careers</title></head>
<body><div id="root"></div>
<script type="application/ld+json">{json.dumps(payload)}</script>
</body></html>
"""


LONG_JSON_LD_DESCRIPTION = (
    "<p>Vector Systems is looking for a Senior Backend Engineer to join our platform team. "
    "You will design, build, and operate backend services that power our core product, "
    "working closely with product and infrastructure teams to ship reliable, well-tested code.</p>"
    "<h2>Responsibilities</h2><ul>"
    "<li>Design and build backend services using Python and PostgreSQL</li>"
    "<li>Operate and monitor production systems running on AWS and Docker</li>"
    "</ul>"
    "<h2>Requirements</h2><ul>"
    "<li>5+ years of experience with Python and PostgreSQL</li>"
    "<li>Experience with Docker and Kubernetes</li>"
    "</ul>"
)


def test_parse_job_url_json_ld_job_posting_with_readable_description():
    url = "https://careers.vectorsystems.example/jobs/backend-engineer"
    html = _json_ld_html(LONG_JSON_LD_DESCRIPTION)

    with _patched_get(lambda u, headers=None, timeout=None: _mock_response(html, u)):
        result = parser_mod.parse_job_url(url)

    assert result["title"] == "Senior Backend Engineer"
    assert result["company"] == "Vector Systems"
    assert result["location"] == "Denver, CO, US"
    assert result["seniority_level"] == "Senior"
    assert result["years_experience_min"] == 5
    assert set(result["required_skills"]) == {"Python", "PostgreSQL", "AWS", "Docker", "Kubernetes"}
    assert result["parsing_status"] == "full"
    assert result["raw_parsed_data"]["source_type"] == "json_ld"
    # Quirk: JSON-LD descriptions are HTML, and _html_to_text/_json_string
    # collapse all whitespace (including the newlines BeautifulSoup inserts
    # between tags) into single spaces. With no line breaks left, the
    # Responsibilities/Requirements headings can never be recognized as
    # section boundaries, so both fields fall back to matching the entire
    # description as one undivided blob.
    assert result["responsibilities"] == result["requirements"]
    assert result["responsibilities"][0].startswith("Vector Systems is looking for")


def test_parse_job_url_json_ld_short_description_falls_back_to_url_slug():
    # The JSON-LD description here is under MIN_READABLE_TEXT_CHARS (300)
    # once HTML-stripped, so the json_ld branch is skipped entirely and
    # parsing falls through to the generic page-metadata/url-slug fallback,
    # which merges the JSON-LD's location with the slug-derived title.
    short_description = (
        "<p>We are looking for a Senior Backend Engineer with 5+ years of "
        "experience in Python and AWS.</p>"
    )
    url = "https://careers.vectorsystems.example/jobs/backend-engineer"
    html = _json_ld_html(short_description)

    with _patched_get(lambda u, headers=None, timeout=None: _mock_response(html, u)):
        result = parser_mod.parse_job_url(url)

    assert result["parsing_status"] == "partial"
    assert result["raw_parsed_data"]["source_type"] == "url_slug_fallback"
    assert result["title"] == "backend engineer"
    assert result["company"] == "Vectorsystems"
    assert result["location"] == "Denver, CO, US"
    assert parser_mod.PARTIAL_PARSE_WARNING in result["parsing_warnings"]


def test_parse_job_url_embedded_json_script_variable():
    description = (
        "Vertex Labs is looking for a Machine Learning Engineer to join our applied research team. "
        "You will design experiments, build models with PyTorch and TensorFlow, and deploy them to "
        "production using Docker and Kubernetes on AWS. This role partners closely with product and "
        "data engineering to bring research into real user-facing features."
    )
    html = f"""
<html><head><title>Vertex Labs Careers</title></head>
<body>
<div id="app"></div>
<script>
  window.__JOB_DATA__ = {{"jobPosting": {{"jobDescription": {json.dumps(description)}, "qualifications": "5+ years of experience"}}}};
</script>
</body></html>
"""
    url = "https://careers.vertexlabs.example/jobs/ml-engineer"

    with _patched_get(lambda u, headers=None, timeout=None: _mock_response(html, u)):
        result = parser_mod.parse_job_url(url)

    assert result["raw_parsed_data"]["source_type"] == "embedded_json"
    assert result["parsing_status"] == "full"
    assert set(result["required_skills"]) >= {"PyTorch", "TensorFlow", "Docker", "Kubernetes", "AWS"}
    assert result["years_experience_min"] == 5


WORKDAY_SHELL_HTML = """
<html><head><title>Acme Careers</title></head>
<body><div id="app"></div><script>window.__INITIAL_STATE__ = {};</script></body></html>
"""

WORKDAY_API_DESCRIPTION = (
    "<p>Acme Corp is hiring a Senior Software Engineer to build our core platform. "
    "You will work across the stack with Python, PostgreSQL, and AWS, partnering closely with "
    "product and design to ship reliable, well-tested features end to end. This role sits on our "
    "platform team and owns critical infrastructure that every other engineering team depends on "
    "daily.</p>"
    "<h2>Requirements</h2><ul><li>5+ years of experience with Python</li>"
    "<li>Experience with AWS and Docker</li></ul>"
)


def test_parse_job_url_workday_js_heavy_page_uses_api_fallback():
    api_payload = {
        "jobPostingInfo": {
            "title": "Senior Software Engineer",
            "jobDescription": WORKDAY_API_DESCRIPTION,
            "location": "Santa Clara, CA",
        },
        "hiringOrganization": {"name": "Acme Corp"},
    }

    def handler(url, headers=None, timeout=None):
        if "/wday/cxs/" in url:
            return _mock_response(json.dumps(api_payload), url)
        return _mock_response(WORKDAY_SHELL_HTML, url)

    with _patched_get(handler):
        result = parser_mod.parse_job_url(WORKDAY_URL)

    assert result["source"] == "workday"
    assert result["title"] == "Senior Software Engineer"
    assert result["company"] == "Acme Corp"
    assert result["location"] == "Santa Clara, CA"
    assert result["parsing_status"] == "full"
    assert result["raw_parsed_data"]["source_type"] == "workday_api"
    assert result["years_experience_min"] == 5
    assert parser_mod.JS_HEAVY_FETCH_WARNING in result["parsing_warnings"]


def test_parse_job_url_workday_api_unavailable_falls_back_to_url_slug_inference():
    def handler(url, headers=None, timeout=None):
        if "/wday/cxs/" in url:
            raise requests.exceptions.ConnectionError("boom")
        return _mock_response(WORKDAY_SHELL_HTML, url)

    with _patched_get(handler):
        result = parser_mod.parse_job_url(WORKDAY_URL)

    assert result["source"] == "workday"
    assert result["title"] == "Senior Software Engineer"
    assert result["company"] == "Acmecorp"
    assert result["location"] == "Santa Clara, CA, US"
    assert result["parsing_status"] == "partial"
    assert result["raw_parsed_data"]["source_type"] == "workday_url_slug_fallback"
    assert parser_mod.WORKDAY_INFERENCE_WARNING in result["parsing_warnings"]
    assert any("Workday public API fallback failed" in warning for warning in result["parsing_warnings"])


def test_parse_job_url_invalid_scheme_raises():
    with pytest.raises(ValueError, match="must start with http"):
        parser_mod.fetch_job_url_text("ftp://example.com/job/1")


def test_parse_job_url_empty_url_raises():
    with pytest.raises(ValueError, match="Job URL is empty"):
        parser_mod.fetch_job_url_text("   ")


def test_parse_job_url_non_workday_network_failure_reraises():
    def handler(url, headers=None, timeout=None):
        raise requests.exceptions.ConnectionError("network down")

    with _patched_get(handler):
        with pytest.raises(ValueError, match="Failed to fetch the job URL"):
            parser_mod.parse_job_url("https://careers.example.com/jobs/123")


def test_parse_job_url_completely_unparseable_page_raises():
    empty_shell_html = "<html><head><title></title></head><body><div id='app'></div></body></html>"

    with _patched_get(lambda u, headers=None, timeout=None: _mock_response(empty_shell_html, u)):
        with pytest.raises(ValueError, match="did not contain readable text"):
            parser_mod.parse_job_url("https://careers.example.com/")
