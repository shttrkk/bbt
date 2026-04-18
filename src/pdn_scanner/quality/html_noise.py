from __future__ import annotations

import re

from pdn_scanner.models import DetectionResult

UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", flags=re.IGNORECASE)
LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_-]{20,}\b")
HEX_TOKEN_RE = re.compile(r"\b[a-f0-9]{24,}\b", flags=re.IGNORECASE)
NOISE_MARKERS = (
    "window.",
    "document.",
    "datalayer",
    "gtag(",
    "ym(",
    "utm_",
    "session",
    "token",
    "cache-control",
    "onclick",
    "javascript:",
    "function(",
    "const ",
    "let ",
    " var ",
    "=>",
    "{",
    "}",
    "return ",
)
WEB_DOC_MARKERS = ("meta", "canonical", "viewport", "stylesheet", "generator", "theme-color", "journal")


def is_html_noise_chunk(chunk: str) -> bool:
    lowered = chunk.lower()
    marker_hits = sum(1 for marker in NOISE_MARKERS if marker in lowered)
    long_tokens = len(LONG_TOKEN_RE.findall(chunk)) + len(HEX_TOKEN_RE.findall(chunk)) + len(UUID_RE.findall(chunk))
    punctuation = sum(1 for char in chunk if char in "{}[]=;<>/&")
    ratio = punctuation / max(len(chunk), 1)
    return marker_hits >= 2 or long_tokens >= 3 or ratio >= 0.08


def should_suppress_html_detection(detection: DetectionResult, chunk: str) -> bool:
    lowered = chunk.lower()
    if detection.category in {"inn", "snils", "bank_card", "phone"} and (
        UUID_RE.search(chunk) or LONG_TOKEN_RE.search(chunk) or "token" in lowered
    ):
        return True

    if detection.category == "person_name":
        if any(marker in lowered for marker in WEB_DOC_MARKERS) and "фио" not in lowered and "employee" not in lowered:
            return True
        if "живого журнала" in lowered:
            return True

    return is_html_noise_chunk(chunk) and not detection.context_keywords
