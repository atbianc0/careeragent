from pathlib import Path

from app.core.config import settings


def resolve_resume_template_path() -> Path | None:
    for candidate in (settings.resume_path, settings.resume_example_path):
        if candidate.exists():
            return candidate
    return None


def compile_latex_resume_placeholder() -> dict[str, str]:
    active_template = resolve_resume_template_path()

    return {
        "status": "placeholder",
        "message": "LaTeX resume compilation will be implemented in a later stage.",
        "expected_private_resume_path": str(settings.resume_path),
        "fallback_template_path": str(settings.resume_example_path),
        "active_template_path": str(active_template) if active_template else "",
    }
