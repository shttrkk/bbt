from __future__ import annotations

import re

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ConfidenceLevel, ValidationStatus
from pdn_scanner.models import DetectionResult, ExtractedContent
from pdn_scanner.normalize import extract_context_window, normalize_numeric_id
from pdn_scanner.reporting.masking import hash_value, mask_preview
from pdn_scanner.validators import is_valid_luhn

CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
CARD_KEYWORDS = ("card", "карта", "visa", "mastercard", "мир", "pan")
IDENTIFIER_KEYWORDS = ("number:", "id:", "_id:", "incident", "created:", "updated:", "begin:", "end:")


def detect_payment(content: ExtractedContent, config: AppConfig) -> list[DetectionResult]:
    detections: list[DetectionResult] = []

    for index, chunk in enumerate(content.text_chunks):
        for match in CARD_RE.finditer(chunk):
            value = match.group(0)
            normalized = normalize_numeric_id(value)
            if len(normalized) < 13 or len(normalized) > 19:
                continue

            context = extract_context_window(chunk, match.start(), match.end(), config.detection.context_window).lower()
            keywords = [keyword for keyword in CARD_KEYWORDS if keyword in context]
            is_valid = is_valid_luhn(normalized)
            grouped_presentation = bool(re.search(r"\d{4}[ -]\d{4}[ -]\d{4}", value))
            identifier_context = any(keyword in context for keyword in IDENTIFIER_KEYWORDS)

            if not is_valid and not keywords:
                continue

            if not keywords and not grouped_presentation:
                continue

            if identifier_context and not keywords:
                continue

            detections.append(
                DetectionResult(
                    category="bank_card",
                    family="payment",
                    detector_id="payment.card.regex",
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
