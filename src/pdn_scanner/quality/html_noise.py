from __future__ import annotations

import re

from pdn_scanner.models import DetectionResult

UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", flags=re.IGNORECASE)
LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_-]{20,}\b")
HEX_TOKEN_RE = re.compile(r"\b[a-f0-9]{24,}\b", flags=re.IGNORECASE)
NOISE_MARKERS = (
    "window.",
    "document.",
    "datalayer",
    "gtag(",
    "ym(",
    "utm_",
    "session",
    "token",
    "cache-control",
    "onclick",
    "javascript:",
    "function(",
    "const ",
    "let ",
    " var ",
    "=>",
    "{",
    "}",
    "return ",
)
WEB_DOC_MARKERS = ("meta", "canonical", "viewport", "stylesheet", "generator", "theme-color", "journal")
PUBLIC_WEB_MARKERS = (
    "livejournal",
    "жж",
    "follow us",
    "top interesting",
    "checklist",
    "applications ios",
    "android",
    "huawei",
    "telegram",
    "twitter",
    "vkontakte",
    "user agreement",
    "comments",
    "tags",
    "rss",
    "atom",
)
PUBLIC_WEB_SUPPRESSED_CATEGORIES = {
    "address",
    "email",
    "birth_date",
    "birth_place",
    "passport_series",
    "passport_number",
    "passport_series_number",
    "driver_license",
    "mrz",
    "health_data",
    "religious_beliefs",
    "political_beliefs",
    "race_data",
    "nationality_data",
    "special_category_other",
    "fingerprints",
    "iris_pattern",
    "voice_print",
    "face_geometry",
}


def is_html_noise_chunk(chunk: str) -> bool:
    lowered = chunk.lower()
    marker_hits = sum(1 for marker in NOISE_MARKERS if marker in lowered)
    long_tokens = len(LONG_TOKEN_RE.findall(chunk)) + len(HEX_TOKEN_RE.findall(chunk)) + len(UUID_RE.findall(chunk))
    punctuation = sum(1 for char in chunk if char in "{}[]=;<>/&")
    ratio = punctuation / max(len(chunk), 1)
    return marker_hits >= 2 or long_tokens >= 3 or ratio >= 0.08


def is_public_web_page(chunk: str) -> bool:
    lowered = chunk.lower()
    hits = sum(1 for marker in PUBLIC_WEB_MARKERS if marker in lowered)
    return hits >= 3


def should_suppress_html_detection(detection: DetectionResult, chunk: str) -> bool:
    lowered = chunk.lower()
    public_web_page = is_public_web_page(chunk)

    if public_web_page and detection.category in PUBLIC_WEB_SUPPRESSED_CATEGORIES:
        return True

    if detection.category in {"inn_individual", "inn_legal_entity", "snils", "bank_card", "phone"} and (
        UUID_RE.search(chunk) or LONG_TOKEN_RE.search(chunk) or "token" in lowered
    ):
        return True

    if detection.category == "person_name":
        has_person_label = any(
            marker in lowered
            for marker in ("фио", "employee", "full name", "first name", "last name", "requester", "applicant", "recipient")
        )
        if any(marker in lowered for marker in WEB_DOC_MARKERS) and not has_person_label:
            return True
        if "живого журнала" in lowered:
            return True

    return is_html_noise_chunk(chunk) and not detection.context_keywords
