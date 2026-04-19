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
INTL_PHONE_RE = re.compile(r"(?<!\d)(?:\+\d{1,3}[\s().-]*)?(?:\(?\d{2,4}\)?[\s().-]*){2,4}\d{2,4}(?!\d)")
CYRILLIC_NAME_RE = re.compile(r"\b[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?\b")
LATIN_NAME_RE = re.compile(r"\b[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?(?:\s+[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?){1,2}\b")
DATE_RE = re.compile(r"\b\d{2}[.\-]\d{2}[.\-]\d{4}\b")
ZIP_RE = re.compile(r"\b\d{5}(?:-\d{4})?\b")
UK_POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b")

PHONE_KEYWORDS = (
    "тел",
    "телефон",
    "phone",
    "phone number",
    "telephone",
    "mobile phone",
    "mobile number",
    "contact number",
    "cell phone",
    "моб",
    "контакт",
    "контактный",
    "номер",
)
NAME_KEYWORDS = (
    "фио",
    "first name",
    "last name",
    "middle name",
    "middle initial",
    "given name",
    "forename",
    "surname",
    "family name",
    "получатель",
    "сотрудник",
    "заказчик",
    "customer_name",
    "customer name",
    "employee",
    "employee name",
    "full name",
    "applicant",
    "recipient",
    "contact person",
    "name",
    "requester",
    "requestor",
)
STRONG_NAME_KEYWORDS = tuple(keyword for keyword in NAME_KEYWORDS if keyword != "name")
PERSON_MARKERS = (
    "физическое лицо",
    "person",
    "employee",
    "subject",
    "субъект",
    "получатель",
    "заказчик",
    "requester",
    "requestor",
    "applicant",
    "recipient",
    "contact person",
)
COMPANY_MARKERS = (
    "ооо",
    "оао",
    "пао",
    "ао",
    "ип",
    "ltd",
    "limited",
    "llc",
    "inc",
    "corp",
    "corporation",
    "company",
    "co.",
    "компания",
    "партнеры",
    "university",
    "institute",
    "department",
    "agency",
    "bank",
    "office",
    "«",
)
ADDRESS_KEYWORDS = (
    "address",
    "address line",
    "street address",
    "mailing address",
    "home address",
    "residential address",
    "residence address",
    "permanent address",
    "registered address",
    "shipping address",
    "destination_address",
    "адрес",
    "регистрации",
    "проживания",
    "доставки",
)
ADDRESS_MARKERS = ("г.", "гор.", "город", "ул.", "улица", "пр.", "пр-кт", "пер.", "бул.", "наб.", "д.", "дом", "кв.", "стр.", "обл.", "с.", "п.")
ENGLISH_ADDRESS_MARKERS = (
    "street",
    "st.",
    "road",
    "rd.",
    "avenue",
    "ave.",
    "boulevard",
    "blvd",
    "lane",
    "ln.",
    "drive",
    "dr.",
    "court",
    "ct.",
    "place",
    "pl.",
    "way",
    "apt",
    "apartment",
    "suite",
    "unit",
    "floor",
    "city",
    "state",
    "zip",
    "postal code",
)
ENGLISH_BIRTH_PLACE_MARKERS = ("city", "state", "county", "district", "province", "region", "country", "town")
BIRTH_DATE_KEYWORDS = ("дата рождения", "birth date", "date of birth", "date_of_birth", "birth_date", "dob")
BIRTH_PLACE_KEYWORDS = (
    "место рождения",
    "birth place",
    "place of birth",
    "place_of_birth",
    "birthplace",
    "city of birth",
    "country of birth",
)
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
            phone_max_digits = 15 if value.lstrip().startswith("+") else config.detection.phone_max_digits
            if not (config.detection.phone_min_digits <= len(normalized) <= phone_max_digits):
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
    seen: set[tuple[int, int, str]] = set()
    for regex in (PHONE_RE, INTL_PHONE_RE):
        for match in regex.finditer(chunk):
            value = normalize_whitespace(match.group(0))
            digits = normalize_phone(value)
            if len(digits) < 10 or len(digits) > 15:
                continue
            if regex is INTL_PHONE_RE and "+" not in value and value.count("-") + value.count(" ") < 2 and "(" not in value:
                continue
            key = (match.start(), match.end(), digits)
            if key in seen:
                continue
            seen.add(key)
            yield value, match.start(), match.end()


def _detect_person_names(chunk: str, index: int, config: AppConfig) -> list[DetectionResult]:
    lowered = chunk.lower()
    if not any(keyword in lowered for keyword in NAME_KEYWORDS):
        return []
    if not any(marker in lowered for marker in PERSON_MARKERS) and not any(keyword in lowered for keyword in STRONG_NAME_KEYWORDS):
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
        value = _extract_generic_address_value(chunk)
    if value is None:
        value = chunk

    normalized_value = normalize_whitespace(value)
    if not _looks_like_address(normalized_value):
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
    if not _looks_like_birth_place(normalized_value):
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
        rf"(?:{escaped})\s*:\s*([\s\S]+?)(?=(?:\s+[A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё_ .()/-]{{1,40}}\s*:)|\||$)",
        chunk,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).strip()


def _extract_name_candidates(chunk: str) -> list[str]:
    candidates: list[str] = []
    name_labels = (
        "first name",
        "last name",
        "middle name",
        "middle initial",
        "given name",
        "forename",
        "surname",
        "family name",
        "customer_name",
        "customer name",
        "получатель",
        "заказчик(?:\\s+пропуска\\s*\\(житель\\))?",
        "фио",
        "employee(?:\\s+name)?",
        "requester",
        "requestor",
        "applicant",
        "recipient",
        "contact person",
        "full name",
        "name",
    )
    escaped_labels = "|".join(name_labels)
    name_value_pattern = (
        r"([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?(?:[ \t]+[А-ЯЁ][а-яё]+){1,2}|"
        r"[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?(?:[ \t]+[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?){1,2})"
    )

    labeled_name_match = re.search(
        rf"(?:{escaped_labels})\s*:\s*{name_value_pattern}",
        chunk,
        flags=re.IGNORECASE,
    )
    if labeled_name_match:
        labeled_name = normalize_whitespace(labeled_name_match.group(1))
        if _is_person_name_candidate(labeled_name):
            candidates.append(labeled_name)

    multiline_labeled_name_match = re.search(
        rf"(?:{escaped_labels})\s*:\s*\n+\s*{name_value_pattern}",
        chunk,
        flags=re.IGNORECASE,
    )
    if multiline_labeled_name_match:
        labeled_name = normalize_whitespace(multiline_labeled_name_match.group(1))
        if _is_person_name_candidate(labeled_name):
            candidates.append(labeled_name)

    applicant_line_match = re.search(
        rf"(?:^|\n)от [^\n]{{1,80}}\n\s*{name_value_pattern}",
        chunk,
        flags=re.IGNORECASE,
    )
    if applicant_line_match:
        applicant_name = normalize_whitespace(applicant_line_match.group(1))
        if _is_person_name_candidate(applicant_name):
            candidates.append(applicant_name)

    ru_last_name = _extract_labeled_value(chunk, ("фамилия",))
    ru_first_name = _extract_labeled_value(chunk, ("имя",))
    ru_middle_name = _extract_labeled_value(chunk, ("отчество",))
    if ru_last_name and ru_first_name and ru_middle_name:
        full_name = normalize_whitespace(f"{ru_last_name} {ru_first_name} {ru_middle_name}")
        if _is_person_name_candidate(full_name):
            candidates.append(full_name)

    en_first_name = _extract_labeled_value(chunk, ("first name", "given name", "forename"))
    en_last_name = _extract_labeled_value(chunk, ("last name", "surname", "family name"))
    en_middle_name = _extract_labeled_value(chunk, ("middle name", "middle initial"))
    if en_first_name and en_last_name:
        full_name = normalize_whitespace(" ".join(part for part in (en_first_name, en_middle_name, en_last_name) if part))
        if _is_person_name_candidate(full_name):
            candidates.append(full_name)

    emergency_contact = re.search(
        rf"контакт на случай чс\s*:\s*{name_value_pattern}",
        chunk,
        flags=re.IGNORECASE,
    )
    if emergency_contact:
        value = normalize_whitespace(emergency_contact.group(1))
        if _is_person_name_candidate(value):
            candidates.append(value)

    return list(dict.fromkeys(candidates))


def _is_person_name_candidate(value: str) -> bool:
    normalized = normalize_whitespace(value)
    if not normalized or _contains_company_marker(normalized):
        return False
    lowered = normalized.lower()
    leaked_label_markers = (
        "first name",
        "last name",
        "middle name",
        "middle initial",
        "given name",
        "forename",
        "surname",
        "family name",
        "дата рождения",
        "date of birth",
        "birth date",
        "address",
        "адрес",
        "phone",
        "телефон",
    )
    if any(marker in lowered for marker in leaked_label_markers):
        return False
    return bool(CYRILLIC_NAME_RE.fullmatch(normalized) or LATIN_NAME_RE.fullmatch(normalized))


def _looks_like_address(value: str) -> bool:
    lowered = value.lower()
    ru_marker_hits = sum(1 for marker in ADDRESS_MARKERS if marker in lowered)
    if ru_marker_hits >= 2:
        return True

    en_marker_hits = sum(1 for marker in ENGLISH_ADDRESS_MARKERS if marker in lowered)
    has_house_number = bool(re.search(r"\b\d+[A-Za-z]?\b", value))
    has_postcode = bool(ZIP_RE.search(value) or UK_POSTCODE_RE.search(value))
    return en_marker_hits >= 2 or (en_marker_hits >= 1 and has_house_number and ("," in value or has_postcode))


def _looks_like_birth_place(value: str) -> bool:
    normalized = normalize_whitespace(value)
    if not normalized:
        return False

    lowered = normalized.lower()
    if _contains_company_marker(normalized):
        return False
    if any(marker in lowered for marker in BIRTH_PLACE_MARKERS):
        return True
    if any(marker in lowered for marker in ENGLISH_BIRTH_PLACE_MARKERS):
        return True
    if "," in normalized and re.search(r"[A-Za-zА-Яа-яЁё]", normalized):
        return True

    tokens = normalized.split()
    if 1 <= len(tokens) <= 4 and all(token[:1].isupper() for token in tokens if token[:1].isalpha()):
        return True
    return False


def _contains_company_marker(value: str) -> bool:
    lowered = value.lower()
    for marker in COMPANY_MARKERS:
        if re.search(rf"(?<![\w-]){re.escape(marker)}(?![\w-])", lowered):
            return True
    return False


def _extract_generic_address_value(chunk: str) -> str | None:
    match = re.search(
        r"(?:^|\||\s)(?:[A-Za-zА-Яа-яЁё_ .()/-]{0,40})?(?:address|адрес)(?:[A-Za-zА-Яа-яЁё_ .()/-]{0,40})?\s*:\s*"
        r"([\s\S]+?)(?=(?:\s+[A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё_ .()/-]{1,40}\s*:)|\||$)",
        chunk,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).strip()
