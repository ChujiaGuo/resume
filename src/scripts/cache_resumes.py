#!/usr/bin/env python3
"""Cache root-level sources and remove generated PDFs from the project root."""
from __future__ import annotations

import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RESUME_ARCHIVE_DIR = ROOT / "build" / "ollama" / "resume"
COVER_LETTER_ARCHIVE_DIR = ROOT / "build" / "ollama" / "cover_letter"
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
    sources = sorted(path for path in ROOT.glob("*.tex") if path.is_file())
    pdfs = sorted(path for path in ROOT.glob("*.pdf") if path.is_file())
    if not sources and not pdfs:
        print("No root-level resume sources or PDFs found.")
        return 0

    if sources:
        RESUME_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        COVER_LETTER_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    skipped = 0
    for source in sources:
        try:
            content = source.read_bytes()
            text = content.decode("utf-8")
            is_cover_letter = source.stem.endswith("-cover-letter")
            archive_dir = COVER_LETTER_ARCHIVE_DIR if is_cover_letter else RESUME_ARCHIVE_DIR
            base = archive_dir / archive_name(source, text)
            destination = unique_destination(base, content)
            source_type = "cover letter" if is_cover_letter else "resume"
            if destination is None:
                # The identical cache copy is already durable, so remove the root
                # copy to complete the move into its type-specific cache.
                source.unlink()
                print(f"Already cached {source_type}; removed root copy: {source.name}")
                skipped += 1
                continue
            shutil.copy2(source, destination)
            if destination.read_bytes() != content:
                raise OSError(f"Cache copy verification failed: {destination}")
            source.unlink()
            print(f"Cached {source_type} and removed {source.name} -> {destination.relative_to(ROOT)}")
            copied += 1
        except (OSError, UnicodeDecodeError) as exc:
            print(f"Could not cache {source.name}: {exc}", file=sys.stderr)
            return 1

    removed_pdfs = 0
    for pdf in pdfs:
        try:
            pdf.unlink()
            print(f"Removed root-level PDF: {pdf.name}")
            removed_pdfs += 1
        except OSError as exc:
            print(f"Could not remove {pdf.name}: {exc}", file=sys.stderr)
            return 1

    print(f"Done: {copied} sources cached, {skipped} already cached, {removed_pdfs} PDFs removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
