from __future__ import annotations

import re
from typing import Any

from app.utils.text import normalize_whitespace

EXPERIENCE_LEVELS = {"internship", "new_grad_entry", "early_career", "mid_level", "senior", "unknown"}
REQUIREMENT_STRENGTHS = {"required", "preferred", "minimum", "nice_to_have", "unknown"}

SENIOR_TITLE_RE = re.compile(
    r"\b(?:senior|sr\.?|staff|principal|lead|manager|director|architect|head of)\b",
    flags=re.IGNORECASE,
)
INTERN_TITLE_RE = re.compile(r"\b(?:internship|summer intern|student intern|intern|co-?op|coop)\b", flags=re.IGNORECASE)
NEW_GRAD_RE = re.compile(
    r"\b(?:new grad(?:uate)?|new college grad|university grad|recent graduate|early career|entry[- ]level|"
    r"junior|associate|software engineer i|data analyst i|data engineer i|class of 202[5-7]|graduating in 202[5-7])\b",
    flags=re.IGNORECASE,
)
MID_TITLE_RE = re.compile(r"\b(?:level ii|software engineer ii|data engineer ii|data scientist ii|experienced)\b", flags=re.IGNORECASE)

IGNORED_YEAR_CONTEXT_RE = re.compile(
    r"\b(?:team of|top|days?|offices?|products?|million|billion|founded|raised|series [a-z]|fortune\s*500|"
    r"401k|24/7|years?\s+ago|years?\s+old|years?\s+after|company has)\b",
    flags=re.IGNORECASE,
)
EXPERIENCE_CONTEXT_RE = re.compile(
    r"\b(?:experience|professional|relevant|software|engineering|engineer|data|machine learning|ml|analytics|"
    r"qualification|qualifications|required|requires|minimum|must have|preferred|nice to have|ideally|bonus)\b",
    flags=re.IGNORECASE,
)
PREFERRED_RE = re.compile(r"\b(?:preferred|ideally|nice to have|nice-to-have|bonus|plus|advantage)\b", flags=re.IGNORECASE)
REQUIRED_RE = re.compile(r"\b(?:required|requires|required:|must have|at least|minimum|basic qualifications?)\b", flags=re.IGNORECASE)
MINIMUM_RE = re.compile(r"\b(?:minimum|min\.|at least)\b", flags=re.IGNORECASE)
NO_EXPERIENCE_RE = re.compile(r"\b(?:no experience required|no prior experience|0\s+years?)\b", flags=re.IGNORECASE)
LESS_THAN_RE = re.compile(r"\bless than\s+([0-9]{1,2})\s+years?\b", flags=re.IGNORECASE)

YEAR_PATTERNS = [
    re.compile(
        r"\b(?P<min>[0-9]{1,2}(?:\.[0-9])?)\s*(?:-|to)\s*(?P<max>[0-9]{1,2}(?:\.[0-9])?)\s*\+?\s*"
        r"years?(?:\s+of)?(?:\s+(?:professional|relevant|software|engineering|data|machine learning|analytics))?"
        r"(?:\s+experience)?\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:minimum\s+|at least\s+|requires?\s+|required:?\s+)?(?P<min>[0-9]{1,2}(?:\.[0-9])?)\+?\s*"
        r"(?:or more\s+)?years?(?:\s+of)?(?:\s+(?:professional|relevant|software|engineering|data|machine learning|analytics))?"
        r"(?:\s+experience)?\b",
        flags=re.IGNORECASE,
    ),
]

BACHELORS_RE = re.compile(
    r"\b(?:bachelor(?:'s|s|’s)?(?:\s+degree)?|bs/ba|ba/bs|b\.?s\.?|b\.?a\.?|undergraduate degree|"
    r"4[- ]year degree|degree in (?:computer science|data science|statistics|engineering))\b",
    flags=re.IGNORECASE,
)
MASTERS_RE = re.compile(r"\b(?:master(?:'s|s|’s)?(?:\s+degree)?|m\.?s\.?|msc|graduate degree|advanced degree)\b", flags=re.IGNORECASE)
PHD_RE = re.compile(r"\b(?:ph\.?\s*d\.?|doctorate|doctoral degree)\b", flags=re.IGNORECASE)
EQUIVALENT_RE = re.compile(
    r"\b(?:or equivalent (?:practical |work )?experience|equivalent work experience|or related experience|commensurate experience)\b",
    flags=re.IGNORECASE,
)
DEGREE_REQUIRED_RE = re.compile(
    r"\b(?:required|requires|required:|must have|minimum qualifications?|basic qualifications?|"
    r"required qualifications?|minimum requirement|qualifications include|you have)\b",
    flags=re.IGNORECASE,
)
DEGREE_PREFERRED_RE = re.compile(
    r"\b(?:preferred|preferred qualifications?|nice to have|bonus|plus|ideally|desired|strong plus|advantage)\b",
    flags=re.IGNORECASE,
)
DEGREE_IGNORED_CONTEXT_RE = re.compile(
    r"\b(?:equal opportunity|reasonable accommodation|benefits?|401k|medical insurance|dental insurance|vision insurance)\b",
    flags=re.IGNORECASE,
)


def _norm(value: Any) -> str:
    return normalize_whitespace(str(value or "")).strip()


def _to_number(value: str) -> int | float:
    parsed = float(value)
    return int(parsed) if parsed.is_integer() else parsed


def _context(text: str, start: int, end: int, window: int = 100) -> str:
    return normalize_whitespace(text[max(0, start - window) : min(len(text), end + window)])


def _nearby_phrase(text: str, start: int, end: int) -> str:
    context = _context(text, start, end, window=70)
    return context[:220]


def _strength_from_context(context: str) -> str:
    if PREFERRED_RE.search(context):
        if re.search(r"\b(?:nice to have|nice-to-have|bonus|plus|advantage)\b", context, flags=re.IGNORECASE):
            return "nice_to_have"
        return "preferred"
    if MINIMUM_RE.search(context):
        return "minimum"
    if REQUIRED_RE.search(context):
        return "required"
    return "unknown"


def _experience_level_from_years(years_min: int | float | None, years_max: int | float | None) -> str:
    if years_min is None:
        return "unknown"
    if years_min <= 0 and years_max is not None and years_max <= 1:
        return "new_grad_entry"
    if years_min <= 0 and years_max is not None and years_max <= 2:
        return "early_career"
    if years_min <= 1:
        return "new_grad_entry"
    if years_min < 2:
        return "early_career"
    if years_min < 6:
        return "mid_level"
    return "senior"


def _experience_level_from_years_and_strength(
    years_min: int | float | None,
    years_max: int | float | None,
    strength: str,
) -> str:
    if years_min is None:
        return "unknown"
    if strength in {"preferred", "nice_to_have"}:
        if years_min <= 2:
            return "early_career"
        return "mid_level"
    if years_min >= 8:
        return "senior"
    if years_min >= 6 and strength in {"required", "minimum"}:
        return "senior"
    if years_min >= 6 and strength == "unknown":
        return "mid_level"
    return _experience_level_from_years(years_min, years_max)


def _find_year_requirement(text: str) -> dict[str, Any]:
    best: dict[str, Any] = {}

    less_than = LESS_THAN_RE.search(text)
    if less_than:
        max_years = _to_number(less_than.group(1))
        return {
            "years_min": 0,
            "years_max": max_years,
            "years_text": _nearby_phrase(text, less_than.start(), less_than.end()),
            "requirement_strength": _strength_from_context(_context(text, less_than.start(), less_than.end())),
            "signals": [less_than.group(0)],
        }

    no_exp = NO_EXPERIENCE_RE.search(text)
    if no_exp:
        return {
            "years_min": 0,
            "years_max": 0,
            "years_text": _nearby_phrase(text, no_exp.start(), no_exp.end()),
            "requirement_strength": "required",
            "signals": [no_exp.group(0)],
        }

    for pattern in YEAR_PATTERNS:
        for match in pattern.finditer(text):
            context = _context(text, match.start(), match.end())
            phrase = match.group(0)
            if IGNORED_YEAR_CONTEXT_RE.search(context):
                continue
            if not EXPERIENCE_CONTEXT_RE.search(context) and "experience" not in phrase.lower():
                continue
            years_min = _to_number(match.group("min"))
            years_max = _to_number(match.group("max")) if "max" in match.groupdict() and match.group("max") else None
            candidate = {
                "years_min": years_min,
                "years_max": years_max,
                "years_text": _nearby_phrase(text, match.start(), match.end()),
                "requirement_strength": _strength_from_context(context),
                "signals": [phrase],
            }
            if not best or (
                candidate["requirement_strength"] in {"required", "minimum"}
                and best.get("requirement_strength") not in {"required", "minimum"}
            ):
                best = candidate
    return best


def classify_experience_requirements(title: str | None, description: str | None) -> dict[str, Any]:
    title_text = _norm(title)
    text = _norm(f"{title or ''}\n{description or ''}")
    lower_text = text.lower()
    signals: list[str] = []
    reasons: list[str] = []

    year_result = _find_year_requirement(text)
    years_min = year_result.get("years_min")
    years_max = year_result.get("years_max")
    years_text = str(year_result.get("years_text") or "")
    strength = str(year_result.get("requirement_strength") or "unknown")
    signals.extend(str(signal) for signal in year_result.get("signals") or [])

    if INTERN_TITLE_RE.search(title_text):
        signals.append("internship title")
        reasons.append("Experience level is internship because the title contains intern/co-op language.")
        level = "internship"
        confidence = 96
    elif SENIOR_TITLE_RE.search(title_text):
        signals.append("senior title")
        reasons.append("Experience level is senior because the title contains senior/staff/principal/lead/manager language.")
        level = "senior"
        confidence = 96
    elif NEW_GRAD_RE.search(lower_text):
        matched = NEW_GRAD_RE.search(lower_text)
        if matched:
            signals.append(matched.group(0))
        if years_min == 0 and years_max is not None and years_max <= 2:
            level = "early_career"
            reasons.append("Experience requirement appears early-career because the posting asks for 0-2 years.")
        else:
            level = "new_grad_entry"
            reasons.append("Experience level appears entry/new-grad from title or description language.")
        confidence = 88
    elif years_min is not None:
        level = _experience_level_from_years_and_strength(years_min, years_max, strength)
        if level == "senior":
            reasons.append(f"Experience level appears senior because the posting asks for {years_min}+ years.")
        elif level == "mid_level":
            if strength in {"preferred", "nice_to_have"}:
                reasons.append(f"Experience requirement appears mid-level but {strength.replace('_', ' ')}: {signals[-1] if signals else years_text}.")
            else:
                reasons.append(f"Experience requirement appears mid-level from years requirement: {signals[-1] if signals else years_text}.")
        elif level == "early_career":
            reasons.append("Experience requirement appears low: 0-2 years.")
        else:
            reasons.append("Experience requirement appears entry-level.")
        confidence = 84 if strength != "unknown" else 74
    elif MID_TITLE_RE.search(lower_text):
        matched = MID_TITLE_RE.search(lower_text)
        if matched:
            signals.append(matched.group(0))
        reasons.append("Experience level appears mid-level from title/description level-II or experienced language.")
        level = "mid_level"
        confidence = 64
    else:
        level = "unknown"
        confidence = 35 if text else 0
        reasons.append("Experience level is unknown because no clear title or requirement signal was found.")

    if strength == "unknown" and (level in {"internship", "new_grad_entry", "early_career", "mid_level", "senior"}):
        strength = "unknown"

    return {
        "experience_level": level if level in EXPERIENCE_LEVELS else "unknown",
        "years_min": years_min,
        "years_max": years_max,
        "years_text": years_text,
        "requirement_strength": strength if strength in REQUIREMENT_STRENGTHS else "unknown",
        "confidence": confidence,
        "signals": list(dict.fromkeys(signals)),
        "reasons": reasons,
    }


def classify_experience_level(
    title: str | None,
    description: str | None,
    years_min: int | float | None = None,
    years_max: int | float | None = None,
) -> dict[str, Any]:
    result = classify_experience_requirements(title, description)
    if result["years_min"] is None and years_min is not None:
        result["years_min"] = years_min
        result["years_max"] = years_max
        result["experience_level"] = _experience_level_from_years(years_min, years_max)
        result["reasons"] = [f"Experience level inferred from normalized years: {years_min}{'-' + str(years_max) if years_max is not None else '+'} years."]
        result["confidence"] = max(int(result.get("confidence") or 0), 70)
    return result


def _degree_context(text: str, match: re.Match[str]) -> str:
    return _context(text, match.start(), match.end(), window=140)


def _degree_strength(context: str, *, equivalent: bool) -> str:
    if equivalent:
        return "equivalent_experience"

    preferred_matches = list(DEGREE_PREFERRED_RE.finditer(context))
    required_matches = list(DEGREE_REQUIRED_RE.finditer(context))
    if preferred_matches and required_matches:
        last_preferred = preferred_matches[-1].start()
        last_required = required_matches[-1].start()
        return "preferred" if last_preferred >= last_required else "required"
    if preferred_matches:
        return "preferred"
    if required_matches:
        return "required"
    return "accepted"


def _degree_entry(text: str, regex: re.Pattern[str], label: str) -> dict[str, Any] | None:
    match = None
    context = ""
    for candidate in regex.finditer(text):
        candidate_context = _degree_context(text, candidate)
        if DEGREE_IGNORED_CONTEXT_RE.search(candidate_context):
            continue
        match = candidate
        context = candidate_context
        break
    if not match:
        return None
    equivalent = bool(EQUIVALENT_RE.search(context))
    strength = _degree_strength(context, equivalent=equivalent)
    return {
        "level": label,
        "text": _nearby_phrase(text, match.start(), match.end()),
        "strength": strength,
        "required": bool(strength == "required" and not equivalent),
        "preferred": bool(strength == "preferred"),
        "equivalent": equivalent,
        "signal": match.group(0),
    }


def classify_degree_requirements(title: str | None, description: str | None) -> dict[str, Any]:
    text = _norm(f"{title or ''}\n{description or ''}")
    if not text:
        return {
            "degree_level": "unknown",
            "degree_requirement_strength": "unknown",
            "masters_required": False,
            "phd_required": False,
            "bachelors_required": False,
            "degree_text": "",
            "confidence": 0,
            "signals": [],
            "reasons": ["Degree requirement is unknown because the posting text is empty."],
        }

    phd = _degree_entry(text, PHD_RE, "phd")
    masters = _degree_entry(text, MASTERS_RE, "masters")
    bachelors = _degree_entry(text, BACHELORS_RE, "bachelors")
    entries = [entry for entry in [phd, masters, bachelors] if entry]

    if not entries:
        return {
            "degree_level": "none_mentioned",
            "degree_requirement_strength": "unknown",
            "masters_required": False,
            "phd_required": False,
            "bachelors_required": False,
            "degree_text": "",
            "confidence": 70,
            "signals": [],
            "reasons": ["No strict degree requirement found."],
        }

    phd_required = bool(phd and phd["required"])
    masters_required = bool(masters and masters["required"] and not phd_required)
    bachelors_required = bool(bachelors and bachelors["required"] and not masters_required and not phd_required)

    selected = phd or masters or bachelors
    if phd_required:
        selected = phd
    elif masters_required:
        selected = masters
    elif phd and phd["preferred"]:
        selected = phd
    elif masters and masters["preferred"]:
        selected = masters
    elif bachelors:
        selected = bachelors

    degree_level = str(selected["level"])
    strength = str(selected["strength"])
    if masters_required or phd_required or bachelors_required:
        strength = "required"

    reasons: list[str] = []
    if phd_required:
        reasons.append("PhD is required by the posting.")
    elif masters_required:
        reasons.append("Master's degree is required by the posting.")
    elif bachelors and bachelors["equivalent"]:
        reasons.append("Degree requirement is Bachelor's or equivalent experience.")
    elif degree_level == "masters" and strength == "preferred":
        reasons.append("Master's is preferred, not required.")
    elif degree_level == "phd" and strength == "preferred":
        reasons.append("PhD is preferred, not required.")
    elif degree_level == "bachelors":
        reasons.append("Bachelor's degree is required or accepted.")
    else:
        reasons.append("Degree requirement was detected but is not clearly required or preferred.")

    return {
        "degree_level": degree_level,
        "degree_requirement_strength": strength,
        "masters_required": masters_required,
        "phd_required": phd_required,
        "bachelors_required": bachelors_required,
        "degree_text": str(selected.get("text") or ""),
        "confidence": 88 if (masters_required or phd_required or bachelors_required or strength != "accepted") else 76,
        "signals": [str(entry["signal"]) for entry in entries],
        "reasons": reasons,
    }
