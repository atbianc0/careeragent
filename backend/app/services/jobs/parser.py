import re
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.utils.text import normalize_whitespace

DEFAULT_HEADERS = {
    "User-Agent": (
        "CareerAgent/0.5 Rule-Based Job Parser "
        "(safe rule-based fetch; no browser automation)"
    )
}
FETCH_TIMEOUT_SECONDS = 10
KNOWN_HOSTING_DOMAINS = {
    "ashbyhq.com",
    "boards.greenhouse.io",
    "greenhouse.io",
    "jobs.ashbyhq.com",
    "jobs.lever.co",
    "lever.co",
    "myworkdayjobs.com",
    "workday.com",
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
        ("ML Engineer", ["ml engineer", "machine learning engineer", "ai engineer"]),
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
    if any(keyword in haystack for keyword in ["new grad", "new graduate", "recent graduate", "university graduate"]):
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
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    page_title = _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    h1 = _clean_text(soup.find("h1").get_text(" ", strip=True)) if soup.find("h1") else ""
    visible_text = "\n".join(_get_non_empty_lines(soup.get_text("\n", strip=True)))
    visible_text = visible_text.strip()

    if not visible_text:
        raise ValueError("The fetched job page did not contain readable text to parse.")

    return {
        "url": normalized_url,
        "domain": parsed.netloc,
        "page_title": page_title,
        "h1": h1,
        "visible_text": visible_text,
    }


def parse_job_description(text: str) -> dict[str, Any]:
    return _build_parse_result(text, url="")


def parse_job_url(url: str) -> dict[str, Any]:
    fetched = fetch_job_url_text(url)
    title_hint = fetched["h1"] or fetched["page_title"]
    return _build_parse_result(
        fetched["visible_text"],
        url=fetched["url"],
        title_hint=title_hint,
        fetch_metadata={
            "domain": fetched["domain"],
            "page_title": fetched["page_title"],
            "h1": fetched["h1"],
        },
    )
