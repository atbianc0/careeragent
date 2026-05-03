from __future__ import annotations

import re
from typing import Any


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(cleaned)
    return unique


def _build_priority_skills(job: Any, profile: dict[str, Any], scoring_evidence: dict[str, Any] | None) -> list[str]:
    profile_skills = [str(skill) for skill in (profile.get("skills") or [])]
    scoring_raw_data = dict(getattr(job, "scoring_raw_data", None) or {})
    matched_required = list(scoring_raw_data.get("matched_required_skills") or [])
    matched_preferred = list(scoring_raw_data.get("matched_preferred_skills") or [])
    required_skills = list(getattr(job, "required_skills", None) or [])
    preferred_skills = list(getattr(job, "preferred_skills", None) or [])

    summary_skills: list[str] = []
    if scoring_evidence:
        skill_match = dict(scoring_evidence.get("skill_match") or {})
        summary_skills.extend(skill_match.get("matched_required_skills") or [])
        summary_skills.extend(skill_match.get("matched_preferred_skills") or [])

    return _unique_preserve_order(
        matched_required + matched_preferred + summary_skills + required_skills + preferred_skills + profile_skills
    )


def _reorder_skill_items(items_text: str, priority_skills: list[str]) -> tuple[str, bool]:
    trailing_break = "\\\\" if items_text.rstrip().endswith("\\\\") else ""
    normalized_text = items_text.rstrip()
    if trailing_break:
        normalized_text = normalized_text[:-2].rstrip()

    items = [item.strip() for item in normalized_text.split(",")]
    items = [item for item in items if item]
    if len(items) < 2:
        return items_text, False

    priority_lookup = {skill.casefold(): index for index, skill in enumerate(priority_skills)}
    original_items = list(items)

    def sort_key(item: str) -> tuple[int, int, str]:
        lowered = item.casefold()
        for priority_skill, priority_index in priority_lookup.items():
            if priority_skill in lowered:
                return (0, priority_index, lowered)
        return (1, len(priority_lookup), lowered)

    reordered = sorted(items, key=sort_key)
    if reordered == original_items:
        return items_text, False

    updated = ", ".join(reordered)
    if trailing_break:
        updated = f"{updated} {trailing_break}"
    return updated, True


def _reorder_skill_section(content: str, priority_skills: list[str]) -> tuple[str, list[str]]:
    lines = content.splitlines()
    changes: list[str] = []

    skill_heading_index = None
    for index, line in enumerate(lines):
        if "\\textbf{\\large Skills}" in line:
            skill_heading_index = index
            break

    if skill_heading_index is None:
        return content, changes

    changed_any = False
    for index in range(skill_heading_index + 1, len(lines)):
        raw_line = lines[index]
        stripped = raw_line.strip()
        if not stripped:
            break
        if stripped.startswith("\\vspace") or "\\textbf{\\large" in stripped:
            break
        if ":" not in raw_line or "," not in raw_line:
            continue
        prefix, suffix = raw_line.split(":", 1)
        reordered, changed = _reorder_skill_items(suffix, priority_skills)
        if changed:
            lines[index] = f"{prefix}: {reordered.lstrip()}"
            changed_any = True

    if changed_any:
        changes.append("Reordered existing skills within the current skills section to surface the most job-relevant truthful matches first.")

    return "\n".join(lines), changes


def _insert_tailoring_comment(content: str, job: Any, priority_skills: list[str]) -> tuple[str, list[str]]:
    comment_lines = [
        "% CareerAgent Stage 6 tailoring context:",
        f"% Target role: {str(getattr(job, 'title', 'Unknown Title') or 'Unknown Title')} at {str(getattr(job, 'company', 'Unknown Company') or 'Unknown Company')}.",
    ]
    if priority_skills:
        comment_lines.append(f"% Relevant existing skills emphasized conservatively: {', '.join(priority_skills[:8])}.")
    comment_lines.append("% Resume structure and visual style preserved from the source document.")
    comment_block = "\n".join(comment_lines)

    marker = "\\begin{document}"
    if marker in content:
        updated = content.replace(marker, f"{comment_block}\n\n{marker}", 1)
    else:
        updated = f"{comment_block}\n\n{content}"
    return updated, ["Added a LaTeX comment documenting the tailoring target and preserved-structure rule."]


def generate_tailored_resume_source(
    base_resume_tex: str,
    job: Any,
    profile: dict[str, Any],
    scoring_evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    priority_skills = _build_priority_skills(job, profile, scoring_evidence)
    tailored_content, comment_changes = _insert_tailoring_comment(base_resume_tex, job, priority_skills)
    tailored_content, skill_changes = _reorder_skill_section(tailored_content, priority_skills)

    changes = _unique_preserve_order(comment_changes + skill_changes)
    if not changes:
        changes = ["Kept the resume content unchanged because no safe, deterministic content-only edits were identified."]

    unchanged = [
        "Kept the original LaTeX document structure and preamble.",
        "Kept the original section order, commands, spacing, fonts, and margins.",
        "Did not add new experience, companies, dates, titles, metrics, or tools.",
    ]
    safety_notes = [
        "No experience was invented.",
        "No new companies, dates, titles, metrics, or credentials were added.",
        "Tailoring was limited to conservative content-only edits inside the existing resume structure.",
    ]

    return {
        "content": tailored_content,
        "changes": changes,
        "unchanged": unchanged,
        "safety_notes": safety_notes,
    }
