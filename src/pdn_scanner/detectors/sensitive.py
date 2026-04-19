from __future__ import annotations

import re

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ConfidenceLevel, ValidationStatus
from pdn_scanner.models import DetectionResult, ExtractedContent

from .common import build_detection

SUBJECT_MARKERS = (
    "субъект",
    "гражданин",
    "пациент",
    "клиент",
    "сотрудник",
    "employee",
    "person",
    "фио",
)

LABELED_PATTERNS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("biometric", "fingerprints", ("отпечатки пальцев", "fingerprints")),
    ("biometric", "iris_pattern", ("радужка", "радужная оболочка", "iris")),
    ("biometric", "voice_print", ("голосовой образец", "voice sample", "voiceprint")),
    ("biometric", "face_geometry", ("геометрия лица", "face geometry", "face recognition")),
    ("special", "health_data", ("состояние здоровья", "диагноз", "медицинские данные")),
    ("special", "religious_beliefs", ("вероисповедание", "религиозные убеждения")),
    ("special", "political_beliefs", ("политические убеждения", "политические взгляды")),
    ("special", "race_data", ("расовая принадлежность", "раса")),
    ("special", "nationality_data", ("национальность", "национальная принадлежность")),
    ("special", "special_category_other", ("интимная жизнь", "сексуальная жизнь")),
)


def detect_sensitive(content: ExtractedContent, config: AppConfig) -> list[DetectionResult]:
    if not config.feature_flags.enable_sensitive_detectors:
        return []

    detections: list[DetectionResult] = []

    for index, chunk in enumerate(content.text_chunks):
        lowered = chunk.lower()
        for family, subtype, phrases in LABELED_PATTERNS:
            detections.extend(_detect_labeled(chunk, lowered, index, family, subtype, phrases, config))
            detections.extend(_detect_contextual(chunk, lowered, index, family, subtype, phrases, config))

    return detections


def _detect_labeled(
    chunk: str,
    lowered: str,
    index: int,
    family: str,
    subtype: str,
    phrases: tuple[str, ...],
    config: AppConfig,
) -> list[DetectionResult]:
    detections: list[DetectionResult] = []
    for phrase in phrases:
        match = re.search(rf"{re.escape(phrase)}\s*:\s*([^\n|;]+)", chunk, flags=re.IGNORECASE)
        if not match:
            continue
        value = match.group(0)
        detections.append(
            build_detection(
                entity_category=family,
                entity_subtype=subtype,
                detector_id="sensitive.labeled_phrase",
                confidence=ConfidenceLevel.HIGH,
                validation_status=ValidationStatus.UNKNOWN,
                raw_value=value,
                normalized_value=value.lower(),
                config=config,
                chunk=chunk,
                chunk_index=index,
                start=match.start(),
                end=match.end(),
                context_keywords=[phrase],
            )
        )
    return detections


def _detect_contextual(
    chunk: str,
    lowered: str,
    index: int,
    family: str,
    subtype: str,
    phrases: tuple[str, ...],
    config: AppConfig,
) -> list[DetectionResult]:
    if not any(marker in lowered for marker in SUBJECT_MARKERS):
        return []

    detections: list[DetectionResult] = []
    for phrase in phrases:
        start = lowered.find(phrase)
        if start < 0:
            continue
        end = start + len(phrase)
        detections.append(
            build_detection(
                entity_category=family,
                entity_subtype=subtype,
                detector_id="sensitive.context_phrase",
                confidence=ConfidenceLevel.MEDIUM,
                validation_status=ValidationStatus.UNKNOWN,
                raw_value=chunk[start:end],
                normalized_value=chunk[start:end].lower(),
                config=config,
                chunk=chunk,
                chunk_index=index,
                start=start,
                end=end,
                context_keywords=[phrase],
            )
        )
    return detections
