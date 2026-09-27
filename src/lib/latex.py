"""LaTeX escaping and validation for generated resume documents."""
from __future__ import annotations
import json
import re
from typing import Any
from .errors import WorkflowError


_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
    "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}


def escape_latex(text: str) -> str:
    """Escape LaTeX-special characters in plain text (never in markup)."""
    if not isinstance(text, str):
        raise TypeError("escape_latex expects a string")
    return "".join(_LATEX_ESCAPES.get(char, char) for char in text)


def _strip_code_fence(text: str) -> str:
    match = re.fullmatch(r"\s*```[\w-]*\s*\n(.*?)\n```\s*", text, flags=re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def _validate_requirements(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"Requirement extraction did not return valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowError("Requirement extraction must return a JSON object")
    for key in ("role", "company", "location"):
        if not isinstance(value.get(key), str):
            raise WorkflowError(f"Requirements JSON field '{key}' must be a string")
    for key in ("minimum_requirements", "preferred_requirements", "notes"):
        if not isinstance(value.get(key), list):
            raise WorkflowError(f"Requirements JSON field '{key}' must be an array")
    for list_name in ("minimum_requirements", "preferred_requirements"):
        for item in value[list_name]:
            if not isinstance(item, dict) or not all(
                isinstance(item.get(field), str) for field in ("id", "category", "requirement", "evidence")
            ):
                raise WorkflowError(f"Each item in '{list_name}' needs string id, category, requirement, and evidence fields")
    if not all(isinstance(note, str) for note in value["notes"]):
        raise WorkflowError("Every item in requirements JSON 'notes' must be a string")
    return value


def _validate_latex(source: str) -> str:
    source = _strip_code_fence(source).lstrip("\ufeff\n\r\t ")
    document = re.sub(r"\A% Generated: [^\n]*\n", "", source, count=1)
    if not document.startswith(r"\documentclass") or not source.rstrip().endswith(r"\end{document}"):
        raise WorkflowError("Tailoring response is not a complete LaTeX document")
    placeholders = re.findall(
        r"\[(?:Name|Email|Phone|LinkedIn|GitHub|Website|Institution|Degree and Field|Languages|Frameworks|"
        r"Tools and Practices|Libraries|Company|Role|Location|Start Date[^]]*|Project Name|Project Links|Bullet \d)\]",
        source,
    )
    if placeholders:
        raise WorkflowError("Tailoring response still contains template placeholders: " + ", ".join(sorted(set(placeholders))))
    _validate_bullet_limits(source, "Experience", "Projects")
    _validate_bullet_limits(source, "Projects", None)
    return source.rstrip() + "\n"


def _validate_bullet_limits(source: str, section: str, next_section: str | None) -> None:
    start = source.find(f"\\section{{{section}}}")
    if start < 0:
        return
    start += len(f"\\section{{{section}}}")
    end = source.find(f"\\section{{{next_section}}}", start) if next_section else source.find(r"\end{document}", start)
    if end < 0:
        end = len(source)
    content = source[start:end]
    heading = r"\\resumeExperienceHeading" if section == "Experience" else r"\\resumeProjectHeading"
    starts = [match.start() for match in re.finditer(heading, content)]
    for index, entry_start in enumerate(starts):
        entry_end = starts[index + 1] if index + 1 < len(starts) else len(content)
        count = len(re.findall(r"\\resumeItem\s*\{", content[entry_start:entry_end]))
        if count > 3:
            raise WorkflowError(f"{section} entry {index + 1} has {count} bullets; the maximum is 3")
