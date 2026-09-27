"""End-to-end local resume tailoring using Ollama's HTTP API."""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from html import unescape as html_unescape
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "gemma4:12b"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
RESUME_NAME = "Chujia_Guo_Software_Engineering_Resume.tex"
REQUIREMENTS_PROMPT = ROOT / "src/prompts/01-extract-job-requirements.md"
RESUME_DATA = ROOT / "resume_data"
TEMPLATES = ROOT / "templates"
BASE_RESUME_TEMPLATE = TEMPLATES / "00-resume-template.tex"
SECTION_CONFIGS = (
    {
        "key": "education",
        "title": "Education",
        "prompt": ROOT / "src/prompts/02-education.md",
        "data": RESUME_DATA / "education",
        "template": TEMPLATES / "01-education-template.tex",
        "list_wrapper": True,
    },
    {
        "key": "skills",
        "title": "Technical Skills",
        "prompt": ROOT / "src/prompts/03-skills.md",
        "data": RESUME_DATA / "skills.md",
        "template": TEMPLATES / "02-skills-template.tex",
        "list_wrapper": False,
    },
    {
        "key": "experience",
        "title": "Experience",
        "prompt": ROOT / "src/prompts/04-experience.md",
        "data": RESUME_DATA / "experience",
        "template": TEMPLATES / "03-experience-template.tex",
        "list_wrapper": True,
    },
    {
        "key": "projects",
        "title": "Projects",
        "prompt": ROOT / "src/prompts/05-projects.md",
        "data": RESUME_DATA / "projects",
        "template": TEMPLATES / "04-projects-template.tex",
        "list_wrapper": True,
    },
)


class WorkflowError(RuntimeError):
    """An actionable workflow or Ollama API error."""


class _TeeTextIO:
    """Copy text written to the wrapper to both the original stream and a log file."""

    def __init__(self, *streams: Any) -> None:
        self.streams = streams

    def write(self, text: str) -> int:
        for stream in self.streams:
            stream.write(text)
        return len(text)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()

    def isatty(self) -> bool:
        return any(stream.isatty() for stream in self.streams if hasattr(stream, "isatty"))


def _log_debug_prompt(label: str, prompt: str) -> None:
    print(f"\n--- rendered {label} prompt ---", flush=True)
    print(prompt, flush=True)
    print(f"--- end rendered {label} prompt ---\n", flush=True)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        try:
            display_path = path.relative_to(ROOT)
        except ValueError:
            display_path = path
        raise WorkflowError(f"Cannot read {display_path}: {exc}") from exc


def _prompt_text(path: Path) -> str:
    raw = _read_text(path)
    match = re.search(r"```[\w-]*\s*\n(.*?)\n```", raw, flags=re.DOTALL)
    if not match:
        raise WorkflowError(f"No fenced prompt body found in {path.relative_to(ROOT)}")
    return match.group(1)


def _replace_tokens(template: str, values: dict[str, str]) -> str:
    token_pattern = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
    unresolved = sorted(set(token_pattern.findall(template)) - values.keys())
    if unresolved:
        raise WorkflowError("Unfilled prompt token(s): " + ", ".join("{{" + token + "}}" for token in unresolved))
    return token_pattern.sub(lambda match: values[match.group(1)], template)


def _files_as_context(folder: Path, extensions: set[str]) -> str:
    files = sorted(path for path in folder.rglob("*") if path.is_file() and path.suffix in extensions)
    if not files:
        raise WorkflowError(f"No input files found under {folder.relative_to(ROOT)}")
    parts: list[str] = []
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        parts.append(f"===== {relative} =====\n{_read_text(path).rstrip()}\n")
    return "\n".join(parts)


def _http_json(
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 3600,
    *,
    debug: bool = False,
    response_label: str = "Ollama response",
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method="GET" if data is None else "POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise WorkflowError(f"Ollama returned HTTP {exc.code} for {url}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise WorkflowError(
            f"Could not reach Ollama at {url}: {exc}. Start Ollama and check its default local API port 11434."
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"Ollama returned invalid JSON from {url}: {exc}") from exc
    if not isinstance(result, dict):
        raise WorkflowError(f"Ollama returned an unexpected response from {url}")
    if debug:
        print(f"\n--- {response_label} ---", flush=True)
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        print(f"--- end {response_label} ---\n", flush=True)
    return result


def _ensure_model(base_url: str, model: str, *, debug: bool = False) -> None:
    result = _http_json(
        f"{base_url.rstrip('/')}/api/tags",
        timeout=10,
        debug=debug,
        response_label="Ollama model-list response",
    )
    available = result.get("models", [])
    names = {entry.get("name", "") for entry in available if isinstance(entry, dict)}
    if model not in names and f"{model}:latest" not in names:
        installed = ", ".join(sorted(name for name in names if name)) or "(none)"
        raise WorkflowError(
            f"Model '{model}' is not installed in Ollama. Install it with `ollama pull {model}`. "
            f"Installed models: {installed}"
        )


def _chat(
    base_url: str,
    model: str,
    prompt: str,
    *,
    json_mode: bool = False,
    format_schema: dict[str, Any] | None = None,
    debug: bool = False,
    response_label: str = "Ollama chat response",
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {"temperature": 0.1, "num_predict": 12000},
    }
    if format_schema is not None:
        payload["format"] = format_schema
    elif json_mode:
        payload["format"] = "json"
    response = _http_json(
        f"{base_url.rstrip('/')}/api/chat",
        payload,
        debug=debug,
        response_label=response_label,
    )
    message = response.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise WorkflowError("Ollama returned an empty response")
    return content.strip()


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


def _validate_template_array(raw: str, section: str) -> list[str]:
    # A model may emit a LaTeX command with one backslash inside JSON. In
    # particular, JSON treats ``\r`` in ``\resume...`` as a carriage return.
    # Repair unescaped LaTeX command slashes before decoding so the command is
    # not silently corrupted by json.loads(). Already doubled slashes are left
    # alone.
    raw = re.sub(
        r"(?<!\\)\\(?=(?:resume[A-Za-z]*|section|begin|end|small|textbf|textit|href|underline|vspace|item|"
        r"faGithub|faLink|scshape)\b)",
        r"\\\\",
        _strip_code_fence(raw),
    )
    try:
        values = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"The {section} prompt did not return valid JSON: {exc}") from exc
    if not isinstance(values, list) or not all(isinstance(value, str) and value.strip() for value in values):
        raise WorkflowError(f"The {section} prompt must return a JSON array of non-empty LaTeX strings")
    values = _group_project_snippets(values, section)
    values = [_escape_latex_text_specials(value) for value in values]
    for index, value in enumerate(values, start=1):
        if re.search(
            r"\[(?:Name|Email|Phone|LinkedIn|GitHub|Website|Institution|Degree and Field|Languages|Frameworks|"
            r"Tools and Practices|Libraries|Company|Role|Location|Start Date[^]]*|Project Name|Project Links|Bullet \d)\]",
            value,
        ):
            raise WorkflowError(f"The {section} prompt left an unfilled placeholder in array item {index}")
        _validate_section_snippet(value, section, index)
    return [value.strip() for value in values]


def _group_project_snippets(values: list[str], section: str) -> list[str]:
    """Reassemble project snippets when the model splits one project across array items."""
    if section != "Projects":
        return values

    grouped: list[str] = []
    current: list[str] = []
    for value in values:
        if value.lstrip().startswith(r"\resumeProjectHeading"):
            if current:
                raise WorkflowError("The Projects prompt started a new project before ending the previous project's bullet list")
            current = [value]
        elif current:
            current.append(value)
        else:
            raise WorkflowError("The Projects prompt returned content before a project heading")

        if current and r"\resumeItemListEnd" in value:
            grouped.append("\n".join(current))
            current = []

    if current:
        raise WorkflowError("The Projects prompt returned a project without resumeItemListEnd")
    return grouped


def _escape_latex_text_specials(value: str) -> str:
    """Escape text-only LaTeX specials in a returned snippet."""
    value = html_unescape(value)
    value = re.sub(r"\\n(?=\\resume)", "\n", value).replace(r"\>", ">")
    result: list[str] = []
    backslashes = 0
    in_math = False
    for char in value:
        if char == "$" and backslashes % 2 == 0:
            in_math = not in_math
            result.append(char)
        elif char in "<>" and not in_math:
            result.append("$<$" if char == "<" else "$>$")
        elif char in "&%" and backslashes % 2 == 0:
            result.append("\\" + char)
        else:
            result.append(char)
        backslashes = backslashes + 1 if char == "\\" else 0
    return "".join(result)


def _validate_section_snippet(value: str, section: str, index: int) -> None:
    """Reject malformed model snippets before they are assembled into a document."""
    prefix = f"The {section} prompt returned invalid LaTeX in array item {index}: "
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise WorkflowError(prefix + "contains an unexpected control character")
    if re.search(r"&(?:amp|lt|gt|quot);", value):
        raise WorkflowError(prefix + "contains an HTML entity; use LaTeX escaping instead")

    # Unescaped percent starts a TeX comment; unescaped ampersand is an
    # alignment separator and is only valid in the template's own tabulars.
    if re.search(r"(?<!\\)(?:\\\\)*%", value):
        raise WorkflowError(prefix + "contains an unescaped percent sign")
    if re.search(r"(?<!\\)(?:\\\\)*&", value):
        raise WorkflowError(prefix + "contains an unescaped ampersand")

    depth = 0
    escaped = False
    for char in value:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                raise WorkflowError(prefix + "has an unmatched closing brace")
    if depth:
        raise WorkflowError(prefix + "has unmatched braces")

    if section == "Education":
        if not re.match(r"\s*\\resumeEducationHeading\b", value):
            raise WorkflowError(prefix + "must start with \\resumeEducationHeading")
    elif section == "Experience":
        if not re.match(r"\s*\\resumeExperienceHeading\b", value):
            raise WorkflowError(prefix + "must start with \\resumeExperienceHeading")
        if value.count(r"\resumeItemListStart") != 1 or value.count(r"\resumeItemListEnd") != 1:
            raise WorkflowError(prefix + "must contain one complete resumeItemListStart/resumeItemListEnd pair")
    elif section == "Projects":
        if not re.match(r"\s*\\resumeProjectHeading\b", value):
            raise WorkflowError(prefix + "must start with \\resumeProjectHeading")
        if value.count(r"\resumeItemListStart") != 1 or value.count(r"\resumeItemListEnd") != 1:
            raise WorkflowError(prefix + "must contain one complete resumeItemListStart/resumeItemListEnd pair")
    elif section == "Technical Skills":
        if not re.match(r"\s*\\section\{Technical Skills\}", value):
            raise WorkflowError(prefix + "must contain the complete Technical Skills section")
        if r"\begin{small}" in value or r"\small{\item{" not in value:
            raise WorkflowError(prefix + "must preserve the template's \\small{\\item{...}} structure")


def _section_data_context(path: Path) -> str:
    if path.is_dir():
        return _files_as_context(path, {".md"})
    return f"===== {path.relative_to(ROOT).as_posix()} =====\n{_read_text(path).rstrip()}\n"


def populate_section(
    base: str,
    config: dict[str, Any],
    requirements_json: str,
    model: str,
    base_url: str,
    *,
    debug: bool = False,
) -> str:
    """Ask Ollama for filled entry templates and append that section to the LaTeX base."""
    for required_path in (config["prompt"], config["data"], config["template"]):
        if not required_path.exists():
            raise WorkflowError(f"Missing {config['title']} input: {required_path.relative_to(ROOT)}")

    prompt = _replace_tokens(
        _prompt_text(config["prompt"]),
        {
            "REQUIREMENTS_JSON": requirements_json,
            "SECTION_DATA": _section_data_context(config["data"]),
            "SECTION_TEMPLATE": _read_text(config["template"]),
        },
    )
    if debug:
        _log_debug_prompt(f"{config['key']}", prompt)
    entries = _validate_template_array(
        _chat(
            base_url,
            model,
            prompt,
            format_schema={"type": "array", "items": {"type": "string"}},
            debug=debug,
            response_label=f"Ollama {config['title']} response",
        ),
        config["title"],
    )
    if not entries:
        return base

    section_parts: list[str] = []
    if config["list_wrapper"]:
        section_parts.extend((f"\\section{{{config['title']}}}", r"\resumeSubHeadingListStart"))
    section_parts.extend(entries)
    if config["list_wrapper"]:
        section_parts.append(r"\resumeSubHeadingListEnd")
    return base.rstrip() + "\n\n" + "\n\n".join(section_parts) + "\n"


def _safe_slug(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug or "job"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    suffix = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{suffix}{path.suffix}")
        if not candidate.exists():
            return candidate
        suffix += 1


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise WorkflowError(f"Cannot write {path.relative_to(ROOT)}: {exc}") from exc


def _validate_latex(source: str) -> str:
    source = _strip_code_fence(source)
    source = source.lstrip("\ufeff\n\r\t ")
    if not source.startswith("\\documentclass") or not source.rstrip().endswith("\\end{document}"):
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
    end = source.find(f"\\section{{{next_section}}}", start) if next_section else source.find("\\end{document}", start)
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


def _compile_resume(resume_path: Path, *, debug: bool = False) -> None:
    if shutil.which("latexmk") is None:
        raise WorkflowError("`latexmk` is not installed or is not available on PATH")
    result = subprocess.run(
        ["latexmk", resume_path.name],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if debug and result.stdout:
        print("--- latexmk output ---", flush=True)
        print(result.stdout.rstrip(), flush=True)
        print("--- end latexmk output ---", flush=True)
    if result.returncode != 0:
        details = result.stdout.strip() or "No compiler output was captured."
        raise WorkflowError(f"LaTeX compilation failed (exit {result.returncode}):\n{details}")


def run(job_description_path: Path, model: str, base_url: str, *, debug: bool = False) -> tuple[Path, Path]:
    job_description = _read_text(job_description_path)
    if not job_description.strip():
        raise WorkflowError(f"Job description is empty: {job_description_path}")
    if not BASE_RESUME_TEMPLATE.is_file():
        raise WorkflowError(f"Resume template is missing: {BASE_RESUME_TEMPLATE}")
    missing_inputs = [
        path
        for config in SECTION_CONFIGS
        for path in (config["prompt"], config["data"], config["template"])
        if not path.exists()
    ]
    if missing_inputs:
        missing = ", ".join(path.relative_to(ROOT).as_posix() for path in missing_inputs)
        raise WorkflowError(f"Section inputs are not ready yet: {missing}")

    print(f"Checking local Ollama model '{model}'...", flush=True)
    _ensure_model(base_url, model, debug=debug)

    print("Extracting job requirements...", flush=True)
    extraction_prompt = _replace_tokens(_prompt_text(REQUIREMENTS_PROMPT), {"JOB_DESCRIPTION": job_description})
    if debug:
        _log_debug_prompt("requirements-extraction", extraction_prompt)
    requirements = _validate_requirements(
        _chat(
            base_url,
            model,
            extraction_prompt,
            json_mode=True,
            debug=debug,
            response_label="Ollama requirements-extraction response",
        )
    )

    run_date = date.today().isoformat()
    company_slug = _safe_slug(requirements["company"] or "unknown-company")
    role_slug = _safe_slug(requirements["role"])
    requirements_path = _unique_path(
        ROOT / "build" / "ollama" / "requirements" / f"{run_date}_{company_slug}_{role_slug}.json"
    )
    requirements_text = json.dumps(requirements, ensure_ascii=False, indent=2) + "\n"
    _write_atomic(requirements_path, requirements_text)
    print(f"Saved requirements: {requirements_path.relative_to(ROOT)}", flush=True)

    print("Populating resume sections...", flush=True)
    tailored_source = _read_text(BASE_RESUME_TEMPLATE)
    for config in SECTION_CONFIGS:
        print(f"Populating {config['title']}...", flush=True)
        tailored_source = populate_section(
            tailored_source,
            config,
            requirements_text,
            model,
            base_url,
            debug=debug,
        )
    tailored_source = _validate_latex(tailored_source.rstrip() + "\n\n\\end{document}\n")
    print(tailored_source)
    resume_path = ROOT / RESUME_NAME
    if not resume_path.is_file():
        raise WorkflowError(f"Current resume to archive is missing: {resume_path}")

    archive_path = _unique_path(
        ROOT / "build" / "ollama" / "resume" / f"{run_date}_{RESUME_NAME}"
    )
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(resume_path), str(archive_path))
    except OSError as exc:
        raise WorkflowError(f"Could not archive the current resume to {archive_path}: {exc}") from exc

    try:
        _write_atomic(resume_path, tailored_source)
        print("Compiling tailored resume...", flush=True)
        _compile_resume(resume_path, debug=debug)
    except WorkflowError:
        # Keep the archive and restore the previous root source if generation or compilation fails.
        if archive_path.exists():
            shutil.copy2(archive_path, resume_path)
        raise
    except OSError as exc:
        if archive_path.exists():
            shutil.copy2(archive_path, resume_path)
        raise WorkflowError(f"Could not write the tailored resume: {exc}") from exc

    print(f"Tailored resume: {resume_path.relative_to(ROOT)}", flush=True)
    print(f"Archived previous resume: {archive_path.relative_to(ROOT)}", flush=True)
    return requirements_path, archive_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tailor and compile a resume using a local Ollama model.")
    parser.add_argument(
        "--job-description",
        type=Path,
        default=ROOT / "Job_Description.txt",
        help="Job description input (default: Job_Description.txt in the project root).",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL),
        help=f"Installed Ollama model (default: {DEFAULT_MODEL}, or OLLAMA_MODEL).",
    )
    parser.add_argument(
        "--ollama-url",
        default=os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL),
        help=f"Ollama API base URL (default: {DEFAULT_OLLAMA_URL}, or OLLAMA_URL).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print every Ollama API response, including full model output, to the console.",
    )
    return parser


def _execute(args: argparse.Namespace) -> int:
    job_path = args.job_description if args.job_description.is_absolute() else ROOT / args.job_description
    try:
        requirements_path, archive_path = run(job_path, args.model, args.ollama_url, debug=args.debug)
    except WorkflowError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Requirements: {requirements_path.relative_to(ROOT)}")
    print(f"Archive: {archive_path.relative_to(ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.debug:
        return _execute(args)

    log_path = ROOT / "debug.log"
    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            stdout_tee = _TeeTextIO(sys.stdout, log_file)
            stderr_tee = _TeeTextIO(sys.stderr, log_file)
            with redirect_stdout(stdout_tee), redirect_stderr(stderr_tee):
                print("Resume tailoring debug log", flush=True)
                return _execute(args)
    except OSError as exc:
        print(f"Error: cannot write debug log at {log_path}: {exc}", file=sys.stderr)
        return 1
