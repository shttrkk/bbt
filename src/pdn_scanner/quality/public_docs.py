from __future__ import annotations

from pdn_scanner.enums import ConfidenceLevel, ValidationStatus
from pdn_scanner.models import DetectionResult

PUBLIC_DOC_KEYWORDS = (
    "privacy",
    "privacy policy",
    "terms",
    "terms of service",
    "rules",
    "cookies",
    "policy",
    "политика",
    "cookies",
    "персональные данные",
    "обработка персональных данных",
    "соглашение",
    "правила",
    "условия использования",
)
LEGAL_MARKERS = (
    "оператор персональных данных",
    "субъект персональных данных",
    "consent",
    "controller",
    "lawful basis",
    "конфиденциальность",
    "настоящая политика",
    "персональных данных",
)


def detect_public_doc(path: str, text: str, detections: list[DetectionResult]) -> tuple[bool, list[str]]:
    combined = f"{path}\n{text}".lower()
    keyword_hits = sum(1 for keyword in PUBLIC_DOC_KEYWORDS if keyword in combined)
    legal_hits = sum(1 for marker in LEGAL_MARKERS if marker in combined)
    trusted_personal = sum(1 for detection in detections if _is_subject_signal(detection))
    validated_identifiers = sum(1 for detection in detections if _is_validated_identifier(detection))

    reasons: list[str] = []
    if keyword_hits >= 2:
        reasons.append("PUBLIC_DOC_KEYWORDS")
    if legal_hits >= 1:
        reasons.append("PUBLIC_DOC_LEGAL_TEXT")

    is_public_doc = keyword_hits + legal_hits >= 3 and trusted_personal == 0 and validated_identifiers == 0
    return is_public_doc, reasons if is_public_doc else []


def _is_subject_signal(detection: DetectionResult) -> bool:
    return detection.category in {"person_name", "address", "birth_date_candidate"} and detection.confidence in {
        ConfidenceLevel.HIGH,
        ConfidenceLevel.MEDIUM,
    }


def _is_validated_identifier(detection: DetectionResult) -> bool:
    return detection.family in {"government", "payment"} and detection.validation_status == ValidationStatus.VALID
