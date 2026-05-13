from __future__ import annotations

from typing import Any

from app.utils.text import normalize_whitespace

BAY_AREA_TERMS = {
    "bay area",
    "sf bay area",
    "san francisco bay area",
    "silicon valley",
    "san francisco",
    "sf",
    "south san francisco",
    "daly city",
    "brisbane",
    "san bruno",
    "millbrae",
    "burlingame",
    "san mateo",
    "foster city",
    "belmont",
    "san carlos",
    "redwood city",
    "menlo park",
    "atherton",
    "east palo alto",
    "palo alto",
    "mountain view",
    "los altos",
    "los altos hills",
    "sunnyvale",
    "santa clara",
    "san jose",
    "cupertino",
    "campbell",
    "saratoga",
    "los gatos",
    "milpitas",
    "morgan hill",
    "gilroy",
    "oakland",
    "berkeley",
    "emeryville",
    "alameda",
    "san leandro",
    "hayward",
    "union city",
    "fremont",
    "newark",
    "pleasanton",
    "dublin",
    "livermore",
    "san ramon",
    "danville",
    "walnut creek",
    "concord",
    "richmond",
    "el cerrito",
    "albany",
    "orinda",
    "lafayette",
    "moraga",
    "san rafael",
    "mill valley",
    "novato",
    "sausalito",
    "petaluma",
    "santa rosa",
    "napa",
    "vallejo",
    "benicia",
    "fairfield",
    "san francisco county",
    "san mateo county",
    "santa clara county",
    "alameda county",
    "contra costa county",
    "marin county",
    "sonoma county",
    "napa county",
    "solano county",
}

NON_BAY_CA_TERMS = {
    "los angeles",
    "santa monica",
    "irvine",
    "san diego",
    "sacramento",
    "santa barbara",
    "orange county",
    "pasadena",
    "burbank",
    "long beach",
    "riverside",
}

OTHER_US_TERMS = {
    "new york",
    "nyc",
    "seattle",
    "austin",
    "boston",
    "chicago",
    "denver",
    "miami",
    "atlanta",
    "washington dc",
    "washington, dc",
    "nashville",
    "portland",
    "dallas",
    "houston",
    "phoenix",
    "salt lake city",
    "raleigh",
}

INTERNATIONAL_TERMS = {
    "canada",
    "toronto",
    "vancouver",
    "london",
    "uk",
    "united kingdom",
    "europe",
    "india",
    "bangalore",
    "bengaluru",
    "singapore",
    "australia",
    "germany",
    "netherlands",
    "amsterdam",
    "france",
    "ireland",
    "poland",
    "portugal",
    "spain",
    "italy",
    "romania",
    "brazil",
    "mexico",
    "new zealand",
    "japan",
}

REMOTE_US_MARKERS = {
    "remote us",
    "remote usa",
    "remote - united states",
    "united states remote",
    "us remote",
    "usa remote",
    "remote, united states",
    "remote within united states",
    "anywhere in the u.s.",
    "anywhere in the us",
    "distributed, us",
    "remote, us",
    "remote (us)",
    "remote (usa)",
}

US_STATE_HINTS = {
    " al ",
    " ak ",
    " az ",
    " ar ",
    " ca ",
    " co ",
    " ct ",
    " de ",
    " fl ",
    " ga ",
    " hi ",
    " id ",
    " il ",
    " in ",
    " ia ",
    " ks ",
    " ky ",
    " la ",
    " ma ",
    " md ",
    " me ",
    " mi ",
    " mn ",
    " mo ",
    " ms ",
    " mt ",
    " nc ",
    " nd ",
    " ne ",
    " nh ",
    " nj ",
    " nm ",
    " nv ",
    " ny ",
    " oh ",
    " ok ",
    " or ",
    " pa ",
    " ri ",
    " sc ",
    " sd ",
    " tn ",
    " tx ",
    " ut ",
    " va ",
    " vt ",
    " wa ",
    " wi ",
    " wv ",
    " wy ",
}


def _norm(value: Any) -> str:
    return normalize_whitespace(str(value or "")).lower()


def _clean_location(value: Any) -> str:
    raw = normalize_whitespace(str(value or "")).strip()
    if not raw or raw.lower() in {"unknown", "n/a", "none", "null", "not specified"}:
        return ""
    return raw


def _contains_any(text: str, terms: set[str]) -> str:
    padded = f" {text.replace(',', ' ').replace(';', ' ')} "
    for term in sorted(terms, key=len, reverse=True):
        if term == "sf":
            if " sf " in padded or " sf bay area " in padded:
                return term
            continue
        if term in text:
            return term
    return ""


def _has_remote_us(text: str) -> bool:
    if _contains_any(text, REMOTE_US_MARKERS):
        return True
    return "remote" in text and any(term in text for term in ["united states", "usa", "u.s.", " us ", " u.s "])


def _has_us_hint(text: str) -> bool:
    padded = f" {text.replace(',', ' ').replace(';', ' ').replace('-', ' ')} "
    return (
        "united states" in text
        or "usa" in text
        or "u.s." in text
        or any(hint in padded for hint in US_STATE_HINTS)
        or bool(_contains_any(text, OTHER_US_TERMS))
        or bool(_contains_any(text, NON_BAY_CA_TERMS))
        or bool(_contains_any(text, BAY_AREA_TERMS))
    )


def _has_ca_state(text: str) -> bool:
    padded = f" {text.replace(',', ' ').replace(';', ' ').replace('-', ' ')} "
    return " ca " in padded


def classify_location_fit(location_text: str | None, description: str | None = None) -> dict[str, Any]:
    normalized_location = _clean_location(location_text)
    location_only = _norm(normalized_location)
    description_only = _norm(description)
    text = _norm(f"{normalized_location} {description or ''}")
    hybrid = "hybrid" in text
    remote = "remote" in text or "distributed" in text
    signals: list[str] = []
    reasons: list[str] = []

    unclear_locations = {"multiple locations", "various", "global", "hybrid", "remote", "not specified"}
    bay_signal = _contains_any(location_only, BAY_AREA_TERMS) or (
        (not normalized_location or location_only in unclear_locations) and _contains_any(description_only, BAY_AREA_TERMS)
    )
    if bay_signal:
        signals.append(bay_signal)
        reasons.append(f"Location matches Bay Area: {normalized_location or bay_signal}.")
        return {
            "location": normalized_location or bay_signal.title(),
            "normalized_location": normalized_location or bay_signal.title(),
            "location_fit": "bay_area",
            "remote_status": "hybrid" if hybrid else "remote" if remote and _has_remote_us(text) else "onsite",
            "confidence": 95,
            "signals": signals,
            "reasons": reasons,
        }

    if _has_remote_us(text):
        signals.append("remote_us")
        reasons.append(f"Remote US role: {normalized_location or 'Remote - United States'}.")
        return {
            "location": normalized_location or "Remote - United States",
            "normalized_location": normalized_location or "Remote - United States",
            "location_fit": "remote_us",
            "remote_status": "hybrid" if hybrid else "remote",
            "confidence": 92,
            "signals": signals,
            "reasons": reasons,
        }

    intl_signal = _contains_any(location_only, INTERNATIONAL_TERMS)
    if intl_signal:
        signals.append(intl_signal)
        reasons.append(f"Location appears international: {normalized_location}.")
        return {
            "location": normalized_location,
            "normalized_location": normalized_location,
            "location_fit": "international",
            "remote_status": "hybrid" if hybrid else "remote" if remote else "onsite",
            "confidence": 88,
            "signals": signals,
            "reasons": reasons,
        }

    ca_signal = _contains_any(location_only, NON_BAY_CA_TERMS)
    if ca_signal or ("california" in location_only and not bay_signal) or (_has_ca_state(location_only) and normalized_location):
        signals.append(ca_signal or "california")
        reasons.append(f"Location is non-Bay Area California: {normalized_location}.")
        return {
            "location": normalized_location,
            "normalized_location": normalized_location,
            "location_fit": "non_bay_area_california",
            "remote_status": "hybrid" if hybrid else "remote" if remote else "onsite",
            "confidence": 86 if ca_signal else 72,
            "signals": signals,
            "reasons": reasons,
        }

    us_signal = _contains_any(location_only, OTHER_US_TERMS)
    if us_signal or _has_us_hint(location_only):
        signals.append(us_signal or "us_location")
        reasons.append(f"Location is Other US: {normalized_location}.")
        return {
            "location": normalized_location,
            "normalized_location": normalized_location,
            "location_fit": "other_us",
            "remote_status": "hybrid" if hybrid else "remote" if remote else "onsite",
            "confidence": 82 if us_signal else 65,
            "signals": signals,
            "reasons": reasons,
        }

    if remote:
        signals.append("remote_unclear")
        reasons.append(f"Location appears remote but US eligibility is unclear: {normalized_location or 'Remote'}.")
        return {
            "location": normalized_location or "Remote",
            "normalized_location": normalized_location or "Remote",
            "location_fit": "unknown",
            "remote_status": "remote",
            "confidence": 55,
            "signals": signals,
            "reasons": reasons,
        }

    if not normalized_location:
        return {
            "location": "",
            "normalized_location": "",
            "location_fit": "unknown",
            "remote_status": "unknown",
            "confidence": 0,
            "signals": [],
            "reasons": ["Location is unknown, kept for review if unknown locations are allowed."],
        }

    return {
        "location": normalized_location,
        "normalized_location": normalized_location,
        "location_fit": "unknown",
        "remote_status": "hybrid" if hybrid else "unknown",
        "confidence": 45,
        "signals": [],
        "reasons": ["Location is unclear, so target fit cannot be confirmed."],
    }
