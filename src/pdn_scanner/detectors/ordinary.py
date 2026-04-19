from __future__ import annotations

import re
from collections.abc import Iterable

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ConfidenceLevel, ValidationStatus
from pdn_scanner.models import DetectionResult, ExtractedContent
from pdn_scanner.normalize import extract_context_window, normalize_phone, normalize_whitespace
from pdn_scanner.validators.dates import validate_birth_date

from .common import build_detection

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+7|8)\s*(?:\(\d{3}\)|\d{3})[\s.-]*\d{3}[\s.-]*\d{2}[\s.-]*\d{2}(?!\d)")
NAME_RE = re.compile(r"\b[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?\b")
DATE_RE = re.compile(r"\b\d{2}[.\-]\d{2}[.\-]\d{4}\b")

PHONE_KEYWORDS = ("тел", "телефон", "phone", "моб", "контакт", "контактный", "номер")
NAME_KEYWORDS = ("фио", "получатель", "сотрудник", "заказчик", "customer_name", "employee", "name", "requester")
PERSON_MARKERS = ("физическое лицо", "person", "employee", "субъект", "получатель", "заказчик")
COMPANY_MARKERS = ("ооо", "оао", "пао", "ао", "ип", "ltd", "limited", "company", "компания", "партнеры", "«")
ADDRESS_KEYWORDS = ("address", "destination_address", "адрес", "регистрации", "проживания", "доставки")
ADDRESS_MARKERS = ("г.", "гор.", "город", "ул.", "улица", "пр.", "пр-кт", "пер.", "бул.", "наб.", "д.", "дом", "кв.", "стр.", "обл.", "с.", "п.")
BIRTH_DATE_KEYWORDS = ("дата рождения", "birth date", "date_of_birth", "birth_date", "dob")
BIRTH_PLACE_KEYWORDS = ("место рождения", "birth place", "place_of_birth")
BIRTH_PLACE_MARKERS = ("г.", "город", "гор.", "обл.", "область", "край", "республика", "с.", "пос.", "дер.", "р-н")


def detect_ordinary(content: ExtractedContent, config: AppConfig) -> list[DetectionResult]:
    detections: list[DetectionResult] = []

    for index, chunk in enumerate(content.text_chunks):
        lower_chunk = chunk.lower()

        for match in EMAIL_RE.finditer(chunk):
            value = match.group(0)
            detections.append(
                build_detection(
                    entity_category="ordinary",
                    entity_subtype="email",
                    detector_id="ordinary.email.regex",
                    confidence=ConfidenceLevel.HIGH,
                    validation_status=ValidationStatus.VALID,
                    raw_value=value,
                    normalized_value=value.lower(),
                    config=config,
                    chunk=chunk,
                    chunk_index=index,
                    start=match.start(),
                    end=match.end(),
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
                build_detection(
                    entity_category="ordinary",
                    entity_subtype="phone",
                    detector_id="ordinary.phone.regex",
                    confidence=confidence,
                    validation_status=ValidationStatus.VALID,
                    raw_value=value,
                    normalized_value=normalized,
                    config=config,
                    chunk=chunk,
                    chunk_index=index,
                    start=start,
                    end=end,
                    context_keywords=keywords,
                )
            )

        detections.extend(_detect_person_names(chunk, index, config))
        detections.extend(_detect_addresses(chunk, index, config))
        detections.extend(_detect_birth_place(chunk, index, config))

        if any(keyword in lower_chunk for keyword in BIRTH_DATE_KEYWORDS):
            match = DATE_RE.search(chunk)
            if match:
                value = match.group(0)
                context_keywords = [keyword for keyword in BIRTH_DATE_KEYWORDS if keyword in lower_chunk]
                validation_status = ValidationStatus.VALID if validate_birth_date(value) else ValidationStatus.INVALID
                confidence = ConfidenceLevel.HIGH if validation_status == ValidationStatus.VALID else ConfidenceLevel.LOW
                detections.append(
                    build_detection(
                        entity_category="ordinary",
                        entity_subtype="birth_date",
                        detector_id="ordinary.birth_date.context",
                        confidence=confidence,
                        validation_status=validation_status,
                        raw_value=value,
                        normalized_value=value,
                        config=config,
                        chunk=chunk,
                        chunk_index=index,
                        start=match.start(),
                        end=match.end(),
                        context_keywords=context_keywords,
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
    if not any(marker in lowered for marker in PERSON_MARKERS + NAME_KEYWORDS):
        return []

    detections: list[DetectionResult] = []
    candidates = _extract_name_candidates(chunk)
    for value in candidates:
        detections.append(
            build_detection(
                entity_category="ordinary",
                entity_subtype="person_name",
                detector_id="ordinary.person_name.context",
                confidence=ConfidenceLevel.HIGH,
                validation_status=ValidationStatus.UNKNOWN,
                raw_value=value,
                normalized_value=value.lower(),
                config=config,
                chunk=chunk,
                chunk_index=index,
                start=chunk.find(value),
                end=chunk.find(value) + len(value),
                context_keywords=[keyword for keyword in NAME_KEYWORDS if keyword in lowered],
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
        build_detection(
            entity_category="ordinary",
            entity_subtype="address",
            detector_id="ordinary.address.context",
            confidence=ConfidenceLevel.HIGH,
            validation_status=ValidationStatus.UNKNOWN,
            raw_value=normalized_value,
            normalized_value=normalized_value.lower(),
            config=config,
            chunk=chunk,
            chunk_index=index,
            start=chunk.find(normalized_value) if normalized_value in chunk else 0,
            end=(chunk.find(normalized_value) + len(normalized_value)) if normalized_value in chunk else len(chunk),
            context_keywords=[keyword for keyword in ADDRESS_KEYWORDS if keyword in lowered],
        )
    ]


def _detect_birth_place(chunk: str, index: int, config: AppConfig) -> list[DetectionResult]:
    lowered = chunk.lower()
    if not any(keyword in lowered for keyword in BIRTH_PLACE_KEYWORDS):
        return []

    value = _extract_labeled_value(chunk, BIRTH_PLACE_KEYWORDS)
    if value is None:
        return []

    normalized_value = normalize_whitespace(value)
    if not normalized_value or not any(marker in normalized_value.lower() for marker in BIRTH_PLACE_MARKERS):
        return []

    start = chunk.lower().find(value.lower())
    end = start + len(value) if start >= 0 else len(chunk)
    return [
        build_detection(
            entity_category="ordinary",
            entity_subtype="birth_place",
            detector_id="ordinary.birth_place.context",
            confidence=ConfidenceLevel.MEDIUM,
            validation_status=ValidationStatus.UNKNOWN,
            raw_value=normalized_value,
            normalized_value=normalized_value.lower(),
            config=config,
            chunk=chunk,
            chunk_index=index,
            start=max(start, 0),
            end=end,
            context_keywords=[keyword for keyword in BIRTH_PLACE_KEYWORDS if keyword in lowered],
        )
    ]


def _extract_labeled_value(chunk: str, labels: tuple[str, ...]) -> str | None:
    escaped = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"(?:{escaped})\s*:\s*(.+?)(?=(?:\s+[A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё0-9_ .()/-]{{1,40}}\s*:)|\||$)",
        chunk,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).strip()


def _extract_name_candidates(chunk: str) -> list[str]:
    candidates: list[str] = []

    labeled_name_match = re.search(
        r"(?:customer_name|получатель|заказчик(?:\s+пропуска\s*\(житель\))?|фио|employee|requester)\s*:\s*"
        r"([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?(?:\s+[А-ЯЁ][а-яё]+){1,2})",
        chunk,
        flags=re.IGNORECASE,
    )
    if labeled_name_match:
        labeled_name = normalize_whitespace(labeled_name_match.group(1))
        if NAME_RE.fullmatch(labeled_name):
            candidates.append(labeled_name)

    multiline_labeled_name_match = re.search(
        r"(?:customer_name|получатель|заказчик(?:\s+пропуска\s*\(житель\))?|фио|employee|requester)\s*:\s*\n+\s*"
        r"([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?(?:\s+[А-ЯЁ][а-яё]+){1,2})",
        chunk,
        flags=re.IGNORECASE,
    )
    if multiline_labeled_name_match:
        labeled_name = normalize_whitespace(multiline_labeled_name_match.group(1))
        if NAME_RE.fullmatch(labeled_name):
            candidates.append(labeled_name)

    applicant_line_match = re.search(
        r"(?:^|\n)от [^\n]{1,80}\n\s*([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})",
        chunk,
        flags=re.IGNORECASE,
    )
    if applicant_line_match:
        applicant_name = normalize_whitespace(applicant_line_match.group(1))
        if NAME_RE.fullmatch(applicant_name):
            candidates.append(applicant_name)

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
