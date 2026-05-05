import json
import re
from typing import Any
from urllib.parse import quote, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from app.services.ai import build_job_parse_prompt, get_ai_provider
from app.utils.text import normalize_whitespace

DEFAULT_HEADERS = {
    "User-Agent": (
        "CareerAgent/0.5 Rule-Based Job Parser "
        "(safe rule-based fetch; no browser automation)"
    )
}
FETCH_TIMEOUT_SECONDS = 10
MIN_READABLE_TEXT_CHARS = 300
MAX_EMBEDDED_SCRIPT_CHARS = 200_000
JS_HEAVY_FETCH_WARNING = "Fetched page had little readable text; it may be JavaScript-heavy."
PARTIAL_PARSE_WARNING = (
    "This page is JavaScript-heavy. CareerAgent inferred partial details from the URL. "
    "For better parsing, paste the job description text manually."
)
WORKDAY_INFERENCE_WARNING = "CareerAgent inferred title/location/company from the Workday URL."
PASTE_DESCRIPTION_WARNING = "Paste the job description manually for better results."
PARTIAL_JOB_DESCRIPTION = (
    "CareerAgent could not extract the full job description from this JavaScript-heavy page. "
    "Partial details were inferred from the URL. Paste the job description manually for better parsing."
)
KNOWN_HOSTING_DOMAINS = {
    "ashbyhq.com",
    "boards.greenhouse.io",
    "greenhouse.io",
    "jobs.ashbyhq.com",
    "jobs.lever.co",
    "lever.co",
    "myworkdayjobs.com",
    "workday.com",
    "workdayjobs.com",
}
WORKDAY_COMPANY_ALIASES = {
    "nvidia": "NVIDIA",
}
SKILL_PATTERNS = [
    ("Python", [r"\bpython\b"]),
    ("SQL", [r"\bsql\b"]),
    ("Java", [r"\bjava\b"]),
    ("JavaScript", [r"\bjavascript\b"]),
    ("TypeScript", [r"\btypescript\b"]),
    ("C++", [r"\bc\+\+\b"]),
    ("R", [r"\br\b programming", r"\br language\b", r"\busing r\b"]),
    ("MATLAB", [r"\bmatlab\b"]),
    ("Pandas", [r"\bpandas\b"]),
    ("NumPy", [r"\bnumpy\b"]),
    ("scikit-learn", [r"\bscikit-learn\b", r"\bsklearn\b"]),
    ("TensorFlow", [r"\btensorflow\b"]),
    ("PyTorch", [r"\bpytorch\b"]),
    ("Deep Learning", [r"\bdeep learning\b"]),
    ("TensorRT", [r"\btensorrt\b"]),
    ("XGBoost", [r"\bxgboost\b"]),
    ("Spark", [r"\bspark\b", r"\bapache spark\b"]),
    ("Databricks", [r"\bdatabricks\b"]),
    ("Airflow", [r"\bairflow\b"]),
    ("dbt", [r"\bdbt\b"]),
    ("Tableau", [r"\btableau\b"]),
    ("Power BI", [r"\bpower bi\b"]),
    ("Looker", [r"\blooker\b"]),
    ("Excel", [r"\bexcel\b"]),
    ("AWS", [r"\baws\b", r"\bamazon web services\b"]),
    ("GCP", [r"\bgcp\b", r"\bgoogle cloud\b"]),
    ("Azure", [r"\bazure\b"]),
    ("Docker", [r"\bdocker\b"]),
    ("Kubernetes", [r"\bkubernetes\b", r"\bk8s\b"]),
    ("Git", [r"\bgit\b"]),
    ("Linux", [r"\blinux\b"]),
    ("PostgreSQL", [r"\bpostgresql\b", r"\bpostgres\b"]),
    ("MySQL", [r"\bmysql\b"]),
    ("Snowflake", [r"\bsnowflake\b"]),
    ("BigQuery", [r"\bbigquery\b", r"\bbig query\b"]),
    ("Redshift", [r"\bredshift\b"]),
    ("machine learning", [r"\bmachine learning\b"]),
    ("data science", [r"\bdata science\b"]),
    ("data engineering", [r"\bdata engineering\b"]),
    ("analytics", [r"\banalytics\b"]),
    ("statistics", [r"\bstatistics\b", r"\bstatistical\b"]),
    ("experimentation", [r"\bexperimentation\b"]),
    ("A/B testing", [r"\ba/?b testing\b"]),
    ("ETL", [r"\betl\b"]),
    ("data pipelines", [r"\bdata pipelines?\b"]),
    ("APIs", [r"\bapis?\b"]),
]
PREFERRED_SECTION_KEYWORDS = [
    "bonus",
    "ideal candidate",
    "nice to have",
    "preferred",
    "preferred qualifications",
]
RESPONSIBILITY_HEADINGS = [
    "responsibilities",
    "what you'll do",
    "what you will do",
    "you will",
    "day to day",
]
REQUIREMENT_HEADINGS = [
    "minimum qualifications",
    "must have",
    "qualifications",
    "requirements",
    "what we're looking for",
]
EDUCATION_HEADINGS = [
    "education",
    "education requirement",
    "education requirements",
]
ALL_HEADINGS = RESPONSIBILITY_HEADINGS + REQUIREMENT_HEADINGS + EDUCATION_HEADINGS + PREFERRED_SECTION_KEYWORDS


def _clean_text(text: str) -> str:
    return normalize_whitespace(text.replace("\xa0", " "))


def _get_non_empty_lines(text: str) -> list[str]:
    return [line.strip(" -•\t") for line in text.splitlines() if line.strip()]


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _html_to_text(value: str) -> str:
    soup = BeautifulSoup(value or "", "html.parser")
    return _clean_text(soup.get_text("\n", strip=True))


def _is_readable_text(text: str) -> bool:
    return len(_clean_text(text)) >= MIN_READABLE_TEXT_CHARS


def _json_loads_maybe(raw: str) -> Any | None:
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def _iter_json_objects(value: Any):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _iter_json_objects(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_json_objects(item)


def _json_string(value: Any) -> str:
    if isinstance(value, str):
        return _html_to_text(value) if "<" in value and ">" in value else _clean_text(value)
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def _collect_json_strings(value: Any, collector: list[str]) -> None:
    if isinstance(value, str):
        cleaned = _json_string(value)
        if len(cleaned) >= 3 and not cleaned.lower().startswith(("http://", "https://", "urn:")):
            collector.append(cleaned)
        return
    if isinstance(value, dict):
        for nested in value.values():
            _collect_json_strings(nested, collector)
        return
    if isinstance(value, list):
        for item in value:
            _collect_json_strings(item, collector)


def _meta_content(soup: BeautifulSoup, *, name: str | None = None, property_name: str | None = None) -> str:
    attrs = {"name": name} if name else {"property": property_name}
    tag = soup.find("meta", attrs=attrs)
    if not tag:
        return ""
    return _clean_text(str(tag.get("content") or ""))


def _extract_embedded_page_data(soup: BeautifulSoup) -> dict[str, Any]:
    json_payloads: list[Any] = []
    embedded_chunks: list[str] = []
    key_pattern = re.compile(
        r'"(?:title|jobTitle|jobDescription|description|location|locationsText|responsibilities|qualifications)"\s*:\s*"((?:\\.|[^"\\])*)"',
        re.IGNORECASE,
    )

    for script in soup.find_all("script"):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw:
            continue

        script_type = str(script.get("type") or "").lower()
        script_id = str(script.get("id") or "")
        should_try_json = script_type in {"application/ld+json", "application/json"} or script_id == "__NEXT_DATA__"
        if should_try_json:
            payload = _json_loads_maybe(raw.strip())
            if payload is not None:
                json_payloads.append(payload)
                _collect_json_strings(payload, embedded_chunks)
            continue

        lowered = raw.lower()
        if len(raw) > MAX_EMBEDDED_SCRIPT_CHARS or not any(
            keyword in lowered for keyword in ["jobdescription", "jobposting", "qualifications", "responsibilities"]
        ):
            continue
        for match in key_pattern.finditer(raw):
            decoded = _json_loads_maybe(f'"{match.group(1)}"')
            embedded_chunks.append(_json_string(decoded if decoded is not None else match.group(1)))

    return {
        "json_ld": json_payloads,
        "embedded_text": "\n".join(_unique_preserve_order(embedded_chunks))[:50_000],
    }


def _extract_job_posting_metadata_from_json(payloads: list[Any]) -> dict[str, str]:
    for payload in payloads:
        for item in _iter_json_objects(payload):
            raw_type = item.get("@type") or item.get("type")
            type_values = raw_type if isinstance(raw_type, list) else [raw_type]
            if not any(str(type_value).lower() == "jobposting" for type_value in type_values if type_value):
                continue

            hiring_organization = item.get("hiringOrganization") or {}
            job_location = item.get("jobLocation") or {}
            location = ""
            if isinstance(job_location, list) and job_location:
                job_location = job_location[0]
            if isinstance(job_location, dict):
                address = job_location.get("address") or {}
                if isinstance(address, dict):
                    locality = _json_string(address.get("addressLocality"))
                    region = _json_string(address.get("addressRegion"))
                    country = _json_string(address.get("addressCountry"))
                    location = ", ".join(part for part in [locality, region, country] if part)
                location = location or _json_string(job_location.get("name"))

            return {
                "title": _json_string(item.get("title")),
                "company": _json_string(hiring_organization.get("name")) if isinstance(hiring_organization, dict) else "",
                "location": location,
                "job_description": _json_string(item.get("description")),
            }
    return {}


def clean_slug_text(slug: str) -> str:
    decoded = unquote(slug or "")
    decoded = decoded.rsplit("?", 1)[0].rsplit("#", 1)[0]
    decoded = re.sub(r"\.[.]+$", "", decoded)
    decoded = re.sub(r"[_+]+", "-", decoded)
    decoded = re.sub(r"-{4,}", " CAREERAGENTDASH ", decoded)
    decoded = decoded.replace("---", " CAREERAGENTDASH ")
    decoded = decoded.replace("--", " CAREERAGENTCOMMA ")
    decoded = decoded.replace("-", " ")
    decoded = decoded.replace("CAREERAGENTDASH", "-")
    decoded = decoded.replace("CAREERAGENTCOMMA", ",")
    decoded = re.sub(r"\s+([,])", r"\1", decoded)
    decoded = re.sub(r"\s*-\s*", " - ", decoded)
    return _clean_text(decoded).strip(" ,-/")


def clean_workday_title(title_slug: str) -> str:
    cleaned_slug = re.sub(r"_[A-Z]{1,8}\d+.*$", "", title_slug or "")
    return clean_slug_text(cleaned_slug)


def clean_workday_location(location_slug: str) -> str:
    parts = [part for part in re.split(r"[-_]+", unquote(location_slug or "")) if part]
    if len(parts) >= 3 and len(parts[0]) in {2, 3} and len(parts[1]) == 2:
        country = parts[0].upper()
        region = parts[1].upper()
        city = " ".join(parts[2:]).title()
        return f"{city}, {region}, {country}"
    if parts and parts[0].lower() == "remote":
        return "Remote"
    return clean_slug_text(location_slug).title() or "Unknown"


def is_workday_url(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return "myworkdayjobs.com" in hostname or "workdayjobs.com" in hostname


def _workday_tenant_from_host(hostname: str) -> str:
    first_label = (hostname or "").split(".", 1)[0].lower()
    return first_label.removeprefix("www-").removeprefix("www")


def _format_company_from_host(hostname: str) -> str:
    tenant = _workday_tenant_from_host(hostname)
    if not tenant:
        return "Unknown Company"
    if tenant in WORKDAY_COMPANY_ALIASES:
        return WORKDAY_COMPANY_ALIASES[tenant]
    return tenant.replace("-", " ").title()


def parse_workday_url_slug(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    path_parts = [unquote(part) for part in parsed.path.split("/") if part]
    if "job" not in path_parts:
        return {}

    job_index = path_parts.index("job")
    site = path_parts[0] if job_index > 0 else ""
    location_slug = path_parts[job_index + 1] if len(path_parts) > job_index + 1 else ""
    title_slug = path_parts[job_index + 2] if len(path_parts) > job_index + 2 else ""
    title = clean_workday_title(title_slug)
    location = clean_workday_location(location_slug)
    company = _format_company_from_host(hostname)
    inferred_fields = [
        field
        for field, value in [("company", company), ("title", title), ("location", location)]
        if value and not value.startswith("Unknown")
    ]

    return {
        "company": company,
        "title": title or "Unknown Title",
        "location": location or "Unknown",
        "source": "workday",
        "source_type": "workday_url_slug_fallback",
        "site": site,
        "tenant": _workday_tenant_from_host(hostname),
        "location_slug": location_slug,
        "title_slug": title_slug,
        "inferred_fields": inferred_fields,
    }


def extract_workday_metadata_from_url(url: str) -> dict[str, Any]:
    return parse_workday_url_slug(url)


def try_workday_api_fetch(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    slug_metadata = parse_workday_url_slug(url)
    site = str(slug_metadata.get("site") or "")
    tenant = str(slug_metadata.get("tenant") or "")
    location_slug = str(slug_metadata.get("location_slug") or "")
    title_slug = str(slug_metadata.get("title_slug") or "")
    if not all([hostname, tenant, site, location_slug, title_slug]):
        return {"source_type": "workday_api_unavailable", "warnings": ["Workday API fallback was skipped because the URL structure was incomplete."]}

    api_url = (
        f"{parsed.scheme or 'https'}://{hostname}/wday/cxs/{quote(tenant, safe='')}/"
        f"{quote(site, safe='')}/job/{quote(location_slug, safe='')}/{quote(title_slug, safe='')}"
    )
    warnings: list[str] = []
    try:
        response = requests.get(
            api_url,
            headers={**DEFAULT_HEADERS, "Accept": "application/json"},
            timeout=FETCH_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        return {
            "source_type": "workday_api_unavailable",
            "api_url": api_url,
            "warnings": [f"Workday public API fallback failed: {exc}"],
        }

    if response.status_code >= 400:
        return {
            "source_type": "workday_api_unavailable",
            "api_url": api_url,
            "status_code": response.status_code,
            "warnings": [f"Workday public API fallback returned HTTP {response.status_code}."],
        }

    payload = _json_loads_maybe(response.text)
    if not isinstance(payload, dict):
        return {
            "source_type": "workday_api_unavailable",
            "api_url": api_url,
            "status_code": response.status_code,
            "warnings": ["Workday public API fallback did not return JSON."],
        }

    job_info = payload.get("jobPostingInfo") if isinstance(payload.get("jobPostingInfo"), dict) else payload
    description = _json_string(job_info.get("jobDescription") or job_info.get("description"))
    title = _json_string(job_info.get("title"))
    company = _json_string(payload.get("hiringOrganization"))
    if isinstance(payload.get("hiringOrganization"), dict):
        company = _json_string(payload["hiringOrganization"].get("name"))
    location = _json_string(job_info.get("location") or job_info.get("locationsText"))
    if not description:
        warnings.append("Workday public API fallback returned no job description.")

    return {
        "source_type": "workday_api",
        "api_url": api_url,
        "status_code": response.status_code,
        "title": title,
        "company": company,
        "location": location,
        "job_description": description,
        "warnings": warnings,
    }


def _parse_generic_url_slug(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return {}
    title = clean_slug_text(path_parts[-1])
    if not title or title.lower() in {"job", "jobs", "careers", "career", "apply"}:
        return {}
    return {
        "company": _infer_company([], url=url),
        "title": title,
        "location": "Unknown",
        "source": "url",
        "source_type": "url_slug_fallback",
        "inferred_fields": ["title"],
    }


def _parse_page_metadata_fallback(fetched: dict[str, Any], json_metadata: dict[str, str]) -> dict[str, Any]:
    title_hint = (
        str(fetched.get("h1") or "")
        or str(json_metadata.get("title") or "")
        or str(fetched.get("page_title") or "")
    )
    meta_description = str(json_metadata.get("job_description") or fetched.get("meta_description") or "")
    if not title_hint and not meta_description:
        return {}

    lines = _get_non_empty_lines("\n".join([title_hint, meta_description]))
    remote_status = infer_remote_status(meta_description)
    title = _infer_title(lines, title_hint=title_hint)
    company = str(json_metadata.get("company") or "") or _infer_company(
        lines,
        title_hint=title_hint,
        url=str(fetched.get("final_url") or fetched.get("url") or ""),
    )
    location = str(json_metadata.get("location") or "") or _infer_location(lines, meta_description, remote_status)
    inferred_fields = [
        field
        for field, value in [("company", company), ("title", title), ("location", location)]
        if value and not value.startswith("Unknown")
    ]
    if not inferred_fields:
        return {}
    return {
        "company": company,
        "title": title,
        "location": location,
        "source": "url",
        "source_type": "page_metadata_fallback",
        "inferred_fields": inferred_fields,
    }


def _line_is_heading(line: str) -> bool:
    cleaned = re.sub(r"[^a-z0-9/ +]", " ", line.lower()).strip()
    if not cleaned or len(cleaned) > 80:
        return False
    return any(keyword in cleaned for keyword in ALL_HEADINGS)


def _extract_section(lines: list[str], heading_keywords: list[str]) -> list[str]:
    collected: list[str] = []
    in_section = False
    for line in lines:
        lowered = line.lower().rstrip(":")
        if any(keyword in lowered for keyword in heading_keywords) and len(line) <= 80:
            in_section = True
            continue
        if in_section and _line_is_heading(line):
            break
        if in_section:
            cleaned = line.strip(" -•\t")
            if cleaned:
                collected.append(cleaned)
    return _unique_preserve_order(collected)


def _find_prefixed_value(lines: list[str], prefixes: list[str]) -> str | None:
    for line in lines[:12]:
        lowered = line.lower()
        for prefix in prefixes:
            if lowered.startswith(prefix):
                value = line.split(":", 1)[-1].strip() if ":" in line else line[len(prefix):].strip()
                return value or None
    return None


def _looks_like_title(line: str) -> bool:
    lowered = line.lower()
    blocked_fragments = ["company:", "location:", "about", "apply", "job description"]
    if any(fragment in lowered for fragment in blocked_fragments):
        return False
    return 3 <= len(line) <= 100


def _infer_title(lines: list[str], title_hint: str | None = None) -> str:
    explicit = _find_prefixed_value(lines, ["title", "role", "position"])
    if explicit:
        return explicit
    if title_hint:
        split_title = re.split(r"\s+[|\-]\s+|\s+at\s+", title_hint, maxsplit=1)
        candidate = split_title[0].strip()
        if _looks_like_title(candidate):
            return candidate
    for line in lines[:8]:
        if _looks_like_title(line):
            return line
    return "Unknown Title"


def _infer_company(lines: list[str], title_hint: str | None = None, url: str | None = None) -> str:
    explicit = _find_prefixed_value(lines, ["company", "employer", "organization"])
    if explicit:
        return explicit
    for line in lines[:6]:
        if " at " in line.lower():
            company = line.split(" at ", 1)[1].strip()
            if company:
                return company
    if title_hint and " at " in title_hint.lower():
        company = title_hint.split(" at ", 1)[1].strip()
        if company:
            return company
    if url:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        hostname = hostname.removeprefix("www.")
        if hostname in {"localhost", "127.0.0.1", "host.docker.internal"} or hostname.endswith(".internal"):
            return "Unknown Company"
        if hostname and hostname not in KNOWN_HOSTING_DOMAINS:
            parts = hostname.split(".")
            if len(parts) >= 2 and parts[-2] not in {"example", "jobs"}:
                return parts[-2].replace("-", " ").title()
    return "Unknown Company"


def _infer_location(lines: list[str], text: str, remote_status: str) -> str:
    explicit = _find_prefixed_value(lines, ["location"])
    if explicit:
        return explicit
    location_match = re.search(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*,\s*[A-Z]{2})\b", text)
    if location_match:
        return location_match.group(1)
    if remote_status == "Remote":
        return "Remote"
    if remote_status == "Hybrid":
        return "Hybrid"
    if remote_status == "Onsite":
        return "Onsite"
    return "Unknown"


def _infer_employment_type(text: str) -> str | None:
    lowered = text.lower()
    employment_map = [
        ("Internship", ["internship", "intern "]),
        ("Full-time", ["full-time", "full time"]),
        ("Part-time", ["part-time", "part time"]),
        ("Contract", ["contract", "contractor"]),
        ("Temporary", ["temporary", "temp role"]),
        ("Apprenticeship", ["apprenticeship", "apprentice"]),
    ]
    for label, keywords in employment_map:
        if any(keyword in lowered for keyword in keywords):
            return label
    return None


def infer_remote_status(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in ["fully remote", "remote-first", "work from home"]):
        return "Remote"
    if "hybrid" in lowered:
        return "Hybrid"
    if "remote" in lowered:
        return "Remote"
    if any(keyword in lowered for keyword in ["on-site", "onsite", "in office"]):
        return "Onsite"
    return "Unknown"


def infer_role_category(title: str, description: str) -> str:
    haystack = f"{title}\n{description}".lower()
    rules = [
        ("Data Scientist", ["data scientist", "applied scientist"]),
        ("Data Engineer", ["data engineer", "etl engineer", "analytics pipeline"]),
        ("ML Engineer", ["ml engineer", "machine learning engineer", "ai engineer", "deep learning"]),
        ("Analytics Engineer", ["analytics engineer", "dbt developer"]),
        ("Data Analyst", ["data analyst", "business analyst", "analytics analyst"]),
        ("Software Engineer", ["software engineer", "backend engineer", "frontend engineer", "full stack"]),
    ]
    for label, keywords in rules:
        if any(keyword in haystack for keyword in keywords):
            return label
    return "Other"


def infer_seniority(title: str, description: str) -> str:
    haystack = f"{title}\n{description}".lower()
    if any(keyword in haystack for keyword in ["intern", "internship"]):
        return "Internship"
    if any(keyword in haystack for keyword in ["new grad", "new graduate", "recent graduate", "university graduate", "new college grad", "college grad"]):
        return "New Grad"
    if any(keyword in haystack for keyword in ["entry level", "entry-level", "associate", "junior", "early career"]):
        return "Entry Level"
    if any(keyword in haystack for keyword in ["senior", "staff", "principal", "lead", "head of", "manager"]):
        return "Senior"
    years = extract_years_experience(description)
    max_years = years["years_experience_max"]
    min_years = years["years_experience_min"]
    if max_years is not None and max_years >= 3:
        return "Mid Level"
    if min_years is not None and min_years >= 3:
        return "Mid Level"
    return "Unknown"


def _parse_salary_number(raw_value: str, suffix: str | None) -> float:
    normalized = raw_value.replace(",", "").strip()
    value = float(normalized)
    if suffix and suffix.lower() == "k":
        value *= 1000
    return value


def extract_salary(text: str) -> dict[str, Any]:
    patterns = [
        re.compile(
            r"\$?\s*(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(k|K)?\s*(?:-|to|–|—)\s*"
            r"\$?\s*(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(k|K)?(?:\s*(USD|usd))?",
            re.IGNORECASE,
        ),
        re.compile(
            r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(k|K)?\s*(?:-|to|–|—)\s*"
            r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(k|K)?\s*(USD|usd)",
            re.IGNORECASE,
        ),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if not match:
            continue
        groups = match.groups()
        minimum = _parse_salary_number(groups[0], groups[1])
        maximum = _parse_salary_number(groups[2], groups[3])
        context_window = text[max(match.start() - 30, 0) : min(match.end() + 30, len(text))].lower()
        matched_text = match.group(0).lower()
        has_salary_context = any(token in context_window for token in ["salary", "compensation", "pay", "usd", "$"])
        looks_like_year_range = "year" in context_window and "$" not in matched_text and "usd" not in matched_text
        if looks_like_year_range and minimum < 1000 and maximum < 1000 and not has_salary_context:
            continue
        currency = groups[4].upper() if len(groups) > 4 and groups[4] else "USD"
        return {
            "salary_min": minimum,
            "salary_max": maximum,
            "salary_currency": currency,
        }
    return {
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
    }


def extract_years_experience(text: str) -> dict[str, int | None]:
    lowered = text.lower()
    range_patterns = [
        re.compile(r"(\d+)\s*(?:\+?\s*)?(?:-|to|–|—)\s*(\d+)\s+years?"),
        re.compile(r"(\d+)\s*-\s*(\d+)\s*yrs?"),
    ]
    for pattern in range_patterns:
        match = pattern.search(lowered)
        if match:
            return {
                "years_experience_min": int(match.group(1)),
                "years_experience_max": int(match.group(2)),
            }
    minimum_patterns = [
        re.compile(r"at least\s+(\d+)\s+years?"),
        re.compile(r"minimum of\s+(\d+)\s+years?"),
        re.compile(r"(\d+)\+\s+years?"),
    ]
    for pattern in minimum_patterns:
        match = pattern.search(lowered)
        if match:
            years = int(match.group(1))
            return {
                "years_experience_min": years,
                "years_experience_max": years,
            }
    return {
        "years_experience_min": None,
        "years_experience_max": None,
    }


def extract_application_questions(text: str) -> list[str]:
    question_keywords = [
        "why are you interested",
        "tell us about yourself",
        "are you authorized",
        "do you require sponsorship",
        "are you willing to relocate",
        "expected salary",
        "cover letter",
        "portfolio",
    ]
    results: list[str] = []
    for line in _get_non_empty_lines(text):
        lowered = line.lower()
        if "?" in line and any(keyword in lowered for keyword in question_keywords):
            results.append(line)
            continue
        if any(keyword in lowered for keyword in question_keywords):
            results.append(line)
    return _unique_preserve_order(results)


def extract_skills(text: str) -> dict[str, list[str]]:
    lines = _get_non_empty_lines(text)
    preferred_section = "\n".join(_extract_section(lines, PREFERRED_SECTION_KEYWORDS))
    required_section_items = (
        _extract_section(lines, REQUIREMENT_HEADINGS) + _extract_section(lines, RESPONSIBILITY_HEADINGS)
    )
    required_section = "\n".join(required_section_items)
    all_matches: list[str] = []
    required_matches: list[str] = []
    preferred_matches: list[str] = []

    for skill_name, patterns in SKILL_PATTERNS:
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            all_matches.append(skill_name)
        if required_section and any(re.search(pattern, required_section, flags=re.IGNORECASE) for pattern in patterns):
            required_matches.append(skill_name)
        if preferred_section and any(re.search(pattern, preferred_section, flags=re.IGNORECASE) for pattern in patterns):
            preferred_matches.append(skill_name)

    all_matches = _unique_preserve_order(all_matches)
    preferred_matches = _unique_preserve_order(preferred_matches)
    if required_matches:
        required_matches = _unique_preserve_order(required_matches)
    else:
        required_matches = all_matches

    return {
        "required_skills": required_matches,
        "preferred_skills": preferred_matches,
    }


def _extract_education_requirements(text: str, lines: list[str]) -> list[str]:
    section = _extract_section(lines, EDUCATION_HEADINGS)
    if section:
        return section
    patterns = [
        r"bachelor'?s degree[^\n.]*",
        r"master'?s degree[^\n.]*",
        r"ph\.?d[^\n.]*",
        r"degree in [^\n.]*",
    ]
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(match.group(0).strip() for match in re.finditer(pattern, text, flags=re.IGNORECASE))
    return _unique_preserve_order(matches)


def _extract_requirement_fallback(lines: list[str]) -> list[str]:
    collected: list[str] = []
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in ["experience with", "proficient in", "required", "must have"]):
            collected.append(line)
    return _unique_preserve_order(collected)


def _extract_responsibility_fallback(lines: list[str]) -> list[str]:
    collected: list[str] = []
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in ["responsible for", "you will", "build", "develop", "design", "maintain"]):
            collected.append(line)
    return _unique_preserve_order(collected)


def _build_parse_result(text: str, *, url: str = "", title_hint: str | None = None, fetch_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError("Job content is empty. Paste a job description or provide a URL to parse.")

    lines = _get_non_empty_lines(cleaned_text)
    remote_status = infer_remote_status(cleaned_text)
    title = _infer_title(lines, title_hint=title_hint)
    company = _infer_company(lines, title_hint=title_hint, url=url or None)
    location = _infer_location(lines, cleaned_text, remote_status)
    employment_type = _infer_employment_type(cleaned_text)
    role_category = infer_role_category(title, cleaned_text)
    seniority_level = infer_seniority(title, cleaned_text)
    skills = extract_skills(cleaned_text)
    salary = extract_salary(cleaned_text)
    years_experience = extract_years_experience(cleaned_text)
    responsibilities = _extract_section(lines, RESPONSIBILITY_HEADINGS) or _extract_responsibility_fallback(lines)
    requirements = _extract_section(lines, REQUIREMENT_HEADINGS) or _extract_requirement_fallback(lines)
    education_requirements = _extract_education_requirements(cleaned_text, lines)
    application_questions = extract_application_questions(cleaned_text)

    return {
        "company": company,
        "title": title,
        "location": location,
        "url": url,
        "source": "manual",
        "job_description": cleaned_text,
        "employment_type": employment_type,
        "remote_status": remote_status,
        "role_category": role_category,
        "seniority_level": seniority_level,
        "years_experience_min": years_experience["years_experience_min"],
        "years_experience_max": years_experience["years_experience_max"],
        "salary_min": salary["salary_min"],
        "salary_max": salary["salary_max"],
        "salary_currency": salary["salary_currency"],
        "required_skills": skills["required_skills"],
        "preferred_skills": skills["preferred_skills"],
        "responsibilities": responsibilities,
        "requirements": requirements,
        "education_requirements": education_requirements,
        "application_questions": application_questions,
        "raw_parsed_data": {
            "parser": "rule_based_v1",
            "line_count": len(lines),
            "fetch_metadata": fetch_metadata or {},
            "title_hint": title_hint,
        },
    }


AI_PARSE_FIELDS = {
    "company",
    "title",
    "location",
    "employment_type",
    "remote_status",
    "role_category",
    "seniority_level",
    "years_experience_min",
    "years_experience_max",
    "salary_min",
    "salary_max",
    "salary_currency",
    "required_skills",
    "preferred_skills",
    "responsibilities",
    "requirements",
    "education_requirements",
    "application_questions",
}


def _ai_parse_mode(provider_name: str) -> str:
    if provider_name == "mock":
        return "mock_ai"
    return f"ai_{provider_name}"


def _merge_ai_parse_result(rule_based_result: dict[str, Any], ai_result: dict[str, Any]) -> dict[str, Any]:
    merged = dict(rule_based_result)
    for field in AI_PARSE_FIELDS:
        ai_value = ai_result.get(field)
        if ai_value in (None, "", []):
            continue
        merged[field] = ai_value
    return merged


def _parse_with_optional_ai(
    *,
    rule_based_result: dict[str, Any],
    cleaned_text: str,
    use_ai: bool,
    provider_name: str | None,
) -> dict[str, Any]:
    base_warnings = list(rule_based_result.get("parsing_warnings") or [])
    if not use_ai:
        return {
            **rule_based_result,
            "parse_mode": "rule_based",
            "provider": None,
            "parsing_status": str(rule_based_result.get("parsing_status") or "full"),
            "parsing_warnings": base_warnings,
        }

    provider = get_ai_provider(provider_name)
    warnings: list[str] = list(base_warnings)
    if not provider.is_available():
        warnings.append(provider.unavailable_reason or f"{provider.name} provider is unavailable.")
        return {
            **rule_based_result,
            "parse_mode": "rule_based",
            "provider": provider.name,
            "parsing_status": str(rule_based_result.get("parsing_status") or "full"),
            "parsing_warnings": warnings + ["Fell back to rule-based parsing."],
        }

    ai_response = provider.parse_json(
        "job_parse",
        build_job_parse_prompt(cleaned_text),
        context={"fallback_json": rule_based_result},
    )
    warnings.extend(list(ai_response.get("warnings") or []))
    parsed_json = ai_response.get("parsed_json")
    if ai_response.get("success") and isinstance(parsed_json, dict):
        merged = _merge_ai_parse_result(rule_based_result, parsed_json)
        raw_parsed_data = dict(merged.get("raw_parsed_data") or {})
        raw_parsed_data["ai_result"] = {"provider": provider.name, "warnings": warnings}
        merged["raw_parsed_data"] = raw_parsed_data
        return {
            **merged,
            "parse_mode": _ai_parse_mode(provider.name),
            "provider": provider.name,
            "parsing_status": str(merged.get("parsing_status") or "full"),
            "parsing_warnings": warnings,
        }

    fallback_warnings = warnings or ["AI parsing failed. Fell back to rule-based parsing."]
    return {
        **rule_based_result,
        "parse_mode": "rule_based",
        "provider": provider.name,
        "parsing_status": str(rule_based_result.get("parsing_status") or "full"),
        "parsing_warnings": fallback_warnings,
    }


def _build_partial_parse_result(
    *,
    url: str,
    fetched: dict[str, Any] | None,
    fallback_metadata: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    title = str(fallback_metadata.get("title") or "").strip() or "Unknown Title"
    company = str(fallback_metadata.get("company") or "").strip() or "Unknown Company"
    location = str(fallback_metadata.get("location") or "").strip() or "Unknown"
    source_type = str(fallback_metadata.get("source_type") or "url_slug_fallback")
    description = str(fallback_metadata.get("job_description") or "").strip() or PARTIAL_JOB_DESCRIPTION
    parser_description = "CareerAgent could not extract the full job description. Partial details were inferred from the URL."
    inferred_lines = [
        f"Company: {company}",
        f"Title: {title}",
        f"Location: {location}",
        parser_description,
    ]
    fetch_metadata = {
        "source_type": source_type,
        "inferred_fields": list(fallback_metadata.get("inferred_fields") or []),
        "fallback_metadata": {
            key: value
            for key, value in fallback_metadata.items()
            if key
            in {
                "site",
                "tenant",
                "location_slug",
                "title_slug",
                "api_url",
                "status_code",
                "source_type",
            }
        },
    }
    if fetched:
        fetch_metadata.update(
            {
                "domain": fetched.get("domain"),
                "final_url": fetched.get("final_url"),
                "status_code": fetched.get("status_code"),
                "page_title": fetched.get("page_title"),
                "h1": fetched.get("h1"),
                "meta_description": fetched.get("meta_description"),
                "source_type": source_type,
            }
        )

    result = _build_parse_result(
        "\n".join(inferred_lines),
        url=url,
        title_hint=title,
        fetch_metadata=fetch_metadata,
    )
    result.update(
        {
            "company": company,
            "title": title,
            "location": location,
            "source": str(fallback_metadata.get("source") or result.get("source") or "url"),
            "job_description": description,
            "parsing_status": "partial",
            "parsing_warnings": _unique_preserve_order(
                warnings + [PARTIAL_PARSE_WARNING, PASTE_DESCRIPTION_WARNING]
            ),
        }
    )
    raw_parsed_data = dict(result.get("raw_parsed_data") or {})
    raw_parsed_data["source_type"] = source_type
    raw_parsed_data["inferred_fields"] = list(fallback_metadata.get("inferred_fields") or [])
    result["raw_parsed_data"] = raw_parsed_data
    return result


def _build_full_parse_result(
    *,
    text: str,
    url: str,
    fetched: dict[str, Any],
    title_hint: str,
    source_type: str,
    warnings: list[str],
    source: str | None = None,
) -> dict[str, Any]:
    result = _build_parse_result(
        text,
        url=url,
        title_hint=title_hint,
        fetch_metadata={
            "domain": fetched.get("domain"),
            "final_url": fetched.get("final_url"),
            "status_code": fetched.get("status_code"),
            "page_title": fetched.get("page_title"),
            "h1": fetched.get("h1"),
            "meta_description": fetched.get("meta_description"),
            "source_type": source_type,
        },
    )
    if source:
        result["source"] = source
    result["parsing_status"] = "full"
    result["parsing_warnings"] = _unique_preserve_order(warnings)
    raw_parsed_data = dict(result.get("raw_parsed_data") or {})
    raw_parsed_data["source_type"] = source_type
    result["raw_parsed_data"] = raw_parsed_data
    return result


def fetch_job_url_text(url: str) -> dict[str, Any]:
    normalized_url = url.strip()
    if not normalized_url:
        raise ValueError("Job URL is empty. Paste a URL to parse.")

    parsed = urlparse(normalized_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Job URL must start with http:// or https://.")

    try:
        response = requests.get(
            normalized_url,
            headers=DEFAULT_HEADERS,
            timeout=FETCH_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError(f"Failed to fetch the job URL: {exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    embedded_page_data = _extract_embedded_page_data(soup)
    meta_description = (
        _meta_content(soup, name="description")
        or _meta_content(soup, property_name="og:description")
        or _meta_content(soup, name="twitter:description")
    )
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    page_title = _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    page_title = page_title or _meta_content(soup, property_name="og:title") or _meta_content(soup, name="twitter:title")
    h1 = _clean_text(soup.find("h1").get_text(" ", strip=True)) if soup.find("h1") else ""
    visible_text = "\n".join(_get_non_empty_lines(soup.get_text("\n", strip=True)))
    visible_text = visible_text.strip()
    warnings: list[str] = []
    if not _is_readable_text(visible_text):
        warnings.append(JS_HEAVY_FETCH_WARNING)

    return {
        "url": normalized_url,
        "final_url": response.url,
        "status_code": response.status_code,
        "domain": parsed.netloc,
        "page_title": page_title,
        "h1": h1,
        "visible_text": visible_text,
        "meta_description": meta_description,
        "json_ld": embedded_page_data["json_ld"],
        "embedded_text": embedded_page_data["embedded_text"],
        "source_type": "requests_html",
        "warnings": warnings,
    }


def parse_job_description(text: str, *, use_ai: bool = False, provider_name: str | None = None) -> dict[str, Any]:
    rule_based_result = _build_parse_result(text, url="")
    return _parse_with_optional_ai(
        rule_based_result=rule_based_result,
        cleaned_text=str(rule_based_result.get("job_description") or text),
        use_ai=use_ai,
        provider_name=provider_name,
    )


def parse_job_url(url: str, *, use_ai: bool = False, provider_name: str | None = None) -> dict[str, Any]:
    fetch_warnings: list[str] = []
    try:
        fetched = fetch_job_url_text(url)
    except ValueError as exc:
        if not is_workday_url(url):
            raise
        fetch_warnings.append(str(exc))
        fetched = {
            "url": url.strip(),
            "final_url": url.strip(),
            "domain": urlparse(url).netloc,
            "status_code": None,
            "page_title": "",
            "h1": "",
            "meta_description": "",
            "visible_text": "",
            "embedded_text": "",
            "json_ld": [],
            "warnings": fetch_warnings,
        }

    visible_text = str(fetched.get("visible_text") or "")
    embedded_text = str(fetched.get("embedded_text") or "")
    json_metadata = _extract_job_posting_metadata_from_json(list(fetched.get("json_ld") or []))
    final_url = str(fetched.get("final_url") or fetched.get("url") or url)
    title_hint = (
        str(fetched.get("h1") or "")
        or str(fetched.get("page_title") or "")
        or str(json_metadata.get("title") or "")
    )
    warnings = _unique_preserve_order(fetch_warnings + list(fetched.get("warnings") or []))
    source = "workday" if is_workday_url(final_url) else None

    if _is_readable_text(visible_text):
        rule_based_result = _build_full_parse_result(
            text=visible_text,
            url=str(fetched.get("url") or url),
            fetched=fetched,
            title_hint=title_hint,
            source_type="requests_html",
            warnings=[],
            source=source,
        )
    else:
        workday_api = try_workday_api_fetch(final_url) if is_workday_url(final_url) else {}
        workday_api_warnings = list(workday_api.get("warnings") or [])
        if _is_readable_text(str(workday_api.get("job_description") or "")):
            api_title_hint = str(workday_api.get("title") or title_hint)
            rule_based_result = _build_full_parse_result(
                text=str(workday_api["job_description"]),
                url=str(fetched.get("url") or url),
                fetched=fetched,
                title_hint=api_title_hint,
                source_type="workday_api",
                warnings=warnings + workday_api_warnings,
                source="workday",
            )
            for field in ["title", "company", "location"]:
                if workday_api.get(field):
                    rule_based_result[field] = workday_api[field]
        elif _is_readable_text(str(json_metadata.get("job_description") or "")):
            json_title_hint = str(json_metadata.get("title") or title_hint)
            rule_based_result = _build_full_parse_result(
                text=str(json_metadata["job_description"]),
                url=str(fetched.get("url") or url),
                fetched=fetched,
                title_hint=json_title_hint,
                source_type="json_ld",
                warnings=warnings,
                source=source,
            )
            for field in ["title", "company", "location"]:
                if json_metadata.get(field):
                    rule_based_result[field] = json_metadata[field]
        elif _is_readable_text(embedded_text):
            rule_based_result = _build_full_parse_result(
                text=embedded_text,
                url=str(fetched.get("url") or url),
                fetched=fetched,
                title_hint=title_hint,
                source_type="embedded_json",
                warnings=warnings,
                source=source,
            )
        else:
            if is_workday_url(final_url):
                fallback_metadata = extract_workday_metadata_from_url(final_url)
                fallback_metadata["warnings"] = workday_api_warnings
                warnings.extend(workday_api_warnings)
                warnings.append(WORKDAY_INFERENCE_WARNING)
            else:
                metadata_fallback = _parse_page_metadata_fallback(fetched, json_metadata)
                fallback_metadata = _parse_generic_url_slug(final_url)
                if fallback_metadata and metadata_fallback:
                    fallback_metadata = {
                        **metadata_fallback,
                        **fallback_metadata,
                        "company": fallback_metadata.get("company")
                        if fallback_metadata.get("company") != "Unknown Company"
                        else metadata_fallback.get("company"),
                        "location": fallback_metadata.get("location")
                        if fallback_metadata.get("location") != "Unknown"
                        else metadata_fallback.get("location"),
                        "inferred_fields": _unique_preserve_order(
                            list(metadata_fallback.get("inferred_fields") or [])
                            + list(fallback_metadata.get("inferred_fields") or [])
                        ),
                    }
                fallback_metadata = fallback_metadata or metadata_fallback

            if not fallback_metadata:
                raise ValueError(
                    "The fetched job page did not contain readable text to parse. "
                    "Open the job in a browser and paste the full job description text manually."
                )

            rule_based_result = _build_partial_parse_result(
                url=str(fetched.get("url") or url),
                fetched=fetched,
                fallback_metadata=fallback_metadata,
                warnings=warnings,
            )

    return _parse_with_optional_ai(
        rule_based_result=rule_based_result,
        cleaned_text=str(rule_based_result.get("job_description") or visible_text or embedded_text),
        use_ai=use_ai,
        provider_name=provider_name,
    )
