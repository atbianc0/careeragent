from __future__ import annotations

from typing import Any

from app.utils.text import normalize_whitespace

BAY_AREA_TERMS = {
    "bay area",
    "san francisco",
    "south san francisco",
    "oakland",
    "berkeley",
    "emeryville",
    "san mateo",
    "foster city",
    "palo alto",
    "menlo park",
    "mountain view",
    "sunnyvale",
    "santa clara",
    "san jose",
    "redwood city",
    "fremont",
    "silicon valley",
    "cupertino",
}

OUTSIDE_LOCATION_TERMS = {
    "new york",
    "boston",
    "seattle",
    "austin",
    "chicago",
    "los angeles",
    "denver",
    "atlanta",
    "dallas",
    "toronto",
    "amsterdam",
    "netherlands",
    "london",
    "india",
    "singapore",
    "canada",
    "united kingdom",
    "uk",
    "germany",
    "france",
    "ireland",
    "europe",
    "poland",
    "portugal",
    "spain",
    "italy",
    "romania",
    "brazil",
    "mexico",
    "australia",
    "new zealand",
    "japan",
}


def _norm(value: Any) -> str:
    return normalize_whitespace(str(value or "")).lower()


def _clean_location(value: Any) -> str:
    raw = normalize_whitespace(str(value or "")).strip()
    if not raw or raw.lower() in {"unknown", "n/a", "none", "null"}:
        return ""
    return raw


def classify_location_fit(location_text: str | None, description: str | None = None) -> dict[str, Any]:
    normalized_location = _clean_location(location_text)
    text = _norm(f"{normalized_location} {description or ''}")
    reasons: list[str] = []

    remote_markers = ["remote", "united states remote", "usa remote", "remote - united states", "remote, us", "remote us"]
    hybrid = "hybrid" in text
    remote = any(marker in text for marker in remote_markers)
    location_only = _norm(normalized_location)
    description_only = _norm(description)
    unclear_explicit_locations = {"multiple locations", "various", "global", "hybrid"}
    loc_has_bay = any(term in location_only for term in BAY_AREA_TERMS)
    desc_has_bay = any(term in description_only for term in BAY_AREA_TERMS)
    bay_area = loc_has_bay or ((not normalized_location or location_only in unclear_explicit_locations) and desc_has_bay)

    if bay_area and hybrid:
        reasons.append(f"Location matches Bay Area hybrid: {normalized_location or 'Bay Area'}.")
        return {
            "location": normalized_location or "Bay Area",
            "location_fit": "hybrid_bay_area",
            "remote_status": "hybrid",
            "confidence": 95,
            "reasons": reasons,
        }

    if bay_area:
        reasons.append(f"Location matches Bay Area: {normalized_location or 'Bay Area'}.")
        return {
            "location": normalized_location or "Bay Area",
            "location_fit": "bay_area",
            "remote_status": "hybrid" if hybrid else "onsite",
            "confidence": 95,
            "reasons": reasons,
        }

    if normalized_location and any(term in location_only for term in OUTSIDE_LOCATION_TERMS):
        reasons.append(f"Location appears outside target area: {normalized_location}.")
        return {
            "location": normalized_location,
            "location_fit": "outside_target",
            "remote_status": "hybrid" if hybrid else "remote" if remote else "onsite",
            "confidence": 85,
            "reasons": reasons,
        }

    if location_only in {"united states", "usa", "us", "u.s.", "united states of america"}:
        reasons.append(f"Location matches remote US: {normalized_location}.")
        return {
            "location": normalized_location,
            "location_fit": "remote_us",
            "remote_status": "remote" if remote else "unknown",
            "confidence": 80,
            "reasons": reasons,
        }

    if (
        normalized_location
        and location_only not in unclear_explicit_locations
        and "remote" not in location_only
        and "hybrid" not in location_only
        and not any(term in location_only for term in ["us", "usa", "united states", "u.s."])
    ):
        reasons.append(f"Location appears outside target area: {normalized_location}.")
        return {
            "location": normalized_location,
            "location_fit": "outside_target",
            "remote_status": "onsite",
            "confidence": 70,
            "reasons": reasons,
        }

    if remote and any(term in text for term in ["us", "usa", "united states", "u.s."]):
        reasons.append(f"Location matches remote US: {normalized_location or 'Remote - United States'}.")
        return {
            "location": normalized_location or "Remote - United States",
            "location_fit": "remote_us",
            "remote_status": "remote",
            "confidence": 90,
            "reasons": reasons,
        }

    if remote and not any(term in text for term in OUTSIDE_LOCATION_TERMS):
        reasons.append(f"Location appears remote but US eligibility is unclear: {normalized_location or 'Remote'}.")
        return {
            "location": normalized_location or "Remote",
            "location_fit": "unknown",
            "remote_status": "remote",
            "confidence": 55,
            "reasons": reasons,
        }

    if not normalized_location:
        return {
            "location": "",
            "location_fit": "unknown",
            "remote_status": "unknown",
            "confidence": 0,
            "reasons": ["Location is missing, so CareerAgent cannot confirm Bay Area fit."],
        }

    if any(term in text for term in OUTSIDE_LOCATION_TERMS):
        reasons.append(f"Location appears outside target area: {normalized_location}.")
        return {
            "location": normalized_location,
            "location_fit": "outside_target",
            "remote_status": "hybrid" if hybrid else "onsite",
            "confidence": 80,
            "reasons": reasons,
        }

    return {
        "location": normalized_location,
        "location_fit": "unknown",
        "remote_status": "hybrid" if hybrid else "unknown",
        "confidence": 45,
        "reasons": ["Location is unclear, so Bay Area fit cannot be confirmed."],
    }
