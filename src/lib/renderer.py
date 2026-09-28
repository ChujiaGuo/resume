"""LaTeX validation, section generation, and template rendering."""
from __future__ import annotations
import json
import re
from typing import Any
from urllib.parse import quote

from .config import ROOT
from .errors import WorkflowError
from .ollama import (
    _chat, _log_debug_prompt, _prompt_text, _read_text, _replace_tokens, _section_data_context,
)


_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
    "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "<": "$<$",
    ">":"$>$",
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


def _parse_section_response(raw: str, config: dict[str, Any]) -> dict[str, Any]:
    title = config["title"]
    try:
        result = json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"The {title} prompt did not return valid JSON: {exc}") from exc
    if not isinstance(result, dict):
        raise WorkflowError(f"The {title} response must be a JSON object")

    key = config["key"]
    if key == "skills":
        expected = {"languages", "frameworks", "developer_tools", "libraries"}
        if set(result) != expected:
            raise WorkflowError(f"The {title} response must contain exactly: {', '.join(sorted(expected))}")
        for field in expected:
            if not _string_list(result[field]):
                raise WorkflowError(f"The {title} field '{field}' must be an array of non-empty strings")
        return result

    if set(result) != {"entries"} or not isinstance(result["entries"], list):
        raise WorkflowError(f"The {title} response must contain an 'entries' array")
    entry_fields = {
        "education": {"institution", "location", "degree_and_field", "dates"},
        "experience": {"company", "dates", "role", "location", "bullets"},
        "projects": {"name", "dates", "role", "links", "bullets"},
    }[key]
    for index, entry in enumerate(result["entries"], 1):
        if not isinstance(entry, dict) or set(entry) != entry_fields:
            raise WorkflowError(f"The {title} entry {index} must contain exactly: {', '.join(sorted(entry_fields))}")
        for field in entry_fields - {"bullets", "links"}:
            if not isinstance(entry[field], str) or not entry[field].strip():
                raise WorkflowError(f"The {title} entry {index} field '{field}' must be a non-empty string")
        if "bullets" in entry and (not _string_list(entry["bullets"]) or len(entry["bullets"]) > 3):
            raise WorkflowError(f"The {title} entry {index} bullets must be an array of at most three non-empty strings")
        if "links" in entry:
            if not isinstance(entry["links"], list):
                raise WorkflowError(f"The Projects entry {index} links must be an array")
            for link_index, link in enumerate(entry["links"], 1):
                if not isinstance(link, dict) or set(link) != {"label", "url"}:
                    raise WorkflowError(f"The Projects entry {index} link {link_index} needs label and url strings")
                if any(not isinstance(link[name], str) or not link[name].strip() for name in ("label", "url")):
                    raise WorkflowError(f"The Projects entry {index} link {link_index} needs non-empty label and url strings")
    return result


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def _fill(template: str, values: dict[str, str]) -> str:
    for name, value in values.items():
        template = template.replace(f"[{name}]", value)
    return template.strip()


def _render_skills(template: str, data: dict[str, Any]) -> str:
    mapping = {
        "Languages": "languages",
        "Frameworks": "frameworks",
        "Developer Tools": "developer_tools",
        "Libraries": "libraries",
    }
    for placeholder, field in mapping.items():
        rendered = ", ".join(escape_latex(skill) for skill in data[field])
        template = template.replace(f"[{placeholder}]", rendered)
    return template.strip()


def _render_entries(template: str, section: str, entries: list[dict[str, Any]]) -> list[str]:
    rendered: list[str] = []
    for entry in entries:
        if section == "education":
            rendered.append(_fill(template, {
                "Institution": escape_latex(entry["institution"]),
                "Location": escape_latex(entry["location"]),
                "Degree and Field": escape_latex(entry["degree_and_field"]),
                "Start Date -- End Date": escape_latex(entry["dates"]),
            }))
            continue

        if section == "experience":
            fields = {
                "Company": escape_latex(entry["company"]),
                "Start Date -- End Date": escape_latex(entry["dates"]),
                "Role": escape_latex(entry["role"]),
                "Location": escape_latex(entry["location"]),
            }
        else:
            links = " $|$ ".join(
                rf"\href{{{quote(link['url'], safe=':/?=')}}}{{{escape_latex(link['label'])}}}"
                for link in entry["links"]
            )
            fields = {
                "Project Name": escape_latex(entry["name"]),
                "Start Date -- End Date": escape_latex(entry["dates"]),
                "Role": escape_latex(entry["role"]),
                "Project Links": links,
            }
        snippet = _fill(template, fields)
        bullets = "\n".join(r"  \resumeItem{" + escape_latex(bullet) + "}" for bullet in entry["bullets"])
        snippet = snippet.replace("    \\resumeItem{[Bullet 1]}\n    \\resumeItem{[Bullet 2]}\n    \\resumeItem{[Bullet 3]}", bullets)
        snippet = snippet.replace("  \\resumeItem{[Bullet 1]}\n  \\resumeItem{[Bullet 2]}\n  \\resumeItem{[Bullet 3]}", bullets)
        if not entry["bullets"]:
            # Empty bullet sets are valid JSON but provide no resume content.
            continue
        rendered.append(snippet.strip())
    return rendered


def populate_section(
    base: str,
    config: dict[str, Any],
    requirements_json: str,
    model: str,
    base_url: str,
    *,
    debug: bool = False,
) -> str:
    """Ask Ollama for structured content and append its locally rendered section."""
    for required_path in (config["prompt"], config["data"], config["template"]):
        if not required_path.exists():
            raise WorkflowError(f"Missing {config['title']} input: {required_path.relative_to(ROOT)}")

    prompt = _replace_tokens(
        _prompt_text(config["prompt"]),
        {"REQUIREMENTS_JSON": requirements_json, "SECTION_DATA": _section_data_context(config["data"])},
    )
    if debug:
        _log_debug_prompt(config["key"], prompt)
    response = _chat(
        base_url, model, prompt, format_schema=config["schema"], debug=debug,
        response_label=f"Ollama {config['title']} response",
    )
    data = _parse_section_response(response, config)
    template = _read_text(config["template"])
    if config["key"] == "skills":
        snippets = [_render_skills(template, data)]
    else:
        snippets = _render_entries(template, config["key"], data["entries"])
    if not snippets:
        return base

    section_parts: list[str] = []
    if config["list_wrapper"]:
        section_parts.extend((f"\\section{{{config['title']}}}", r"\resumeSubHeadingListStart"))
    section_parts.extend(snippets)
    if config["list_wrapper"]:
        section_parts.append(r"\resumeSubHeadingListEnd")
    return base.rstrip() + "\n\n" + "\n\n".join(section_parts) + "\n"
