from __future__ import annotations

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ConfidenceLevel, ValidationStatus
from pdn_scanner.models import DetectionResult, ExtractedContent
from pdn_scanner.reporting.masking import hash_value, mask_preview

STRICT_PHRASES: dict[str, tuple[str, str]] = {
    "biometric_data": ("biometric", "биометрические персональные данные"),
    "health_data": ("special", "состояние здоровья:"),
    "nationality_data": ("special", "национальность:"),
    "religion_data": ("special", "вероисповедание:"),
}


def detect_sensitive(content: ExtractedContent, config: AppConfig) -> list[DetectionResult]:
    if not config.feature_flags.enable_sensitive_detectors:
        return []

    detections: list[DetectionResult] = []

    for index, chunk in enumerate(content.text_chunks):
        lowered = chunk.lower()
        for category, (family, phrase) in STRICT_PHRASES.items():
            if phrase not in lowered:
                continue

            detections.append(
                DetectionResult(
                    category=category,
                    family=family,
                    detector_id="sensitive.strict_phrase",
                    confidence=ConfidenceLevel.MEDIUM,
                    validation_status=ValidationStatus.UNKNOWN,
                    value_hash=hash_value(phrase, config),
                    masked_preview=mask_preview(phrase, config),
                    location_hints=[f"chunk:{index}"],
                    context_keywords=[phrase],
                    raw_value=phrase,
                    normalized_value=phrase,
                )
            )

    return detections
