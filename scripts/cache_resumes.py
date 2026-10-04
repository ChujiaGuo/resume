#!/usr/bin/env python3
"""Copy root-level generated resumes into the workflow's resume cache."""
from __future__ import annotations

import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = ROOT / "build" / "ollama" / "resume"
METADATA_RE = re.compile(
    r"^% Generated: (\d{4}-\d{2}-\d{2}) \| Company: (.*?) \| Role: (.*?)\s*$"
)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-") or "unknown-role"


def archive_name(source: Path, content: str) -> str:
    first_line = content.splitlines()[0] if content.splitlines() else ""
    match = METADATA_RE.match(first_line)
    if match:
        try:
            saved_date = date.fromisoformat(match.group(1)).isoformat()
        except ValueError:
            saved_date = date.today().isoformat()
        company = match.group(2).strip() or "unknown-company"
        role = match.group(3).strip() or source.stem
    else:
        saved_date = date.today().isoformat()
        company = "unknown-company"
        # Root resume names conventionally begin with the candidate's first and
        # last name; retain the rest as a useful role label when metadata is absent.
        role = re.sub(r"^[a-z0-9]+_[a-z0-9]+_", "", source.stem, flags=re.IGNORECASE) or source.stem
    return f"{saved_date}_{slug(company)}_{slug(role)}.tex"


def unique_destination(base: Path, content: bytes) -> Path | None:
    """Return a free path, or None when identical content is already cached."""
    candidate = base
    suffix = 2
    while candidate.exists():
        if candidate.read_bytes() == content:
            return None
        candidate = base.with_name(f"{base.stem}_{suffix}{base.suffix}")
        suffix += 1
    return candidate


def main() -> int:
    resumes = sorted(path for path in ROOT.glob("*.tex") if path.is_file())
    if not resumes:
        print("No root-level .tex resumes found.")
        return 0

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    skipped = 0
    for source in resumes:
        try:
            content = source.read_bytes()
            text = content.decode("utf-8")
            base = ARCHIVE_DIR / archive_name(source, text)
            destination = unique_destination(base, content)
            if destination is None:
                # The identical cache copy is already durable, so the root copy
                # can be removed to complete the requested move.
                source.unlink()
                print(f"Already cached and removed from root: {source.name}")
                skipped += 1
                continue
            shutil.copy2(source, destination)
            if destination.read_bytes() != content:
                raise OSError(f"Cache copy verification failed: {destination}")
            source.unlink()
            print(f"Cached and removed {source.name} -> {destination.relative_to(ROOT)}")
            copied += 1
        except (OSError, UnicodeDecodeError) as exc:
            print(f"Could not cache {source.name}: {exc}", file=sys.stderr)
            return 1

    print(f"Done: {copied} copied, {skipped} already cached.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
