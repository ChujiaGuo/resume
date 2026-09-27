"""Command-line interface and optional debug logging."""
from __future__ import annotations
import argparse
from contextlib import redirect_stderr, redirect_stdout
import os
from pathlib import Path
import sys
from typing import Any
from .config import DEFAULT_MODEL, DEFAULT_OLLAMA_URL, ROOT
from .errors import WorkflowError
from .workflow import run


class _TeeTextIO:
    """Copy text written to the wrapper to both the original stream and a log file."""

    def __init__(self, *streams: Any) -> None:
        self.streams = streams

    def write(self, text: str) -> int:
        for stream in self.streams:
            stream.write(text)
        return len(text)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()

    def isatty(self) -> bool:
        return any(stream.isatty() for stream in self.streams if hasattr(stream, "isatty"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tailor and compile a resume using a local Ollama model.")
    parser.add_argument(
        "--job-description",
        type=Path,
        default=ROOT / "Job_Description.txt",
        help="Job description input (default: Job_Description.txt in the project root).",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL),
        help=f"Installed Ollama model (default: {DEFAULT_MODEL}, or OLLAMA_MODEL).",
    )
    parser.add_argument(
        "--ollama-url",
        default=os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL),
        help=f"Ollama API base URL (default: {DEFAULT_OLLAMA_URL}, or OLLAMA_URL).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print every Ollama API response, including full model output, to the console.",
    )
    return parser


def _execute(args: argparse.Namespace) -> int:
    job_path = args.job_description if args.job_description.is_absolute() else ROOT / args.job_description
    try:
        requirements_path, archive_path = run(job_path, args.model, args.ollama_url, debug=args.debug)
    except WorkflowError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Requirements: {requirements_path.relative_to(ROOT)}")
    if archive_path is not None:
        print(f"Archive: {archive_path.relative_to(ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.debug:
        return _execute(args)

    log_path = ROOT / "debug.log"
    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            stdout_tee = _TeeTextIO(sys.stdout, log_file)
            stderr_tee = _TeeTextIO(sys.stderr, log_file)
            with redirect_stdout(stdout_tee), redirect_stderr(stderr_tee):
                print("Resume tailoring debug log", flush=True)
                return _execute(args)
    except OSError as exc:
        print(f"Error: cannot write debug log at {log_path}: {exc}", file=sys.stderr)
        return 1
