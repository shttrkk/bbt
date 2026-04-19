from __future__ import annotations

import re

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ConfidenceLevel, ValidationStatus
from pdn_scanner.models import DetectionResult, ExtractedContent
from pdn_scanner.normalize import normalize_numeric_id, normalize_whitespace
from pdn_scanner.validators import is_valid_inn, is_valid_snils, validate_mrz

from .common import build_detection

SNILS_RE = re.compile(r"\b\d{3}-\d{3}-\d{3}\s\d{2}\b|\b\d{11}\b")
INN_RE = re.compile(r"\b\d{10}\b|\b\d{12}\b")
PASSPORT_COMBINED_RE = re.compile(
    r"(?:(?:паспорт(?:\s*рф)?|passport)[^0-9]{0,25})?(\d{2}\s?\d{2})[^\d]{0,6}(\d{6})",
    flags=re.IGNORECASE,
)
PASSPORT_SERIES_RE = re.compile(r"(?:серия(?:\s+паспорта)?|passport series)\s*[:#]?\s*(\d{2}\s?\d{2})", flags=re.IGNORECASE)
PASSPORT_NUMBER_RE = re.compile(
    r"(?:номер(?:\s+паспорта)?|passport number)\s*[:#]?\s*(\d{6})",
    flags=re.IGNORECASE,
)
DRIVER_LICENSE_RE = re.compile(r"\b\d{2}\s?\d{2}\s?\d{6}\b|\b\d{10}\b")
MRZ_RE = re.compile(r"\b(?:P<|I<|ID)[A-Z0-9<]{28,42}\b")

PASSPORT_KEYWORDS = ("паспорт", "паспорт рф", "passport", "серия", "номер")
DRIVER_LICENSE_KEYWORDS = ("водительское удостоверение", "вод. удостоверение", "driver license", "ву")


def detect_government(content: ExtractedContent, config: AppConfig) -> list[DetectionResult]:
    detections: list[DetectionResult] = []

    for index, chunk in enumerate(content.text_chunks):
        lowered = chunk.lower()
        detections.extend(_detect_snils(chunk, lowered, index, config))
        detections.extend(_detect_inn(chunk, lowered, index, config))
        detections.extend(_detect_passport(chunk, lowered, index, config))
        detections.extend(_detect_driver_license(chunk, lowered, index, config))
        detections.extend(_detect_mrz(chunk, index, config))

    return detections


def _detect_snils(chunk: str, lowered: str, index: int, config: AppConfig) -> list[DetectionResult]:
    detections: list[DetectionResult] = []
    for match in SNILS_RE.finditer(chunk):
        value = match.group(0)
        normalized = normalize_numeric_id(value)
        is_valid = is_valid_snils(normalized)
        keywords = [keyword for keyword in ("снилс", "snils") if keyword in lowered]
        if not is_valid and not keywords:
            continue
        detections.append(
            build_detection(
                entity_category="government",
                entity_subtype="snils",
                detector_id="government.snils.regex",
                confidence=ConfidenceLevel.HIGH if is_valid else ConfidenceLevel.LOW,
                validation_status=ValidationStatus.VALID if is_valid else ValidationStatus.INVALID,
                raw_value=value,
                normalized_value=normalized,
                config=config,
                chunk=chunk,
                chunk_index=index,
                start=match.start(),
                end=match.end(),
                context_keywords=keywords,
            )
        )
    return detections


def _detect_inn(chunk: str, lowered: str, index: int, config: AppConfig) -> list[DetectionResult]:
    detections: list[DetectionResult] = []
    for match in INN_RE.finditer(chunk):
        value = match.group(0)
        normalized = normalize_numeric_id(value)
        is_valid = is_valid_inn(normalized)
        keywords = [keyword for keyword in ("инн", "inn") if keyword in lowered]
        if not is_valid and not keywords:
            continue
        subtype = "inn_legal_entity" if len(normalized) == 10 else "inn_individual"
        detections.append(
            build_detection(
                entity_category="government",
                entity_subtype=subtype,
                detector_id="government.inn.regex",
                confidence=ConfidenceLevel.HIGH if is_valid else ConfidenceLevel.LOW,
                validation_status=ValidationStatus.VALID if is_valid else ValidationStatus.INVALID,
                raw_value=value,
                normalized_value=normalized,
                config=config,
                chunk=chunk,
                chunk_index=index,
                start=match.start(),
                end=match.end(),
                context_keywords=keywords,
            )
        )
    return detections


def _detect_passport(chunk: str, lowered: str, index: int, config: AppConfig) -> list[DetectionResult]:
    detections: list[DetectionResult] = []
    passport_keywords = [keyword for keyword in PASSPORT_KEYWORDS if keyword in lowered]
    has_passport_context = "паспорт" in lowered or "passport" in lowered or ("серия" in lowered and "номер" in lowered)

    for match in PASSPORT_COMBINED_RE.finditer(chunk):
        if not has_passport_context:
            continue
        series = normalize_numeric_id(match.group(1))
        number = normalize_numeric_id(match.group(2))
        normalized = f"{series}{number}"
        detections.append(
            build_detection(
                entity_category="government",
                entity_subtype="passport_series_number",
                detector_id="government.passport.combined",
                confidence=ConfidenceLevel.HIGH,
                validation_status=ValidationStatus.VALID,
                raw_value=normalize_whitespace(match.group(0)),
                normalized_value=normalized,
                config=config,
                chunk=chunk,
                chunk_index=index,
                start=match.start(),
                end=match.end(),
                context_keywords=passport_keywords,
            )
        )

    for match in PASSPORT_SERIES_RE.finditer(chunk):
        if not has_passport_context:
            continue
        series = normalize_numeric_id(match.group(1))
        if len(series) != 4:
            continue
        detections.append(
            build_detection(
                entity_category="government",
                entity_subtype="passport_series",
                detector_id="government.passport.series",
                confidence=ConfidenceLevel.MEDIUM,
                validation_status=ValidationStatus.VALID,
                raw_value=match.group(1),
                normalized_value=series,
                config=config,
                chunk=chunk,
                chunk_index=index,
                start=match.start(1),
                end=match.end(1),
                context_keywords=passport_keywords or ["серия"],
            )
        )

    for match in PASSPORT_NUMBER_RE.finditer(chunk):
        if not has_passport_context:
            continue
        number = normalize_numeric_id(match.group(1))
        if len(number) != 6:
            continue
        detections.append(
            build_detection(
                entity_category="government",
                entity_subtype="passport_number",
                detector_id="government.passport.number",
                confidence=ConfidenceLevel.MEDIUM,
                validation_status=ValidationStatus.VALID,
                raw_value=match.group(1),
                normalized_value=number,
                config=config,
                chunk=chunk,
                chunk_index=index,
                start=match.start(1),
                end=match.end(1),
                context_keywords=passport_keywords or ["номер"],
            )
        )

    return detections


def _detect_driver_license(chunk: str, lowered: str, index: int, config: AppConfig) -> list[DetectionResult]:
    if not any(keyword in lowered for keyword in DRIVER_LICENSE_KEYWORDS):
        return []

    detections: list[DetectionResult] = []
    keywords = [keyword for keyword in DRIVER_LICENSE_KEYWORDS if keyword in lowered]
    for match in DRIVER_LICENSE_RE.finditer(chunk):
        value = match.group(0)
        normalized = normalize_numeric_id(value)
        if len(normalized) != 10:
            continue
        detections.append(
            build_detection(
                entity_category="government",
                entity_subtype="driver_license",
                detector_id="government.driver_license.context",
                confidence=ConfidenceLevel.MEDIUM,
                validation_status=ValidationStatus.UNKNOWN,
                raw_value=value,
                normalized_value=normalized,
                config=config,
                chunk=chunk,
                chunk_index=index,
                start=match.start(),
                end=match.end(),
                context_keywords=keywords,
            )
        )
    return detections


def _detect_mrz(chunk: str, index: int, config: AppConfig) -> list[DetectionResult]:
    detections: list[DetectionResult] = []
    for match in MRZ_RE.finditer(chunk):
        value = match.group(0)
        is_valid = validate_mrz(value)
        detections.append(
            build_detection(
                entity_category="government",
                entity_subtype="mrz",
                detector_id="government.mrz.regex",
                confidence=ConfidenceLevel.HIGH if is_valid else ConfidenceLevel.LOW,
                validation_status=ValidationStatus.VALID if is_valid else ValidationStatus.INVALID,
                raw_value=value,
                normalized_value=value.replace(" ", ""),
                config=config,
                chunk=chunk,
                chunk_index=index,
                start=match.start(),
                end=match.end(),
                context_keywords=["mrz"],
            )
        )
    return detections
