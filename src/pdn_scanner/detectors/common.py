from __future__ import annotations

import re

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ConfidenceLevel, ValidationStatus
from pdn_scanner.models import DetectionMatch, DetectionResult
from pdn_scanner.normalize import extract_context_window
from pdn_scanner.reporting.masking import hash_value, mask_preview

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+7|8)\s*(?:\(\d{3}\)|\d{3})[\s.-]*\d{3}[\s.-]*\d{2}[\s.-]*\d{2}(?!\d)")
NUMERIC_TOKEN_RE = re.compile(r"\b(?:\d[ -]*?){6,20}\b")
NAME_RE = re.compile(r"\b[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?\b")


def build_detection(
    *,
    entity_category: str,
    entity_subtype: str,
    detector_id: str,
    confidence: ConfidenceLevel,
    validation_status: ValidationStatus,
    raw_value: str,
    normalized_value: str,
    config: AppConfig,
    chunk: str,
    chunk_index: int,
    start: int,
    end: int,
    context_keywords: list[str] | None = None,
) -> DetectionResult:
    fragment = extract_context_window(chunk, start, end, config.detection.context_window)
    masked_value = mask_preview(raw_value, config)
    masked_fragment = _sanitize_fragment(fragment, config)
    match = DetectionMatch(
        chunk_index=chunk_index,
        start_char=start,
        end_char=end,
        fragment=masked_fragment,
    )

    return DetectionResult(
        category=entity_subtype,
        family=entity_category,
        entity_category=entity_category,
        entity_subtype=entity_subtype,
        detector_id=detector_id,
        confidence=confidence,
        validation_status=validation_status,
        value_hash=hash_value(normalized_value, config),
        masked_preview=masked_value,
        chunk_index=chunk_index,
        start_char=start,
        end_char=end,
        source_fragment=masked_fragment,
        matches=[match],
        location_hints=[f"chunk:{chunk_index}", f"span:{start}:{end}"],
        context_keywords=sorted(set(context_keywords or [])),
        raw_value=raw_value,
        normalized_value=normalized_value,
    )


def _sanitize_fragment(fragment: str, config: AppConfig) -> str:
    sanitized = fragment
    for pattern in (EMAIL_RE, PHONE_RE, NUMERIC_TOKEN_RE, NAME_RE):
        sanitized = pattern.sub(lambda match: mask_preview(match.group(0), config), sanitized)
    return sanitized
