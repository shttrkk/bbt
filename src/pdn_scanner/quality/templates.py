from __future__ import annotations

import re

from pdn_scanner.enums import ConfidenceLevel, ValidationStatus
from pdn_scanner.models import DetectionResult

PLACEHOLDER_PATTERNS = (
    re.compile(
        r"\b(?:фио|full name|first name|last name|address|адрес|подпись|дата рождения|date of birth|паспорт|passport|series|номер|number|заявитель|телефон|phone|email|e-mail)\b"
        r"[^.\n:]{0,24}(?:[:\-]\s*)?(?:_{3,}|\.{3,}|[- ]{6,})",
        flags=re.IGNORECASE,
    ),
    re.compile(r"\bсерия\b[^.\n]{0,12}_{2,}[^.\n]{0,12}\bномер\b[^.\n]{0,12}_{2,}", flags=re.IGNORECASE),
)
FORM_MARKERS = (
    "заполнить",
    "заявитель",
    "подпись",
    "расшифровка",
    "паспорт",
    "passport",
    "дата рождения",
    "date of birth",
    "фио",
    "full name",
    "first name",
    "last name",
    "адрес",
    "address",
)


def detect_template_like(text: str, detections: list[DetectionResult]) -> tuple[bool, list[str]]:
    lowered = text.lower()
    placeholder_hits = sum(len(pattern.findall(text)) for pattern in PLACEHOLDER_PATTERNS)
    blank_field_hits = len(re.findall(r"(?:_{3,}|\.{4,})", text))
    form_markers = sum(1 for marker in FORM_MARKERS if marker in lowered)
    trusted_entities = sum(1 for detection in detections if _is_trusted_detection(detection))

    reasons: list[str] = []
    if placeholder_hits >= 2:
        reasons.append("TEMPLATE_PLACEHOLDER_FIELDS")
    if blank_field_hits >= 4:
        reasons.append("TEMPLATE_BLANK_FIELDS")
    if form_markers >= 3:
        reasons.append("TEMPLATE_FORM_MARKERS")

    is_template = bool(reasons) and trusted_entities == 0
    return is_template, reasons if is_template else []


def _is_trusted_detection(detection: DetectionResult) -> bool:
    if detection.validation_status == ValidationStatus.VALID:
        return True
    return detection.confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM} and detection.category in {
        "person_name",
        "address",
    }
