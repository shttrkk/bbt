from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import unquote

from pdn_scanner.enums import ConfidenceLevel, FileFormat, StorageClass, ValidationStatus
from pdn_scanner.models import DetectionResult, ExtractedContent, FileDescriptor

HARD_PERSONAL_CATEGORIES = {
    "snils",
    "passport_series",
    "passport_number",
    "passport_series_number",
    "inn_individual",
    "bank_card",
    "driver_license",
    "mrz",
}
PUBLIC_OVERRIDE_BLOCKERS = {
    "snils",
    "passport_series",
    "passport_number",
    "passport_series_number",
    "bank_card",
    "driver_license",
    "mrz",
}
COMPANION_CATEGORIES = {"address", "phone", "email", "birth_date", "birth_place"}
JUSTIFIED_PUBLIC_MARKERS = (
    "координаты для связи",
    "контактные данные ответственных",
    "структурных подразделений",
    "contact directory",
    "directory",
    "public self disclosure",
    "self disclosure",
    "public report",
    "публичный отчет",
    "публичный отчёт",
    "самообслед",
    "официальный сайт",
    "official",
    "responsible person",
    "ответственный",
    "ответственных",
    "университет",
    "university",
    "академия",
    "academy",
    "институт",
    "institute",
    "department",
    "подразделени",
)
PUBLIC_REPORT_MARKERS = (
    "policy",
    "privacy",
    "report",
    "article",
    "brochure",
    "news",
    "протокол",
    "реестр",
    "registry",
    "extract",
    "выписка",
    "публич",
    "самообслед",
    "disclosure",
)
ROLE_CONTACT_MARKERS = (
    "info@",
    "support@",
    "sales@",
    "press@",
    "hr@",
    "marketing@",
    "контакт",
    "contact",
    "телефон",
    "phone",
    "email",
    "e-mail",
)
PERSONAL_FORM_MARKERS = (
    "анкета",
    "anketa",
    "application",
    "applicant",
    "candidate",
    "заявлен",
    "соглас",
    "consent",
    "доверен",
    "power of attorney",
    "employee card",
    "employee profile",
    "passport",
    "паспорт",
    "snils",
    "снилс",
    "инн",
    "resume",
    "curriculum vitae",
    "personal details",
)
INTERNAL_DOC_MARKERS = (
    "employee",
    "сотрудник",
    "кадры",
    "hr",
    "personnel",
    "рабоч",
    "пропуск",
    "компенсац",
    "служеб",
    "доставка оборудования",
    "delivery",
    "home-office",
    "internet reimbursement",
    "requester",
    "recipient",
)
CORRESPONDENCE_MARKERS = (
    "subject:",
    "from:",
    "to:",
    "re:",
    "fw:",
    "переписка",
    "писем",
    "доставка кресла",
    "сообщение",
)
PERSONAL_EXPORT_PATH_MARKERS = (
    "customers",
    "customer",
    "clients",
    "client",
    "subscribers",
    "billing/full",
    "logistics",
    "shipping",
    "delivery",
    "addresses",
    "physical.parquet",
)
PERSONAL_EXPORT_HEADER_MARKERS = (
    "customer_name",
    "customer type",
    "customer_type",
    "full name",
    "fio",
    "фио",
    "name",
    "address",
    "destination_address",
    "phone",
    "email",
    "passport",
    "snils",
    "inn",
    "birth",
)
COMPANY_EXPORT_MARKERS = (
    "company",
    "company_name",
    "organization",
    "organisation",
    "corporate",
    "contact",
    "contact_person",
    "contact person",
    "юридическ",
)
ORG_SUFFIX_MARKERS = (
    " llc",
    " inc",
    " corp",
    " ltd",
    " and sons",
    " group",
    " company",
    " holdings",
    " ооо ",
    " ао ",
    " пао ",
)
ORG_REQUISITE_MARKERS = (
    "инн организации",
    "legal entity",
    "юридическое лицо",
    "расчетный счет",
    "расчётный счёт",
    "бик",
    "kpp",
    "кпп",
    "operator",
    "оператор",
)
IMAGE_DOC_MARKERS = (
    "scan",
    "скан",
    "паспорт",
    "passport",
    "id card",
    "document image",
    "удостоверение",
)


@dataclass(slots=True)
class LeakContextAssessment:
    storage_class: StorageClass
    primary_genre: str
    genre_tags: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    risk_score: int = 0
    justification_score: int = 0
    noise_score: int = 0


def assess_leak_context(
    descriptor: FileDescriptor,
    extraction: ExtractedContent,
    candidate_detections: list[DetectionResult],
    final_detections: list[DetectionResult],
    *,
    is_template: bool,
    is_public_doc: bool,
    is_reference_data: bool,
) -> LeakContextAssessment:
    path_lower = unquote(descriptor.rel_path).lower()
    sample_text = " ".join(extraction.text_chunks[:20]).lower()
    header = [str(item).lower() for item in extraction.metadata.get("header", [])]
    combined = f"{path_lower}\n{sample_text}"
    counts = Counter()
    for detection in candidate_detections:
        counts[detection.category] += detection.occurrences
    categories = set(counts)

    hard_anchors = bool(categories.intersection(HARD_PERSONAL_CATEGORIES))
    companions = bool(categories.intersection(COMPANION_CATEGORIES))
    person_name = counts.get("person_name", 0) > 0
    special_or_biometric = any(d.family in {"special", "biometric"} for d in candidate_detections)
    trusted_personal = any(_is_trusted_personal_detection(d) for d in candidate_detections)
    validated_payment = any(d.family == "payment" and d.validation_status == ValidationStatus.VALID for d in candidate_detections)
    structured = str(extraction.metadata.get("extractor", "")).lower() in {"csv", "json", "parquet", "xls"}
    row_count = extraction.structured_rows_scanned

    genres: set[str] = set()
    reasons: list[str] = []
    risk_score = 0
    justification_score = 0
    noise_score = 0

    if is_template:
        genres.add("blank_template")
        reasons.append("LEAK_CONTEXT_TEMPLATE")
        noise_score += 5

    personal_form = _looks_like_personal_form(combined, is_template=is_template)
    public_contact_doc = _looks_like_public_contact_doc(combined, counts, trusted_personal, personal_form=personal_form)
    public_report = _looks_like_public_report(combined, personal_form=personal_form)
    org_requisites = _looks_like_org_requisites_doc(combined, counts)
    internal_doc = _looks_like_internal_doc(combined)
    correspondence = _looks_like_correspondence(combined)
    image_personal_doc = _looks_like_image_personal_doc(descriptor, combined, hard_anchors, special_or_biometric)
    personal_export = _looks_like_personal_export(path_lower, header, combined, structured, row_count, counts, hard_anchors, companions)
    company_export = _looks_like_company_export(path_lower, header, combined, structured, row_count, counts, hard_anchors)

    if public_contact_doc:
        genres.add("public_contact_doc")
        reasons.append("LEAK_CONTEXT_PUBLIC_CONTACT_DOC")
        justification_score += 5
    if public_report or is_public_doc:
        genres.add("public_report")
        reasons.append("LEAK_CONTEXT_PUBLIC_REPORT")
        justification_score += 4
    if org_requisites:
        genres.add("org_requisites_doc")
        reasons.append("LEAK_CONTEXT_ORG_REQUISITES")
        noise_score += 4
    if personal_form:
        genres.add("personal_form")
        reasons.append("LEAK_CONTEXT_PERSONAL_FORM")
        risk_score += 4
    if internal_doc:
        genres.add("internal_employee_doc")
        reasons.append("LEAK_CONTEXT_INTERNAL_DOC")
        risk_score += 4
    if correspondence:
        genres.add("correspondence")
        reasons.append("LEAK_CONTEXT_CORRESPONDENCE")
        risk_score += 4
    if image_personal_doc:
        genres.add("image_of_personal_doc")
        reasons.append("LEAK_CONTEXT_DOCUMENT_IMAGE")
        risk_score += 5
    if personal_export:
        genres.add("personal_export")
        reasons.append("LEAK_CONTEXT_PERSONAL_EXPORT")
        risk_score += 5
    if company_export:
        genres.add("company_export")
        reasons.append("LEAK_CONTEXT_COMPANY_EXPORT")
        justification_score += 3

    if hard_anchors:
        reasons.append("LEAK_CONTEXT_HARD_ANCHOR")
        risk_score += 4
    if special_or_biometric:
        reasons.append("LEAK_CONTEXT_SPECIAL_OR_BIOMETRIC")
        risk_score += 5
    if validated_payment:
        reasons.append("LEAK_CONTEXT_VALIDATED_PAYMENT")
        risk_score += 4
    if _has_personal_bundle(counts):
        reasons.append("LEAK_CONTEXT_PERSONAL_BUNDLE")
        risk_score += 3
    if structured and row_count >= 50 and (person_name or companions or hard_anchors):
        reasons.append("LEAK_CONTEXT_SUBJECT_LEVEL_ROWS")
        risk_score += 2

    if is_reference_data and not personal_export:
        reasons.append("LEAK_CONTEXT_REFERENCE_DATA")
        noise_score += 3
    if not candidate_detections:
        reasons.append("LEAK_CONTEXT_NO_PERSONAL_SIGNAL")
        noise_score += 2
    if not trusted_personal and not hard_anchors and not special_or_biometric and not validated_payment:
        noise_score += 1

    storage_class = StorageClass.NON_TARGET
    primary_genre = "unknown"
    if risk_score >= 5 and risk_score > justification_score + max(1, noise_score // 2):
        storage_class = StorageClass.TARGET_LEAK
        primary_genre = _pick_primary_genre(genres, default="personal_record")
    elif justification_score >= 4 and (trusted_personal or hard_anchors or companions or final_detections):
        storage_class = StorageClass.PD_BUT_JUSTIFIED_STORAGE
        primary_genre = _pick_primary_genre(genres, default="justified_public_doc")
    else:
        storage_class = StorageClass.NON_TARGET
        primary_genre = _pick_primary_genre(genres, default="noise")

    if company_export and storage_class == StorageClass.TARGET_LEAK and not hard_anchors and not special_or_biometric:
        storage_class = StorageClass.PD_BUT_JUSTIFIED_STORAGE if companions else StorageClass.NON_TARGET
        reasons.append("LEAK_CONTEXT_COMPANY_EXPORT_OVERRIDES")
        primary_genre = "company_export"

    if public_contact_doc or public_report:
        subject_linked_sensitive = counts.get("person_name", 0) > 0 and (
            special_or_biometric or bool(categories.intersection(PUBLIC_OVERRIDE_BLOCKERS))
        )
        blocking_public_override = subject_linked_sensitive or bool(
            genres.intersection(
                {
                    "personal_form",
                    "internal_employee_doc",
                    "correspondence",
                    "image_of_personal_doc",
                    "personal_export",
                }
            )
        )
        if storage_class == StorageClass.TARGET_LEAK and not blocking_public_override:
            storage_class = StorageClass.PD_BUT_JUSTIFIED_STORAGE
            reasons.append("LEAK_CONTEXT_PUBLIC_JUSTIFIED_OVERRIDES")
            primary_genre = "public_contact_doc" if public_contact_doc else "public_report"

    if is_template and storage_class != StorageClass.TARGET_LEAK:
        storage_class = StorageClass.NON_TARGET
        primary_genre = "blank_template"

    meaningful_signal = bool(final_detections) or (
        "personal_export" in genres and structured and (trusted_personal or hard_anchors or companions)
    )
    if storage_class == StorageClass.TARGET_LEAK and not meaningful_signal and "personal_export" not in genres:
        storage_class = StorageClass.NON_TARGET
        primary_genre = _pick_primary_genre(genres, default="noise")
        reasons.append("LEAK_CONTEXT_WEAK_TARGET_DOWNGRADED")

    return LeakContextAssessment(
        storage_class=storage_class,
        primary_genre=primary_genre,
        genre_tags=sorted(genres) if genres else [primary_genre],
        reasons=sorted(set(reasons)),
        risk_score=risk_score,
        justification_score=justification_score,
        noise_score=noise_score,
    )


def _looks_like_public_contact_doc(
    combined: str,
    counts: Counter[str],
    trusted_personal: bool,
    *,
    personal_form: bool,
) -> bool:
    if personal_form:
        return False

    contact_volume = counts.get("email", 0) + counts.get("phone", 0)
    literal_contact = "@" in combined or "телефон" in combined or "phone" in combined
    return (
        any(marker in combined for marker in JUSTIFIED_PUBLIC_MARKERS)
        and (contact_volume >= 1 or literal_contact)
        and (
            counts.get("person_name", 0) > 0
            or trusted_personal
            or counts.get("address", 0) > 0
            or "ответствен" in combined
            or "responsible" in combined
            or "directory" in combined
        )
    )


def _looks_like_public_report(combined: str, *, personal_form: bool) -> bool:
    if personal_form:
        return False
    return any(marker in combined for marker in PUBLIC_REPORT_MARKERS)


def _looks_like_org_requisites_doc(combined: str, counts: Counter[str]) -> bool:
    org_finance_categories = {"inn_legal_entity", "bank_account", "bik"}
    return any(marker in combined for marker in ORG_REQUISITE_MARKERS) or (
        bool(set(counts).intersection(org_finance_categories))
        and not set(counts).intersection(HARD_PERSONAL_CATEGORIES | {"person_name", "birth_date", "birth_place"})
    )


def _looks_like_personal_form(combined: str, *, is_template: bool) -> bool:
    if is_template:
        return False
    return any(marker in combined for marker in PERSONAL_FORM_MARKERS)


def _looks_like_internal_doc(combined: str) -> bool:
    return any(marker in combined for marker in INTERNAL_DOC_MARKERS)


def _looks_like_correspondence(combined: str) -> bool:
    return any(marker in combined for marker in CORRESPONDENCE_MARKERS)


def _looks_like_image_personal_doc(
    descriptor: FileDescriptor,
    combined: str,
    hard_anchors: bool,
    special_or_biometric: bool,
) -> bool:
    if descriptor.detected_format not in {FileFormat.IMAGE, FileFormat.PDF}:
        return False
    return hard_anchors or special_or_biometric or any(marker in combined for marker in IMAGE_DOC_MARKERS if marker not in {"scan", "скан"})


def _looks_like_personal_export(
    path_lower: str,
    header: list[str],
    combined: str,
    structured: bool,
    row_count: int,
    counts: Counter[str],
    hard_anchors: bool,
    companions: bool,
) -> bool:
    if not structured:
        return False
    header_hits = sum(1 for marker in PERSONAL_EXPORT_HEADER_MARKERS if any(marker in name for name in header))
    path_hits = sum(1 for marker in PERSONAL_EXPORT_PATH_MARKERS if marker in path_lower)
    if hard_anchors:
        return True
    if counts.get("person_name", 0) > 0 and (companions or header_hits >= 2):
        return True
    if row_count >= 50 and header_hits >= 2 and path_hits >= 1:
        return True
    if row_count >= 200 and ("customer_name" in " ".join(header) or "destination_address" in " ".join(header)):
        return True
    return False


def _looks_like_company_export(
    path_lower: str,
    header: list[str],
    combined: str,
    structured: bool,
    row_count: int,
    counts: Counter[str],
    hard_anchors: bool,
) -> bool:
    if not structured or hard_anchors:
        return False
    header_text = " ".join(header)
    marker_hits = sum(1 for marker in COMPANY_EXPORT_MARKERS if marker in header_text or marker in path_lower)
    org_name_hits = sum(1 for marker in ORG_SUFFIX_MARKERS if marker in combined)
    return (
        marker_hits >= 1
        and org_name_hits >= 1
        and counts.get("person_name", 0) == 0
        and (row_count >= 20 or bool(set(counts).intersection({"email", "phone", "address"})))
    )


def _has_personal_bundle(counts: Counter[str]) -> bool:
    categories = set(counts)
    if categories.intersection(HARD_PERSONAL_CATEGORIES) and categories.intersection(COMPANION_CATEGORIES):
        return True
    if "person_name" in categories and categories.intersection(COMPANION_CATEGORIES):
        return True
    return False


def _is_trusted_personal_detection(detection: DetectionResult) -> bool:
    if detection.family in {"government", "payment"} and detection.validation_status == ValidationStatus.VALID:
        return True
    return detection.category in {"person_name", "address", "birth_date", "birth_place"} and detection.confidence in {
        ConfidenceLevel.HIGH,
        ConfidenceLevel.MEDIUM,
    }


def _pick_primary_genre(genres: set[str], *, default: str) -> str:
    priority = (
        "personal_export",
        "image_of_personal_doc",
        "personal_form",
        "internal_employee_doc",
        "correspondence",
        "public_contact_doc",
        "public_report",
        "company_export",
        "org_requisites_doc",
        "blank_template",
    )
    for item in priority:
        if item in genres:
            return item
    return default
