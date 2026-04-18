from __future__ import annotations

import re
from collections.abc import Iterable

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ConfidenceLevel, ValidationStatus
from pdn_scanner.models import DetectionResult, ExtractedContent
from pdn_scanner.normalize import extract_context_window, normalize_phone, normalize_whitespace
from pdn_scanner.reporting.masking import hash_value, mask_preview

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+7|8)\s*(?:\(\d{3}\)|\d{3})[\s.-]*\d{3}[\s.-]*\d{2}[\s.-]*\d{2}(?!\d)")
NAME_RE = re.compile(r"\b[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?\b")

PHONE_KEYWORDS = ("тел", "телефон", "phone", "моб")
NAME_KEYWORDS = ("фио", "получатель", "сотрудник", "заказчик", "customer_name", "employee", "name")
PERSON_MARKERS = ("физическое лицо", "person", "employee", "субъект", "получатель", "заказчик")
COMPANY_MARKERS = ("ооо", "оао", "пао", "ао", "ип", "ltd", "limited", "company", "компания", "партнеры", "«")
ADDRESS_KEYWORDS = ("address", "destination_address", "адрес", "регистрации", "проживания", "доставки")
ADDRESS_MARKERS = ("г.", "гор.", "город", "ул.", "улица", "пр.", "пр-кт", "пер.", "бул.", "наб.", "д.", "дом", "кв.", "стр.", "обл.", "с.", "п.")
BIRTH_DATE_KEYWORDS = ("дата рождения", "birth date", "date_of_birth", "birth_date", "dob")


def detect_ordinary(content: ExtractedContent, config: AppConfig) -> list[DetectionResult]:
    detections: list[DetectionResult] = []

    for index, chunk in enumerate(content.text_chunks):
        lower_chunk = chunk.lower()

        for match in EMAIL_RE.finditer(chunk):
            value = match.group(0)
            detections.append(
                DetectionResult(
                    category="email",
                    family="ordinary",
                    detector_id="ordinary.email.regex",
                    confidence=ConfidenceLevel.HIGH,
                    validation_status=ValidationStatus.VALID,
                    value_hash=hash_value(value.lower(), config),
                    masked_preview=mask_preview(value, config),
                    location_hints=[f"chunk:{index}"],
                    context_keywords=[],
                    raw_value=value,
                    normalized_value=value.lower(),
                )
            )

        for value, start, end in _iter_phone_matches(chunk):
            normalized = normalize_phone(value)
            if not (config.detection.phone_min_digits <= len(normalized) <= config.detection.phone_max_digits):
                continue

            context = extract_context_window(chunk, start, end, config.detection.context_window).lower()
            keywords = [keyword for keyword in PHONE_KEYWORDS if keyword in context]
            confidence = ConfidenceLevel.HIGH if keywords else ConfidenceLevel.LOW
            if confidence == ConfidenceLevel.LOW:
                continue

            detections.append(
                DetectionResult(
                    category="phone",
                    family="ordinary",
                    detector_id="ordinary.phone.regex",
                    confidence=confidence,
                    validation_status=ValidationStatus.VALID,
                    value_hash=hash_value(normalized, config),
                    masked_preview=mask_preview(normalized, config),
                    location_hints=[f"chunk:{index}"],
                    context_keywords=keywords,
                    raw_value=value,
                    normalized_value=normalized,
                )
            )

        detections.extend(_detect_person_names(chunk, index, config))
        detections.extend(_detect_addresses(chunk, index, config))

        if any(keyword in lower_chunk for keyword in BIRTH_DATE_KEYWORDS):
            match = re.search(r"\b\d{2}[.\-]\d{2}[.\-]\d{4}\b", chunk)
            if match:
                value = match.group(0)
                context_keywords = [keyword for keyword in BIRTH_DATE_KEYWORDS if keyword in lower_chunk]
                detections.append(
                    DetectionResult(
                        category="birth_date_candidate",
                        family="ordinary",
                        detector_id="ordinary.birth_date.context",
                        confidence=ConfidenceLevel.LOW,
                        validation_status=ValidationStatus.UNKNOWN,
                        value_hash=hash_value(value, config),
                        masked_preview=mask_preview(value, config),
                        location_hints=[f"chunk:{index}"],
                        context_keywords=context_keywords,
                        raw_value=value,
                        normalized_value=value,
                    )
                )

    return detections


def _iter_phone_matches(chunk: str) -> Iterable[tuple[str, int, int]]:
    for match in PHONE_RE.finditer(chunk):
        yield match.group(0), match.start(), match.end()


def _detect_person_names(chunk: str, index: int, config: AppConfig) -> list[DetectionResult]:
    lowered = chunk.lower()
    if not any(keyword in lowered for keyword in NAME_KEYWORDS):
        return []
    if _contains_company_marker(lowered):
        return []
    if not any(marker in lowered for marker in PERSON_MARKERS + NAME_KEYWORDS):
        return []

    detections: list[DetectionResult] = []
    candidates = _extract_name_candidates(chunk)
    for value in candidates:
        detections.append(
            DetectionResult(
                category="person_name",
                family="ordinary",
                detector_id="ordinary.person_name.context",
                confidence=ConfidenceLevel.HIGH,
                validation_status=ValidationStatus.UNKNOWN,
                value_hash=hash_value(value.lower(), config),
                masked_preview=mask_preview(value, config),
                location_hints=[f"chunk:{index}"],
                context_keywords=[keyword for keyword in NAME_KEYWORDS if keyword in lowered],
                raw_value=value,
                normalized_value=value.lower(),
            )
        )

    return detections


def _detect_addresses(chunk: str, index: int, config: AppConfig) -> list[DetectionResult]:
    lowered = chunk.lower()
    if not any(keyword in lowered for keyword in ADDRESS_KEYWORDS):
        return []

    value = _extract_labeled_value(chunk, ADDRESS_KEYWORDS)
    if value is None:
        value = chunk

    normalized_value = normalize_whitespace(value)
    marker_hits = sum(1 for marker in ADDRESS_MARKERS if marker in normalized_value.lower())
    if marker_hits < 2:
        return []

    return [
        DetectionResult(
            category="address",
            family="ordinary",
            detector_id="ordinary.address.context",
            confidence=ConfidenceLevel.HIGH,
            validation_status=ValidationStatus.UNKNOWN,
            value_hash=hash_value(normalized_value.lower(), config),
            masked_preview=mask_preview(normalized_value, config),
            location_hints=[f"chunk:{index}"],
            context_keywords=[keyword for keyword in ADDRESS_KEYWORDS if keyword in lowered],
            raw_value=normalized_value,
            normalized_value=normalized_value.lower(),
        )
    ]


def _extract_labeled_value(chunk: str, labels: tuple[str, ...]) -> str | None:
    escaped = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?:{escaped})\s*:\s*([^|]+)", chunk, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _extract_name_candidates(chunk: str) -> list[str]:
    candidates: list[str] = []

    labeled_name = _extract_labeled_value(chunk, ("customer_name", "получатель", "заказчик", "фио", "employee"))
    if labeled_name and NAME_RE.fullmatch(normalize_whitespace(labeled_name)):
        candidates.append(normalize_whitespace(labeled_name))

    last_name = _extract_labeled_value(chunk, ("фамилия",))
    first_name = _extract_labeled_value(chunk, ("имя",))
    middle_name = _extract_labeled_value(chunk, ("отчество",))
    if last_name and first_name and middle_name:
        full_name = normalize_whitespace(f"{last_name} {first_name} {middle_name}")
        if NAME_RE.fullmatch(full_name):
            candidates.append(full_name)

    emergency_contact = re.search(
        r"контакт на случай чс\s*:\s*([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})",
        chunk,
        flags=re.IGNORECASE,
    )
    if emergency_contact:
        value = normalize_whitespace(emergency_contact.group(1))
        if NAME_RE.fullmatch(value):
            candidates.append(value)

    return list(dict.fromkeys(candidates))


def _contains_company_marker(lowered: str) -> bool:
    if "юридическое лицо" in lowered:
        return True

    patterns = (
        r"\bооо\b",
        r"\bоао\b",
        r"\bпао\b",
        r"\bао\b",
        r"\bип\b",
        r"\bltd\b",
        r"\blimited\b",
        r"компания",
        r"партнеры",
        r"«",
    )
    return any(re.search(pattern, lowered) for pattern in patterns)
