from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from charset_normalizer import from_bytes


def read_text_with_best_effort(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    raw = path.read_bytes()
    match = from_bytes(raw).best()
    if match is None:
        warnings.append("Could not confidently detect encoding; fallback to utf-8 with ignore")
        return raw.decode("utf-8", errors="ignore"), warnings
    if match.encoding:
        warnings.append(f"Detected encoding: {match.encoding}")
    return str(match), warnings


def flatten_json_to_chunks(data: Any, prefix: str = "") -> Iterator[str]:
    if isinstance(data, dict):
        for key, value in data.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from flatten_json_to_chunks(value, next_prefix)
        return

    if isinstance(data, list):
        for index, value in enumerate(data):
            next_prefix = f"{prefix}[{index}]"
            yield from flatten_json_to_chunks(value, next_prefix)
        return

    if data is None:
        return

    value = str(data).strip()
    if value:
        yield f"{prefix}: {value}" if prefix else value
