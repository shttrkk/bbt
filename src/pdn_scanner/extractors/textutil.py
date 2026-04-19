from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


TEXTUTIL_TIMEOUT_SECONDS = 20


@dataclass(slots=True)
class TextutilExtractionResult:
    chunks: list[str]
    warnings: list[str]
    available: bool


def extract_text_with_textutil(path: Path, *, input_format: str, max_chunks: int) -> TextutilExtractionResult:
    command = [
        "textutil",
        "-convert",
        "txt",
        "-stdout",
        "-encoding",
        "UTF-8",
        "-format",
        input_format,
        "--",
        str(path),
    ]

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=TEXTUTIL_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return TextutilExtractionResult(
            chunks=[],
            warnings=["textutil is not available on this system"],
            available=False,
        )
    except subprocess.TimeoutExpired:
        return TextutilExtractionResult(
            chunks=[],
            warnings=[f"textutil timed out after {TEXTUTIL_TIMEOUT_SECONDS}s"],
            available=True,
        )

    if proc.returncode != 0:
        error_text = (proc.stderr or "").strip() or "unknown textutil error"
        return TextutilExtractionResult(
            chunks=[],
            warnings=[f"textutil conversion failed: {error_text}"],
            available=True,
        )

    chunks = [
        " ".join(line.split())
        for line in proc.stdout.splitlines()
        if " ".join(line.split())
    ][:max_chunks]
    return TextutilExtractionResult(chunks=chunks, warnings=[], available=True)
