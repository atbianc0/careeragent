from pathlib import Path

import yaml
from fastapi import APIRouter

from app.core.config import settings
from app.schemas.profile import ProfileResponse

router = APIRouter()


def _default_profile() -> dict:
    return {
        "personal": {"name": "", "email": "", "phone": "", "location": ""},
        "education": {
            "school": "UC Berkeley",
            "degree": "Data Science",
            "graduation": "May 2026",
        },
        "links": {"linkedin": "", "github": "", "portfolio": ""},
        "target_roles": [
            "Data Scientist",
            "Data Engineer",
            "ML Engineer",
            "Analytics Engineer",
            "Data Analyst",
        ],
        "skills": [
            "Python",
            "SQL",
            "Pandas",
            "NumPy",
            "scikit-learn",
            "PyTorch",
            "TensorFlow",
            "Docker",
            "Git",
            "Linux",
        ],
        "application_defaults": {
            "work_authorized_us": True,
            "need_sponsorship_now": False,
            "need_sponsorship_future": False,
            "willing_to_relocate": True,
            "preferred_locations": ["Bay Area", "California", "Remote"],
        },
        "question_policy": {
            "answer_work_authorization": True,
            "answer_sponsorship": True,
            "answer_relocation": True,
            "answer_salary_expectation": "draft_only",
            "answer_demographic_questions": "prefer_not_to_answer",
            "never_lie": True,
        },
        "writing_style": {
            "tone": "direct, simple, specific, not overly corporate",
            "avoid": [
                "fake-polished language",
                "exaggeration",
                "made-up experience",
            ],
        },
    }


def load_profile_from_yaml(paths: list[Path]) -> dict:
    for path in paths:
        if not path.exists():
            continue

        with path.open("r", encoding="utf-8") as handle:
            parsed = yaml.safe_load(handle) or {}

        return parsed or _default_profile()

    return _default_profile()


@router.get("", response_model=ProfileResponse)
def get_profile() -> ProfileResponse:
    return load_profile_from_yaml([settings.profile_path, settings.profile_example_path])
