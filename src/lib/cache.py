"""Recent requirements and generated resume cache lookup."""
from __future__ import annotations
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from .config import RESUME_NAME, ROOT
from .errors import WorkflowError
from .latex import _validate_latex, _validate_requirements


def _find_cached_requirements(job_description: str, run_date: date) -> tuple[Path, dict[str, Any]] | None:
    """Find a valid requirements record for this company and role from the past week."""
    requirements_dir = ROOT / "build" / "ollama" / "requirements"
    if not requirements_dir.is_dir():
        return None

    candidates: list[tuple[date, Path, dict[str, Any]]] = []
    for path in requirements_dir.glob("*.json"):
        match = re.match(r"^(\d{4}-\d{2}-\d{2})_", path.name)
        if not match:
            continue
        try:
            saved_date = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if not (run_date - timedelta(days=7) <= saved_date <= run_date):
            continue
        try:
            requirements = _validate_requirements(path.read_text(encoding="utf-8"))
        except (OSError, WorkflowError):
            continue

        company = requirements["company"].strip()
        role = requirements["role"].strip()
        # Both identity fields must be stated in the input; this avoids reusing a
        # same-day cache for an unrelated posting when the JD lacks metadata.
        jd_identity = re.sub(r"\s+", " ", job_description).casefold()
        if company and role and company.casefold() in jd_identity and role.casefold() in jd_identity:
            candidates.append((saved_date, path, requirements))

    if not candidates:
        return None
    _, path, requirements = max(candidates, key=lambda candidate: (candidate[0], candidate[1].name))
    return path, requirements


def _find_cached_resume(job_description: str, run_date: date) -> tuple[Path, str] | None:
    """Find a generated resume for the same stated company and role from the past week."""
    resume_dir = ROOT / "build" / "ollama" / "resume"
    jd_identity = re.sub(r"\s+", " ", job_description).casefold()
    candidates: list[tuple[date, Path, str]] = []
    resume_paths = list(resume_dir.glob("*.tex")) if resume_dir.is_dir() else []
    current_resume = ROOT / RESUME_NAME
    if current_resume.is_file():
        resume_paths.append(current_resume)

    for path in resume_paths:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        match = re.match(r"% Generated: (\d{4}-\d{2}-\d{2}) \| Company: (.*?) \| Role: (.*?)\s*\n", source)
        if not match:
            continue
        try:
            saved_date = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if not (run_date - timedelta(days=7) <= saved_date <= run_date):
            continue
        company, role = match.group(2).strip(), match.group(3).strip()
        if company and role and company.casefold() in jd_identity and role.casefold() in jd_identity:
            try:
                source = _validate_latex(source)
            except WorkflowError:
                continue
            candidates.append((saved_date, path, source))
    if not candidates:
        return None
    _, path, source = max(candidates, key=lambda candidate: (candidate[0], candidate[1].name))
    return path, source
