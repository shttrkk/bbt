from __future__ import annotations

import re

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ConfidenceLevel, ValidationStatus
from pdn_scanner.models import DetectionResult, ExtractedContent
from pdn_scanner.normalize import extract_context_window, normalize_numeric_id
from pdn_scanner.validators import is_valid_luhn, validate_account_with_bik, validate_bik

from .common import build_detection

CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
ACCOUNT_RE = re.compile(r"\b\d{20}\b")
BIK_RE = re.compile(r"\b\d{9}\b")
CVV_RE = re.compile(r"\b\d{3,4}\b")
CARD_KEYWORDS = ("card", "карта", "visa", "mastercard", "мир", "pan")
ACCOUNT_KEYWORDS = ("счет", "счёт", "account", "расчетный счет", "расчётный счёт", "р/с")
BIK_KEYWORDS = ("бик", "bik")
CVV_KEYWORDS = ("cvv", "cvc", "cvv/cvc")
IDENTIFIER_KEYWORDS = ("number:", "id:", "_id:", "incident", "created:", "updated:", "begin:", "end:")


def detect_payment(content: ExtractedContent, config: AppConfig) -> list[DetectionResult]:
    detections: list[DetectionResult] = []

    for index, chunk in enumerate(content.text_chunks):
        lowered = chunk.lower()
        detections.extend(_detect_cards(chunk, lowered, index, config))
        detections.extend(_detect_bik(chunk, lowered, index, config))
        detections.extend(_detect_bank_accounts(chunk, lowered, index, config))
        detections.extend(_detect_cvv(chunk, lowered, index, config))

    return detections


def _detect_cards(chunk: str, lowered: str, index: int, config: AppConfig) -> list[DetectionResult]:
    detections: list[DetectionResult] = []
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
            build_detection(
                entity_category="payment",
                entity_subtype="bank_card",
                detector_id="payment.card.regex",
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


def _detect_bik(chunk: str, lowered: str, index: int, config: AppConfig) -> list[DetectionResult]:
    detections: list[DetectionResult] = []
    keywords = [keyword for keyword in BIK_KEYWORDS if keyword in lowered]
    if not keywords:
        return detections

    for match in BIK_RE.finditer(chunk):
        value = match.group(0)
        is_valid = validate_bik(value)
        detections.append(
            build_detection(
                entity_category="payment",
                entity_subtype="bik",
                detector_id="payment.bik.context",
                confidence=ConfidenceLevel.HIGH if is_valid else ConfidenceLevel.LOW,
                validation_status=ValidationStatus.VALID if is_valid else ValidationStatus.INVALID,
                raw_value=value,
                normalized_value=value,
                config=config,
                chunk=chunk,
                chunk_index=index,
                start=match.start(),
                end=match.end(),
                context_keywords=keywords,
            )
        )
    return detections


def _detect_bank_accounts(chunk: str, lowered: str, index: int, config: AppConfig) -> list[DetectionResult]:
    detections: list[DetectionResult] = []
    keywords = [keyword for keyword in ACCOUNT_KEYWORDS if keyword in lowered]
    if not keywords:
        return detections

    bik_match = next((match for match in BIK_RE.finditer(chunk) if "бик" in chunk[max(0, match.start() - 6): match.start()].lower()), None)
    bik_value = bik_match.group(0) if bik_match else ""
    for match in ACCOUNT_RE.finditer(chunk):
        value = match.group(0)
        validation_status = (
            ValidationStatus.VALID if bik_value and validate_account_with_bik(value, bik_value) else ValidationStatus.UNKNOWN
        )
        confidence = ConfidenceLevel.HIGH if validation_status == ValidationStatus.VALID else ConfidenceLevel.MEDIUM
        detections.append(
            build_detection(
                entity_category="payment",
                entity_subtype="bank_account",
                detector_id="payment.bank_account.context",
                confidence=confidence,
                validation_status=validation_status,
                raw_value=value,
                normalized_value=value,
                config=config,
                chunk=chunk,
                chunk_index=index,
                start=match.start(),
                end=match.end(),
                context_keywords=keywords + (["бик"] if bik_value else []),
            )
        )
    return detections


def _detect_cvv(chunk: str, lowered: str, index: int, config: AppConfig) -> list[DetectionResult]:
    detections: list[DetectionResult] = []
    keywords = [keyword for keyword in CVV_KEYWORDS if keyword in lowered]
    if not keywords:
        return detections

    has_card_context = any(keyword in lowered for keyword in CARD_KEYWORDS) or "card" in lowered or "карта" in lowered
    if not has_card_context:
        return detections

    for match in CVV_RE.finditer(chunk):
        value = match.group(0)
        detections.append(
            build_detection(
                entity_category="payment",
                entity_subtype="cvv_cvc",
                detector_id="payment.cvv.context",
                confidence=ConfidenceLevel.MEDIUM,
                validation_status=ValidationStatus.UNKNOWN,
                raw_value=value,
                normalized_value=value,
                config=config,
                chunk=chunk,
                chunk_index=index,
                start=match.start(),
                end=match.end(),
                context_keywords=keywords,
            )
        )
    return detections
