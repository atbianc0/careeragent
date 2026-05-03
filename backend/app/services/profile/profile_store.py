from pathlib import Path
from shutil import copy2
from typing import Any

import yaml

from app.core.config import settings

PROFILE_GITHUB_SAFETY_NOTE = (
    "Your real profile should live in data/profile.yaml, which is ignored by Git. "
    "Do not store API keys, secrets, or other sensitive tokens in profile YAML."
)


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(settings.project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        parsed = yaml.safe_load(handle) or {}

    if not isinstance(parsed, dict):
        raise ValueError(f"Profile file must contain a YAML mapping: {_relative_path(path)}")

    return parsed


def _require_example_profile() -> Path:
    if settings.profile_example_path.exists():
        return settings.profile_example_path

    raise FileNotFoundError(
        "No profile file was found. Expected data/profile.yaml or data/profile.example.yaml."
    )


def load_profile_document() -> dict[str, Any]:
    if settings.profile_path.exists():
        return {
            "source": "private",
            "path": _relative_path(settings.profile_path),
            "profile": _load_yaml(settings.profile_path),
        }

    example_path = _require_example_profile()
    return {
        "source": "example",
        "path": _relative_path(example_path),
        "profile": _load_yaml(example_path),
    }


def save_profile_data(profile: dict[str, Any]) -> dict[str, Any]:
    settings.profile_path.parent.mkdir(parents=True, exist_ok=True)

    with settings.profile_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(profile, handle, sort_keys=False, allow_unicode=True)

    return {
        "source": "private",
        "path": _relative_path(settings.profile_path),
        "profile": profile,
        "message": "Saved profile data to the private local file.",
    }


def create_private_profile_from_example() -> dict[str, Any]:
    if settings.profile_path.exists():
        document = load_profile_document()
        document["message"] = "Private profile already exists."
        return document

    example_path = _require_example_profile()
    settings.profile_path.parent.mkdir(parents=True, exist_ok=True)
    copy2(example_path, settings.profile_path)

    document = load_profile_document()
    document["message"] = "Created data/profile.yaml from the safe public example template."
    return document


def get_profile_status() -> dict[str, Any]:
    private_exists = settings.profile_path.exists()
    example_exists = settings.profile_example_path.exists()

    if private_exists:
        active_source = "private"
    elif example_exists:
        active_source = "example"
    else:
        active_source = "missing"

    return {
        "private_profile_exists": private_exists,
        "example_profile_exists": example_exists,
        "active_source": active_source,
        "private_profile_path": _relative_path(settings.profile_path),
        "example_profile_path": _relative_path(settings.profile_example_path),
        "github_safety_note": PROFILE_GITHUB_SAFETY_NOTE,
    }

