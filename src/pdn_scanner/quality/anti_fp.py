from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ConfidenceLevel, FileFormat, ValidationStatus
from pdn_scanner.models import DetectionResult, ExtractedContent, FileDescriptor

from .html_noise import should_suppress_html_detection
from .public_docs import detect_public_doc
from .reference_data import detect_reference_data
from .templates import detect_template_like

STRONG_SCHEMA_HINTS = {
    "person_name": ("customer_name", "person_name", "employee", "employee_name", "fio", "фио", "full_name"),
    "address": ("destination_address", "address", "registered_address", "delivery_address", "адрес"),
    "phone": ("phone", "mobile", "contact_phone", "телефон", "тел"),
    "email": ("email", "e-mail", "почта"),
    "snils": ("snils", "снилс"),
    "inn": ("inn", "инн"),
    "birth_date_candidate": ("birth", "birth_date", "date_of_birth", "dob", "дата рождения"),
    "bank_card": ("card", "pan", "номер карты", "банковская карта"),
}
ID_HEAVY_FIELD_MARKERS = (
    "id",
    "_id",
    "uuid",
    "guid",
    "token",
    "hash",
    "checksum",
    "incident",
    "status",
    "created",
    "updated",
    "timestamp",
    "plan",
    "product",
    "catalog",
    "code",
    "key",
)
PUBLIC_CONTACT_CATEGORIES = {"email", "phone"}


@dataclass(slots=True)
class QualityAssessment:
    detections: list[DetectionResult]
    reasons: list[str] = field(default_factory=list)
    is_template: bool = False
    is_public_doc: bool = False
    is_reference_data: bool = False
    validated_entities_count: int = 0
    suspicious_entities_count: int = 0
    confidence_summary: dict[str, int] = field(default_factory=dict)


class QualityLayer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def assess(
        self,
        descriptor: FileDescriptor,
        extraction: ExtractedContent,
        detections: list[DetectionResult],
    ) -> QualityAssessment:
        adjusted: list[DetectionResult] = []
        reasons: list[str] = []

        for detection in detections:
            updated_detection, suppression_reasons = self._adjust_detection(descriptor, extraction, detection)
            if updated_detection is None:
                reasons.extend(suppression_reasons)
                continue
            adjusted.append(updated_detection)

        sample_text = " ".join(extraction.text_chunks[:20])
        is_template, template_reasons = (False, [])
        if self.config.feature_flags.enable_template_heuristics:
            is_template, template_reasons = detect_template_like(sample_text, adjusted)
        is_public_doc, public_reasons = detect_public_doc(descriptor.rel_path, sample_text, adjusted)
        is_reference_data, reference_reasons = detect_reference_data(descriptor, extraction, adjusted)

        reasons.extend(template_reasons)
        reasons.extend(public_reasons)
        reasons.extend(reference_reasons)

        adjusted = self._apply_file_level_suppression(
            adjusted,
            is_template=is_template,
            is_public_doc=is_public_doc,
            is_reference_data=is_reference_data,
        )

        return QualityAssessment(
            detections=adjusted,
            reasons=sorted(set(reasons)),
            is_template=is_template,
            is_public_doc=is_public_doc,
            is_reference_data=is_reference_data,
            validated_entities_count=self._validated_entities_count(adjusted),
            suspicious_entities_count=self._suspicious_entities_count(adjusted),
            confidence_summary=self._confidence_summary(adjusted),
        )

    def _adjust_detection(
        self,
        descriptor: FileDescriptor,
        extraction: ExtractedContent,
        detection: DetectionResult,
    ) -> tuple[DetectionResult | None, list[str]]:
        chunk = self._resolve_chunk(extraction, detection)
        chunk_lower = chunk.lower()
        extractor_name = str(extraction.metadata.get("extractor", "")).lower()
        is_structured = extractor_name in {"csv", "json", "parquet"}
        reasons: list[str] = []

        if descriptor.detected_format == FileFormat.HTML and should_suppress_html_detection(detection, chunk):
            return None, [f"SUPPRESSED_HTML_NOISE:{detection.category}"]

        if detection.category == "person_name" and self._looks_like_non_personal_name(chunk, detection):
            return None, ["SUPPRESSED_NON_PERSON_NAME"]

        if detection.category == "birth_date_candidate" and not self._has_birth_context(chunk_lower):
            return None, ["SUPPRESSED_BIRTH_DATE_NO_CONTEXT"]

        if is_structured and self._should_suppress_structured_noise(detection, chunk_lower):
            return None, [f"SUPPRESSED_STRUCTURED_NOISE:{detection.category}"]

        if is_structured:
            detection = self._boost_confidence_from_schema(detection, chunk_lower)

        return detection, reasons

    def _apply_file_level_suppression(
        self,
        detections: list[DetectionResult],
        *,
        is_template: bool,
        is_public_doc: bool,
        is_reference_data: bool,
    ) -> list[DetectionResult]:
        if is_template and not any(self._is_trusted_detection(detection) for detection in detections):
            return []

        if is_public_doc and not any(self._is_subject_signal(detection) for detection in detections):
            return [detection for detection in detections if detection.category not in PUBLIC_CONTACT_CATEGORIES]

        if is_reference_data and not any(self._is_trusted_detection(detection) for detection in detections):
            return []

        return detections

    def _boost_confidence_from_schema(self, detection: DetectionResult, chunk_lower: str) -> DetectionResult:
        hints = STRONG_SCHEMA_HINTS.get(detection.category, ())
        if not any(hint in chunk_lower for hint in hints):
            return detection

        new_confidence = detection.confidence
        if detection.confidence == ConfidenceLevel.LOW:
            new_confidence = ConfidenceLevel.MEDIUM
        elif detection.confidence == ConfidenceLevel.MEDIUM and detection.validation_status == ValidationStatus.VALID:
            new_confidence = ConfidenceLevel.HIGH

        if new_confidence == detection.confidence:
            return detection

        return detection.model_copy(update={"confidence": new_confidence})

    def _should_suppress_structured_noise(self, detection: DetectionResult, chunk_lower: str) -> bool:
        hints = STRONG_SCHEMA_HINTS.get(detection.category, ())
        if any(hint in chunk_lower for hint in hints):
            return False

        id_heavy = sum(1 for marker in ID_HEAVY_FIELD_MARKERS if marker in chunk_lower)
        if detection.category in {"inn", "snils", "bank_card", "phone"} and id_heavy >= 2:
            return True

        if detection.category == "birth_date_candidate" and "дата рождения" not in chunk_lower and "birth" not in chunk_lower:
            return True

        if detection.category == "person_name" and "name:" in chunk_lower and not any(
            hint in chunk_lower for hint in ("customer_name", "employee", "фио", "person")
        ):
            return True

        return False

    def _looks_like_non_personal_name(self, chunk: str, detection: DetectionResult) -> bool:
        lowered = chunk.lower()
        raw_value = (detection.raw_value or "").lower()
        if "живого журнала" in raw_value:
            return True
        if any(marker in lowered for marker in ("privacy", "rules", "policy", "cookies", "journal")) and "фио" not in lowered:
            return True
        return False

    def _has_birth_context(self, chunk_lower: str) -> bool:
        return any(marker in chunk_lower for marker in ("дата рождения", "birth date", "date_of_birth", "dob", "birth_date"))

    def _resolve_chunk(self, extraction: ExtractedContent, detection: DetectionResult) -> str:
        for hint in detection.location_hints:
            if not hint.startswith("chunk:"):
                continue
            match = re.match(r"chunk:(\d+)", hint)
            if not match:
                continue
            index = int(match.group(1))
            if 0 <= index < len(extraction.text_chunks):
                return extraction.text_chunks[index]
        return ""

    def _validated_entities_count(self, detections: list[DetectionResult]) -> int:
        count = 0
        for detection in detections:
            if detection.validation_status == ValidationStatus.VALID:
                count += detection.occurrences
        return count

    def _suspicious_entities_count(self, detections: list[DetectionResult]) -> int:
        count = 0
        for detection in detections:
            if detection.validation_status == ValidationStatus.INVALID or detection.confidence == ConfidenceLevel.LOW:
                count += detection.occurrences
        return count

    def _confidence_summary(self, detections: list[DetectionResult]) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for detection in detections:
            counter[detection.confidence.value] += detection.occurrences
        return dict(counter)

    def _is_subject_signal(self, detection: DetectionResult) -> bool:
        return detection.category in {"person_name", "address", "birth_date_candidate"} and detection.confidence in {
            ConfidenceLevel.HIGH,
            ConfidenceLevel.MEDIUM,
        }

    def _is_trusted_detection(self, detection: DetectionResult) -> bool:
        if detection.family in {"government", "payment"} and detection.validation_status == ValidationStatus.VALID:
            return True
        return detection.confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM} and detection.category in {
            "person_name",
            "address",
        }
