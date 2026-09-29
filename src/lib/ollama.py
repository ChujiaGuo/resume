"""Ollama API access and prompt loading/rendering helpers."""
from __future__ import annotations
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
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
    allow_empty: bool = False,
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
    if not isinstance(content, str) or (not allow_empty and not content.strip()):
        raise WorkflowError("Ollama returned an empty response")
    return content.strip()
