"""Filesystem persistence and LaTeX compilation helpers."""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from .config import ROOT
from .errors import WorkflowError


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
