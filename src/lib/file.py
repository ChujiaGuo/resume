"""Filesystem persistence and LaTeX compilation helpers."""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import tempfile
import json
from datetime import timedelta
from typing import Any
from datetime import date
from pathlib import Path
from .config import RESUME_NAME, ROOT
from .errors import WorkflowError
from .renderer import _validate_latex, _validate_requirements


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


def _resume_archive_path(source: str, fallback_date: str) -> Path:
    """Build a cache filename from the resume being archived, not its replacement."""
    metadata = re.match(
        r"^% Generated: (\d{4}-\d{2}-\d{2}) \| Company: (.*?) \| Role: (.*?)\s*$",
        source.splitlines()[0] if source.splitlines() else "",
    )
    if metadata:
        try:
            date_part = date.fromisoformat(metadata.group(1)).isoformat()
        except ValueError:
            date_part = fallback_date
        company = metadata.group(2).strip() or "unknown-company"
        role = metadata.group(3).strip() or "unknown-role"
    else:
        date_part = fallback_date
        company = "unknown-company"
        role = "unknown-role"
    filename = f"{date_part}_{_safe_slug(company)}_{_safe_slug(role)}.tex"
    return _unique_path(ROOT / "build" / "ollama" / "resume" / filename)


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
