"""End-to-end orchestration for resume tailoring."""
from __future__ import annotations
import json
import shutil
from datetime import date
from pathlib import Path
from .config import (
    BASE_RESUME_TEMPLATE,
    BASE_COVER_LETTER_TEMPLATE,
    COVER_LETTER_CONTENT_TEMPLATE,
    COVER_LETTER_ENDING,
    COVER_LETTER_PROMPT,
    COVER_LETTER_SCHEMA,
    REQUIREMENTS_PROMPT,
    REQUIREMENTS_SCHEMA,
    SECTION_CONFIGS,
    ROOT,
)
from .errors import WorkflowError
from .file import (
    _cache_root_resumes, _compile_resume, _find_cached_requirements, _find_cached_resume, _find_cached_cover_letter,
    _default_resume_path, _resume_archive_path, _cover_letter_archive_path,
    _safe_slug, _unique_path, _write_atomic,
)
from .renderer import (
    _validate_latex, _validate_requirements, populate_section,
    render_cover_letter_content, validate_cover_letter_response,
)
from .ollama import (
    _chat, _ensure_model, _log_debug_prompt, _prompt_text, _read_text, _replace_tokens,
    _section_data_context,
)


def run(
    job_description_path: Path,
    model: str,
    base_url: str,
    *,
    output_path: Path | None = None,
    debug: bool = False,
) -> tuple[Path, Path | None, Path, Path | None]:
    _cache_root_resumes()
    job_description = _read_text(job_description_path)
    if not job_description.strip():
        raise WorkflowError(f"Job description is empty: {job_description_path}")
    if not BASE_RESUME_TEMPLATE.is_file():
        raise WorkflowError(f"Resume template is missing: {BASE_RESUME_TEMPLATE}")
    cover_letter_inputs = (
        BASE_COVER_LETTER_TEMPLATE,
        COVER_LETTER_CONTENT_TEMPLATE,
        COVER_LETTER_PROMPT,
        ROOT / "resume_data/experience",
        ROOT / "resume_data/projects",
    )
    missing_cover_letter_inputs = [path for path in cover_letter_inputs if not path.exists()]
    if missing_cover_letter_inputs:
        missing = ", ".join(path.relative_to(ROOT).as_posix() for path in missing_cover_letter_inputs)
        raise WorkflowError(f"Cover-letter inputs are not ready yet: {missing}")
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
    base_template = _read_text(BASE_RESUME_TEMPLATE)
    resume_path = output_path
    if resume_path is None:
        resume_path = _default_resume_path(base_template, role)
    elif not resume_path.is_absolute():
        resume_path = ROOT / resume_path
    if resume_path.suffix.lower() != ".tex":
        raise WorkflowError(f"Resume output path must end in .tex: {resume_path}")

    cached_resume = _find_cached_resume(job_description, date.fromisoformat(run_date), resume_path)
    if cached_resume:
        cached_resume_path, tailored_source = cached_resume
        try:
            display_cached_path = cached_resume_path.relative_to(ROOT)
        except ValueError:
            display_cached_path = cached_resume_path
        print(f"Using cached resume: {display_cached_path}", flush=True)
    else:
        print("Populating resume sections...", flush=True)
        tailored_source = base_template
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

    cover_letter_path = resume_path.with_name(f"{resume_path.stem}-cover-letter.tex")
    cached_cover_letter = _find_cached_cover_letter(job_description, date.fromisoformat(run_date), cover_letter_path)
    if cached_cover_letter:
        cached_cover_letter_path, cover_letter_source = cached_cover_letter
        try:
            display_cached_letter = cached_cover_letter_path.relative_to(ROOT)
        except ValueError:
            display_cached_letter = cached_cover_letter_path
        print(f"Using cached cover letter: {display_cached_letter}", flush=True)
    else:
        cover_letter_base = _read_text(BASE_COVER_LETTER_TEMPLATE)
        content_template = _read_text(COVER_LETTER_CONTENT_TEMPLATE)
        experience_context = _section_data_context(ROOT / "resume_data/experience")
        project_context = _section_data_context(ROOT / "resume_data/projects")
        print("Drafting cover letter...", flush=True)
        cover_letter_prompt = _replace_tokens(
            _prompt_text(COVER_LETTER_PROMPT),
            {
                "REQUIREMENTS_JSON": requirements_text,
                "JOB_DESCRIPTION": job_description,
                "GENERATED_RESUME": tailored_source,
                "SECTION_DATA": experience_context + "\n" + project_context,
            },
        )
        if debug:
            _log_debug_prompt("cover-letter", cover_letter_prompt)
        cover_letter_data = validate_cover_letter_response(
            _chat(
                base_url,
                model,
                cover_letter_prompt,
                format_schema=COVER_LETTER_SCHEMA,
                debug=debug,
                response_label="Ollama cover-letter response",
            )
        )
        content = render_cover_letter_content(content_template, cover_letter_data)
        cover_letter_source = (
            cover_letter_base.rstrip() + "\n" + content + "\n\n" + COVER_LETTER_ENDING
            + "\n\n\\end{document}\n"
        )
        cover_letter_source = f"% Generated: {run_date} | Company: {company} | Role: {role}\n" + _validate_latex(cover_letter_source)

    archive_path: Path | None = None
    cover_letter_archive: Path | None = None
    if resume_path.is_file():
        current_source = _read_text(resume_path)
        if current_source != tailored_source:
            archive_path = _resume_archive_path(current_source, run_date)
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(resume_path), str(archive_path))
            except OSError as exc:
                raise WorkflowError(f"Could not archive the current resume to {archive_path}: {exc}") from exc
    if cover_letter_path.is_file():
        current_letter = _read_text(cover_letter_path)
        if current_letter != cover_letter_source:
            cover_letter_archive = _cover_letter_archive_path(current_letter, run_date)
            cover_letter_archive.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(cover_letter_path), str(cover_letter_archive))
            except OSError as exc:
                if archive_path is not None and archive_path.exists():
                    shutil.copy2(archive_path, resume_path)
                raise WorkflowError(f"Could not archive the current cover letter to {cover_letter_archive}: {exc}") from exc

    try:
        _write_atomic(resume_path, tailored_source)
        print("Compiling tailored resume...", flush=True)
        _compile_resume(resume_path, debug=debug)
        _write_atomic(cover_letter_path, cover_letter_source)
        print("Compiling cover letter...", flush=True)
        _compile_resume(cover_letter_path, debug=debug)
    except WorkflowError:
        # Keep the archive and restore the previous root source if generation or compilation fails.
        if archive_path is not None and archive_path.exists():
            shutil.copy2(archive_path, resume_path)
        if cover_letter_archive is not None and cover_letter_archive.exists():
            shutil.copy2(cover_letter_archive, cover_letter_path)
        raise
    except OSError as exc:
        if archive_path is not None and archive_path.exists():
            shutil.copy2(archive_path, resume_path)
        if cover_letter_archive is not None and cover_letter_archive.exists():
            shutil.copy2(cover_letter_archive, cover_letter_path)
        raise WorkflowError(f"Could not write the tailored resume: {exc}") from exc

    try:
        display_resume_path = resume_path.relative_to(ROOT)
    except ValueError:
        display_resume_path = resume_path
    print(f"Tailored resume: {display_resume_path}", flush=True)
    try:
        display_cover_letter_path = cover_letter_path.relative_to(ROOT)
    except ValueError:
        display_cover_letter_path = cover_letter_path
    print(f"Tailored cover letter: {display_cover_letter_path}", flush=True)
    if archive_path is not None:
        print(f"Archived previous resume: {archive_path.relative_to(ROOT)}", flush=True)
    if cover_letter_archive is not None:
        print(f"Archived previous cover letter: {cover_letter_archive.relative_to(ROOT)}", flush=True)
    return requirements_path, archive_path, cover_letter_path, cover_letter_archive
