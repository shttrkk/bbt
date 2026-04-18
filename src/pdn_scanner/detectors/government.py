from __future__ import annotations

import re

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ConfidenceLevel, ValidationStatus
from pdn_scanner.models import DetectionResult, ExtractedContent
from pdn_scanner.normalize import normalize_numeric_id
from pdn_scanner.reporting.masking import hash_value, mask_preview
from pdn_scanner.validators import is_valid_inn, is_valid_snils

SNILS_RE = re.compile(r"\b\d{3}-\d{3}-\d{3}\s\d{2}\b|\b\d{11}\b")
INN_RE = re.compile(r"\b\d{10}\b|\b\d{12}\b")


def detect_government(content: ExtractedContent, config: AppConfig) -> list[DetectionResult]:
    detections: list[DetectionResult] = []

    for index, chunk in enumerate(content.text_chunks):
        lowered = chunk.lower()
        for match in SNILS_RE.finditer(chunk):
            value = match.group(0)
            normalized = normalize_numeric_id(value)
            is_valid = is_valid_snils(normalized)
            keywords = [keyword for keyword in ("снилс", "snils") if keyword in lowered]
            if not is_valid and not keywords:
                continue
            detections.append(
                DetectionResult(
                    category="snils",
                    family="government",
                    detector_id="government.snils.regex",
                    confidence=ConfidenceLevel.HIGH if is_valid else ConfidenceLevel.LOW,
                    validation_status=ValidationStatus.VALID if is_valid else ValidationStatus.INVALID,
                    value_hash=hash_value(normalized, config),
                    masked_preview=mask_preview(normalized, config),
                    location_hints=[f"chunk:{index}"],
                    context_keywords=keywords,
                    raw_value=value,
                    normalized_value=normalized,
                )
            )

        for match in INN_RE.finditer(chunk):
            value = match.group(0)
            normalized = normalize_numeric_id(value)
            is_valid = is_valid_inn(normalized)
            keywords = [keyword for keyword in ("инн", "inn") if keyword in lowered]
            if not is_valid and not keywords:
                continue
            detections.append(
                DetectionResult(
                    category="inn",
                    family="government",
                    detector_id="government.inn.regex",
                    confidence=ConfidenceLevel.HIGH if is_valid else ConfidenceLevel.LOW,
                    validation_status=ValidationStatus.VALID if is_valid else ValidationStatus.INVALID,
                    value_hash=hash_value(normalized, config),
                    masked_preview=mask_preview(normalized, config),
                    location_hints=[f"chunk:{index}"],
                    context_keywords=keywords,
                    raw_value=value,
                    normalized_value=normalized,
                )
            )

    return detections
