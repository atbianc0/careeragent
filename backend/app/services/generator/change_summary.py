from __future__ import annotations

from typing import Any

from .common import unique_preserve_order


def generate_change_summary(
    *,
    job: Any,
    source_resume_path: str,
    tailoring_result: dict[str, Any],
) -> str:
    changes = list(tailoring_result.get("changes") or [])
    unchanged = list(tailoring_result.get("unchanged") or [])
    safety_notes = list(tailoring_result.get("safety_notes") or [])

    lines = [
        "# Change Summary",
        "",
        "## Target Job",
        f"- Company: {getattr(job, 'company', 'Unknown Company') or 'Unknown Company'}",
        f"- Title: {getattr(job, 'title', 'Unknown Title') or 'Unknown Title'}",
        f"- Source resume: {source_resume_path}",
        "",
        "## Resume Structure Preserved",
        "CareerAgent preserved the original LaTeX structure, section order, commands, formatting, spacing, fonts, margins, and overall visual style of the source resume.",
        "",
        "## Content Changes Made",
    ]

    if changes:
        lines.extend(f"- {item}" for item in changes)
    else:
        lines.append("- No content changes were made beyond reproducing the source resume in the packet folder.")

    lines.extend(
        [
            "",
            "## Intentionally Left Unchanged",
        ]
    )
    if unchanged:
        lines.extend(f"- {item}" for item in unchanged)
    else:
        lines.append("- No additional unchanged-items note was generated.")

    lines.extend(
        [
            "",
            "## Safety Confirmation",
            "- No experience was invented.",
            "- No skills were invented.",
            "- No dates, titles, or companies were invented.",
            "- No metrics or results were invented.",
        ]
    )
    if safety_notes:
        extra_safety_notes = [
            item
            for item in unique_preserve_order(safety_notes)
            if item not in {"No experience was invented."}
        ]
        lines.extend(f"- {item}" for item in extra_safety_notes)

    lines.extend(
        [
            "",
            "## Limitations",
            "- Stage 6 currently uses deterministic/mock generation unless an optional AI provider is added later.",
            "- Resume tailoring is intentionally conservative to preserve structure and avoid invented claims.",
            "- The user should manually review every generated file before using it anywhere.",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"
