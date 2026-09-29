"""End-to-end orchestration for resume tailoring."""
from __future__ import annotations
import json
import shutil
from datetime import date
from pathlib import Path
from .config import (
    BASE_RESUME_TEMPLATE,
    REQUIREMENTS_PROMPT,
    REQUIREMENTS_SCHEMA,
    RESUME_NAME,
    SECTION_CONFIGS,
    ROOT,
)
from .errors import WorkflowError
from .file import (
    _compile_resume, _find_cached_requirements, _find_cached_resume,
    _resume_archive_path, _safe_slug, _unique_path, _write_atomic,
)
from .renderer import _validate_latex, _validate_requirements, populate_section
from .ollama import (
    _chat, _ensure_model, _log_debug_prompt, _prompt_text, _read_text, _replace_tokens,
)


def run(
    job_description_path: Path,
    model: str,
    base_url: str,
    *,
    debug: bool = False,
) -> tuple[Path, Path | None]:
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

    run_date = date.today().isoformat()
    cached = _find_cached_requirements(job_description, date.fromisoformat(run_date))
    if cached:
        requirements_path, requirements = cached
        requirements_text = json.dumps(requirements, ensure_ascii=False, indent=2) + "\n"
        print(f"Using cached requirements: {requirements_path.relative_to(ROOT)}", flush=True)
    else:
        print("Extracting job requirements...", flush=True)
        extraction_prompt = _replace_tokens(_prompt_text(REQUIREMENTS_PROMPT), {"JOB_DESCRIPTION": job_description})
        if debug:
            _log_debug_prompt("requirements-extraction", extraction_prompt)
        requirements = _validate_requirements(
            _chat(
                base_url,
                model,
                extraction_prompt,
                format_schema=REQUIREMENTS_SCHEMA,
                debug=debug,
                response_label="Ollama requirements-extraction response",
            )
        )

        company_slug = _safe_slug(requirements["company"] or "unknown-company")
        role_slug = _safe_slug(requirements["role"])
        requirements_path = _unique_path(
            ROOT / "build" / "ollama" / "requirements" / f"{run_date}_{company_slug}_{role_slug}.json"
        )
        requirements_text = json.dumps(requirements, ensure_ascii=False, indent=2) + "\n"
        _write_atomic(requirements_path, requirements_text)
        print(f"Saved requirements: {requirements_path.relative_to(ROOT)}", flush=True)

    company = requirements["company"].strip() or "unknown-company"
    role = requirements["role"].strip() or "unknown-role"
    cached_resume = _find_cached_resume(job_description, date.fromisoformat(run_date))
    if cached_resume:
        cached_resume_path, tailored_source = cached_resume
        print(f"Using cached resume: {cached_resume_path.relative_to(ROOT)}", flush=True)
    else:
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
        tailored_source = tailored_source.rstrip() + "\n\n\\end{document}\n"
        tailored_source = f"% Generated: {run_date} | Company: {company} | Role: {role}\n" + tailored_source
        tailored_source = _validate_latex(tailored_source)
    resume_path = ROOT / RESUME_NAME
    archive_path: Path | None = None
    if resume_path.is_file():
        current_source = _read_text(resume_path)
        if current_source != tailored_source:
            archive_path = _resume_archive_path(current_source, run_date)
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
        if archive_path is not None and archive_path.exists():
            shutil.copy2(archive_path, resume_path)
        raise
    except OSError as exc:
        if archive_path is not None and archive_path.exists():
            shutil.copy2(archive_path, resume_path)
        raise WorkflowError(f"Could not write the tailored resume: {exc}") from exc

    print(f"Tailored resume: {resume_path.relative_to(ROOT)}", flush=True)
    if archive_path is not None:
        print(f"Archived previous resume: {archive_path.relative_to(ROOT)}", flush=True)
    return requirements_path, archive_path
