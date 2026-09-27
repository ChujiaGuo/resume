"""Prompt loading, rendering, and resume data context assembly."""
from __future__ import annotations
import re
from pathlib import Path
from .config import ROOT
from .errors import WorkflowError


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


def _section_data_context(path: Path) -> str:
    if path.is_dir():
        return _files_as_context(path, {".md"})
    return f"===== {path.relative_to(ROOT).as_posix()} =====\n{_read_text(path).rstrip()}\n"
