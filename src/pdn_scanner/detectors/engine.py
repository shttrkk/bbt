from __future__ import annotations

from pdn_scanner.config import AppConfig
from pdn_scanner.models import DetectionResult, ExtractedContent
from pdn_scanner.normalize import normalize_text

from .government import detect_government
from .ordinary import detect_ordinary
from .payment import detect_payment
from .sensitive import detect_sensitive


class DetectionEngine:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def detect(self, content: ExtractedContent) -> list[DetectionResult]:
        normalized_chunks = [normalize_text(chunk) for chunk in content.text_chunks if chunk.strip()]
        limited_chunks = normalized_chunks[: self.config.detection.max_text_chunks_per_file]
        normalized_content = content.model_copy(update={"text_chunks": limited_chunks})

        detections: list[DetectionResult] = []
        detections.extend(detect_ordinary(normalized_content, self.config))
        detections.extend(detect_government(normalized_content, self.config))
        detections.extend(detect_payment(normalized_content, self.config))
        detections.extend(detect_sensitive(normalized_content, self.config))
        return self._deduplicate(detections)

    def _deduplicate(self, detections: list[DetectionResult]) -> list[DetectionResult]:
        aggregated: dict[tuple[str, str, str | None], DetectionResult] = {}

        for detection in detections:
            key = (detection.family, detection.category, detection.value_hash)
            existing = aggregated.get(key)
            if existing is None:
                aggregated[key] = detection
                continue

            existing.occurrences += detection.occurrences
            existing.location_hints = sorted(set(existing.location_hints + detection.location_hints))
            existing.context_keywords = sorted(set(existing.context_keywords + detection.context_keywords))

        return list(aggregated.values())
