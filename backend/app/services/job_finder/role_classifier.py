from __future__ import annotations

import re
from typing import Any

from app.utils.text import normalize_whitespace


def _norm(value: Any) -> str:
    return normalize_whitespace(str(value or "")).lower()


def classify_role_category(title: str | None, description: str | None = None) -> dict[str, Any]:
    title_text = _norm(title)
    text = _norm(f"{title or ''} {description or ''}")

    checks = [
        ("Research Engineer", ["research engineer", "ai research engineer", "applied research"]),
        ("Data Engineer", ["data engineer", "data platform engineer", "data infrastructure engineer", "data platform", "data pipeline", "etl engineer"]),
        ("ML Engineer", ["machine learning engineer", "ml engineer", "ai engineer", "applied ai engineer", "deep learning", "computer vision", "nlp", "tensorrt"]),
        ("Data Scientist", ["data scientist", "applied scientist", "product scientist"]),
        ("Analytics Engineer", ["analytics engineer", "dbt", "semantic layer"]),
        ("Data Analyst", ["data analyst", "product analyst", "business intelligence analyst", "bi analyst"]),
    ]
    for category, terms in checks:
        for term in terms:
            if term in title_text or term in text:
                return {
                    "role_category": category,
                    "confidence": 90 if term in title_text else 70,
                    "reasons": [f"Title matched {category} because it contains '{term}'." if term in title_text else f"Description matched {category} because it mentions '{term}'."],
                }

    if "software engineer" in title_text and any(term in text for term in ["machine learning", "ml", "ai", "data", "platform", "infrastructure", "model"]):
        return {
            "role_category": "Software Engineer - Data/ML",
            "confidence": 75,
            "reasons": ["Title is Software Engineer and the posting includes data/ML/platform context."],
        }

    adjacent_checks = [
        ("Software Engineer", [r"\bsoftware engineer\b"]),
        ("Backend Engineer", [r"\bbackend engineer\b", r"\bback end engineer\b"]),
        ("Platform Engineer", [r"\bplatform engineer\b"]),
        ("Infrastructure Engineer", [r"\binfrastructure engineer\b", r"\bcloud engineer\b"]),
        ("Solutions Engineer - Data/AI", [r"\bsolutions engineer\b.*\b(?:data|ai|ml|analytics)\b", r"\b(?:data|ai|ml|analytics)\b.*\bsolutions engineer\b"]),
        ("Technical Analyst", [r"\btechnical analyst\b"]),
        ("Quantitative Analyst", [r"\bquantitative analyst\b", r"\bquant analyst\b"]),
    ]
    for category, patterns in adjacent_checks:
        if any(re.search(pattern, title_text) for pattern in patterns):
            return {
                "role_category": category,
                "confidence": 58,
                "reasons": [f"Title is an adjacent technical role: {category}."],
            }

    return {
        "role_category": "Other",
        "confidence": 30 if title_text else 0,
        "reasons": ["Title does not clearly match target data/ML/analytics roles."],
    }
