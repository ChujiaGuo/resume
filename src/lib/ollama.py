"""HTTP client and model operations for a local Ollama server."""
from __future__ import annotations
import json
import urllib.error
import urllib.request
from typing import Any
from .errors import WorkflowError


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
