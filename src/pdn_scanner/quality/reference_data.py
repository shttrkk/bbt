from __future__ import annotations

import re

from pdn_scanner.enums import ConfidenceLevel, ValidationStatus
from pdn_scanner.models import DetectionResult, ExtractedContent, FileDescriptor

REFERENCE_PATH_MARKERS = (
    "plan",
    "plans",
    "product",
    "products",
    "catalog",
    "catalogue",
    "tariff",
    "billing",
    "incident",
    "incidents",
    "service",
    "services",
    "package",
)
REFERENCE_FIELD_MARKERS = (
    "plan",
    "product",
    "tariff",
    "incident",
    "service",
    "package",
    "catalog",
    "status",
    "type",
    "code",
    "sku",
)
ID_FIELD_RE = re.compile(r"(^|[_\-.])(?:id|uuid|guid|token|hash|code|status|key)($|[_\-.])")
PERSONAL_FIELD_MARKERS = (
    "customer_name",
    "destination_address",
    "address",
    "phone",
    "email",
    "snils",
    "inn",
    "birth",
    "dob",
    "фио",
    "телефон",
    "адрес",
)


def detect_reference_data(
    descriptor: FileDescriptor,
    extraction: ExtractedContent,
    detections: list[DetectionResult],
) -> tuple[bool, list[str]]:
    extractor_name = str(extraction.metadata.get("extractor", "")).lower()
    if extractor_name not in {"csv", "json", "parquet"}:
        return False, []

    path_lower = descriptor.rel_path.lower()
    header = [str(item).lower() for item in extraction.metadata.get("header", [])]
    text_sample = " ".join(extraction.text_chunks[:20]).lower()

    path_hits = sum(1 for marker in REFERENCE_PATH_MARKERS if marker in path_lower)
    field_hits = sum(1 for marker in REFERENCE_FIELD_MARKERS if marker in text_sample)
    id_hits = sum(1 for header_name in header if ID_FIELD_RE.search(header_name)) + len(
        re.findall(r"\b(?:id|uuid|guid|token|hash|status|code)\b", text_sample)
    )
    personal_field_hits = sum(1 for marker in PERSONAL_FIELD_MARKERS if marker in text_sample)
    strong_personal = sum(1 for detection in detections if _is_strong_personal_detection(detection))

    reasons: list[str] = []
    if path_hits >= 1:
        reasons.append("REFERENCE_DATA_PATH")
    if field_hits >= 2:
        reasons.append("REFERENCE_DATA_SCHEMA")
    if id_hits >= 2:
        reasons.append("REFERENCE_DATA_ID_HEAVY")

    is_reference = bool(reasons) and strong_personal == 0 and personal_field_hits <= 1
    return is_reference, reasons if is_reference else []


def _is_strong_personal_detection(detection: DetectionResult) -> bool:
    if detection.family in {"government", "payment"} and detection.validation_status == ValidationStatus.VALID:
        return True
    return detection.category in {"person_name", "address"} and detection.confidence in {
        ConfidenceLevel.HIGH,
        ConfidenceLevel.MEDIUM,
    }
