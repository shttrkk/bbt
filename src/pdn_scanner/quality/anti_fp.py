from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import unquote

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ConfidenceLevel, FileFormat, ValidationStatus
from pdn_scanner.models import DetectionResult, ExtractedContent, FileDescriptor

from .html_noise import is_public_web_page, should_suppress_html_detection
from .public_docs import detect_public_doc
from .reference_data import detect_reference_data
from .templates import detect_template_like

PERSON_NAME_SCHEMA_HINTS = (
    "customer_name",
    "customer name",
    "person_name",
    "employee",
    "employee_name",
    "employee name",
    "fio",
    "фио",
    "full_name",
    "full name",
    "first_name",
    "first name",
    "last_name",
    "last name",
    "middle_name",
    "middle name",
    "middle initial",
    "given name",
    "forename",
    "surname",
    "family name",
    "requester",
    "requestor",
    "applicant",
    "recipient",
    "contact person",
)

STRONG_SCHEMA_HINTS = {
    "person_name": PERSON_NAME_SCHEMA_HINTS,
    "address": (
        "destination_address",
        "address",
        "registered_address",
        "delivery_address",
        "mailing address",
        "home address",
        "residential address",
        "residence address",
        "permanent address",
        "street address",
        "address line",
        "адрес",
    ),
    "phone": ("phone", "phone number", "telephone", "mobile", "mobile phone", "contact_phone", "contact number", "телефон", "тел"),
    "email": ("email", "e-mail", "почта"),
    "snils": ("snils", "снилс"),
    "inn_individual": ("inn", "инн"),
    "inn_legal_entity": ("inn", "инн"),
    "birth_date": ("birth", "birth date", "date of birth", "birth_date", "date_of_birth", "dob", "дата рождения"),
    "birth_place": ("birth_place", "birthplace", "place_of_birth", "place of birth", "city of birth", "country of birth", "место рождения"),
    "bank_card": ("card", "pan", "номер карты", "банковская карта"),
    "bank_account": ("account", "счет", "счёт", "расчетный счет"),
    "bik": ("bik", "бик"),
}
ID_HEAVY_FIELD_MARKERS = (
    "id",
    "_id",
    "uuid",
    "guid",
    "token",
    "hash",
    "checksum",
    "incident",
    "status",
    "created",
    "updated",
    "timestamp",
    "plan",
    "product",
    "catalog",
    "code",
    "key",
)
PUBLIC_CONTACT_CATEGORIES = {"email", "phone"}
XLS_DECLARATION_MARKERS = (
    "декларац",
    "сведения о доход",
    "декларацион",
    "объекты недвижимости",
    "вид объекта",
    "несовершеннолетний ребенок",
    "супруг",
    "на сайт",
)
XLS_ORG_CONTACT_MARKERS = (
    "университет",
    "академия",
    "должность",
    "проректор",
    "начальник",
    "управлен",
    "библиотек",
    "международным связям",
    "научной работе",
)
DOCX_SHORTLIST_MARKERS = (
    "анкет",
    "anketa",
    "заявлен",
    "zayav",
    "соглас",
    "sogl",
    "договор",
    "dogovor",
    "доверен",
    "doverenn",
    "регистрац",
    "registration",
    "воинск",
    "паспорт",
    "snils",
    "снилс",
    "инн",
    "dms",
    "учет",
    "учёт",
)
DOCX_EXCLUDE_MARKERS = (
    "шаблон",
    "template",
    "форма",
    "образец",
    "policy",
    "politika",
    "cookies",
    "инструкц",
    "instruction",
    "syllabus",
    "course",
    "гост",
    "gost",
    "приказ",
    "порядок",
    "перечень",
    "программа",
    "program",
    "семинар",
    "список",
    "spisok",
    "finalist",
    "research",
    "environmental",
    "water quality",
    "oil pollution",
    "congreso",
    "horario",
    "wiley",
)
DOCX_SITE_MARKERS = ("выгрузки/сайты", "sites", "доки")
PERSONAL_STANDALONE_STRONG_CATEGORIES = {
    "passport_series_number",
    "snils",
    "driver_license",
    "mrz",
    "bank_card",
}
PERSONAL_ANCHOR_CATEGORIES = {
    "person_name",
    "passport_series",
    "passport_number",
    "passport_series_number",
    "snils",
    "inn_individual",
    "driver_license",
    "mrz",
    "bank_card",
}
PERSONAL_COMPANION_CATEGORIES = {"address", "phone", "email", "birth_date", "birth_place"}
IMAGE_PUBLIC_MARKERS = (
    "curriculum vitae",
    "certificate of insurance",
    "curriculum",
    "resume",
    "cv",
    "university of",
    "medical center",
)
PDF_PUBLIC_SOURCE_MARKERS = (
    "выгрузки/сайты/доки",
    "документы партнеров",
)
PDF_PUBLIC_MARKERS = (
    "privacy",
    "policy",
    "terms",
    "cookies",
    "agreement",
    "processing",
    "report",
    "progress report",
    "feedback analysis",
    "information",
    "brochure",
    "article",
    "news",
    "mediakit",
    "price-list",
    "presentation",
    "outlook",
    "disclosure",
    "description",
    "profile",
    "admission",
    "protocol",
    "registry",
    "extract",
    "register",
    "plan",
    "public report",
    "публич",
    "информация",
    "политика",
    "правила",
    "правила приема",
    "соглашение",
    "обработк",
    "kişisel veri",
    "aydınlatma metni",
    "kvkk",
    "отчет",
    "отчёт",
    "рапорт",
    "протокол",
    "реестр",
    "реестров",
    "выписка",
    "самообслед",
    "медиакит",
    "координаты для связи",
    "программа",
    "положение",
    "приказ",
    "инструкция",
    "заработной плат",
    "среднемесячн",
    "главных бухгалтер",
    "руководителей",
    "лиценз",
    "аккредит",
    "license",
    "accreditation",
    "neutrality",
    "treaty",
    "pravila",
    "priema",
    "otchet",
    "raport",
    "samoobsled",
)
PDF_OFFICIAL_MARKERS = (
    "министерство",
    "университет",
    "академия",
    "комитет",
    "комисси",
    "федеральное государственное",
    "министерство образования",
    "minister",
    "ministry",
    "university",
    "academy",
    "committee",
    "agency",
    "rector",
    "ректор",
)
PDF_ORG_CONTACT_MARKERS = (
    "контакты",
    "контактная информация",
    "координаты для связи",
    "contact us",
    "info@",
    "support@",
    "sales@",
    "hr@",
    "pr@",
    "press@",
    "marketing@",
    "university",
    "университет",
    "академия",
    "рбк",
)
PDF_NARRATIVE_ONLY_CATEGORIES = {
    "health_data",
    "religious_beliefs",
    "political_beliefs",
    "race_data",
    "nationality_data",
    "special_category_other",
    "email",
    "phone",
    "address",
    "bank_account",
    "bik",
    "inn_legal_entity",
}
PDF_STANDALONE_HARD_ANCHORS = {"snils", "mrz"}
PDF_LINKABLE_ANCHORS = {
    "person_name",
    "passport_series",
    "passport_number",
    "passport_series_number",
    "snils",
    "inn_individual",
    "mrz",
}


@dataclass(slots=True)
class QualityAssessment:
    detections: list[DetectionResult]
    reasons: list[str] = field(default_factory=list)
    is_template: bool = False
    is_public_doc: bool = False
    is_reference_data: bool = False
    validated_entities_count: int = 0
    suspicious_entities_count: int = 0
    confidence_summary: dict[str, int] = field(default_factory=dict)


class QualityLayer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def assess(
        self,
        descriptor: FileDescriptor,
        extraction: ExtractedContent,
        detections: list[DetectionResult],
    ) -> QualityAssessment:
        adjusted: list[DetectionResult] = []
        reasons: list[str] = []

        for detection in detections:
            updated_detection, suppression_reasons = self._adjust_detection(descriptor, extraction, detection)
            if updated_detection is None:
                reasons.extend(suppression_reasons)
                continue
            adjusted.append(updated_detection)

        sample_text = " ".join(extraction.text_chunks[:20])
        is_template, template_reasons = (False, [])
        if self.config.feature_flags.enable_template_heuristics:
            is_template, template_reasons = detect_template_like(sample_text, adjusted)
        is_public_doc, public_reasons = detect_public_doc(descriptor.rel_path, sample_text, adjusted)
        is_reference_data, reference_reasons = detect_reference_data(descriptor, extraction, adjusted)

        reasons.extend(template_reasons)
        reasons.extend(public_reasons)
        reasons.extend(reference_reasons)

        adjusted, html_reasons = self._apply_html_selection(descriptor, sample_text, adjusted)
        reasons.extend(html_reasons)
        adjusted, xls_reasons = self._apply_xls_selection(descriptor, sample_text, adjusted)
        reasons.extend(xls_reasons)
        adjusted, docx_reasons = self._apply_docx_selection(descriptor, sample_text, adjusted)
        reasons.extend(docx_reasons)
        adjusted, office_reasons = self._apply_office_selection(descriptor, sample_text, adjusted)
        reasons.extend(office_reasons)
        adjusted, pdf_reasons = self._apply_pdf_selection(descriptor, sample_text, adjusted)
        reasons.extend(pdf_reasons)
        adjusted, image_reasons = self._apply_image_selection(descriptor, sample_text, adjusted)
        reasons.extend(image_reasons)

        adjusted = self._apply_file_level_suppression(
            adjusted,
            is_template=is_template,
            is_public_doc=is_public_doc,
            is_reference_data=is_reference_data,
        )

        return QualityAssessment(
            detections=adjusted,
            reasons=sorted(set(reasons)),
            is_template=is_template,
            is_public_doc=is_public_doc,
            is_reference_data=is_reference_data,
            validated_entities_count=self._validated_entities_count(adjusted),
            suspicious_entities_count=self._suspicious_entities_count(adjusted),
            confidence_summary=self._confidence_summary(adjusted),
        )

    def _adjust_detection(
        self,
        descriptor: FileDescriptor,
        extraction: ExtractedContent,
        detection: DetectionResult,
    ) -> tuple[DetectionResult | None, list[str]]:
        chunk = self._resolve_chunk(extraction, detection)
        chunk_lower = chunk.lower()
        extractor_name = str(extraction.metadata.get("extractor", "")).lower()
        is_structured = extractor_name in {"csv", "json", "parquet"}
        reasons: list[str] = []

        if descriptor.detected_format == FileFormat.HTML and should_suppress_html_detection(detection, chunk):
            return None, [f"SUPPRESSED_HTML_NOISE:{detection.category}"]

        if detection.category == "person_name" and self._looks_like_non_personal_name(chunk, detection):
            return None, ["SUPPRESSED_NON_PERSON_NAME"]

        if detection.category == "birth_date" and not self._has_birth_context(chunk_lower):
            return None, ["SUPPRESSED_BIRTH_DATE_NO_CONTEXT"]

        if is_structured and self._should_suppress_structured_noise(detection, chunk_lower):
            return None, [f"SUPPRESSED_STRUCTURED_NOISE:{detection.category}"]

        if is_structured:
            detection = self._boost_confidence_from_schema(detection, chunk_lower)

        return detection, reasons

    def _apply_file_level_suppression(
        self,
        detections: list[DetectionResult],
        *,
        is_template: bool,
        is_public_doc: bool,
        is_reference_data: bool,
    ) -> list[DetectionResult]:
        if is_template and not any(self._is_trusted_detection(detection) for detection in detections):
            return []

        if is_public_doc and not any(self._is_subject_signal(detection) for detection in detections):
            return [detection for detection in detections if detection.category not in PUBLIC_CONTACT_CATEGORIES]

        if is_reference_data and not any(self._is_trusted_detection(detection) for detection in detections):
            return []

        return detections

    def _apply_html_selection(
        self,
        descriptor: FileDescriptor,
        sample_text: str,
        detections: list[DetectionResult],
    ) -> tuple[list[DetectionResult], list[str]]:
        if descriptor.detected_format != FileFormat.HTML:
            return detections, []

        if not detections:
            return detections, []

        public_web = is_public_web_page(sample_text)
        if self._has_strong_html_bundle(detections, sample_text, public_web=public_web):
            return detections, ["HTML_STRONG_BUNDLE"]

        if public_web:
            return [], ["HTML_PUBLIC_WEB_NO_STRONG_BUNDLE"]

        if self._has_only_generic_html_signals(detections):
            return [], ["HTML_WEAK_SIGNALS_ONLY"]

        return detections, []

    def _has_strong_html_bundle(
        self,
        detections: list[DetectionResult],
        sample_text: str,
        *,
        public_web: bool,
    ) -> bool:
        ordinary = self._ordinary_categories(detections)
        strong_contacts = ordinary.intersection(PERSONAL_COMPANION_CATEGORIES)
        anchors = self._personal_anchor_categories(detections)
        standalone_strong = anchors.intersection(PERSONAL_STANDALONE_STRONG_CATEGORIES)
        person_name_hits = sum(
            detection.occurrences
            for detection in detections
            if detection.category == "person_name" and detection.confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM}
        )
        subject_markers = (
            "фио",
            "full name",
            "employee",
            "staff",
            "profile",
            "contact",
            "контакт",
            "phone",
            "email",
            "адрес",
            "passport",
            "паспорт",
            "snils",
            "снилс",
            "inn",
            "инн",
        )
        has_subject_context = any(marker in sample_text.lower() for marker in subject_markers)

        if not public_web and standalone_strong and has_subject_context:
            return True

        if not public_web and anchors.intersection(PERSONAL_ANCHOR_CATEGORIES) and strong_contacts:
            return True

        if person_name_hits >= 2 and strong_contacts:
            return True

        if not public_web and len(strong_contacts) >= 2 and has_subject_context:
            return True

        return False

    def _has_only_generic_html_signals(self, detections: list[DetectionResult]) -> bool:
        generic = {
            "health_data",
            "religious_beliefs",
            "political_beliefs",
            "race_data",
            "nationality_data",
            "special_category_other",
            "address",
            "email",
        }
        return all(detection.category in generic for detection in detections)

    def _apply_xls_selection(
        self,
        descriptor: FileDescriptor,
        sample_text: str,
        detections: list[DetectionResult],
    ) -> tuple[list[DetectionResult], list[str]]:
        if descriptor.detected_format != FileFormat.XLS:
            return detections, []

        if not detections:
            return detections, []

        combined = f"{descriptor.rel_path}\n{sample_text}".lower()
        anchors = self._personal_anchor_categories(detections)

        if self._looks_like_org_contact_xls(combined, detections) and (
            anchors.issubset({"person_name"}) or self._is_mass_org_contact_xls(detections)
        ):
            return [], ["XLS_PUBLIC_CONTACTS_WEAK_BUNDLE"]

        if self._has_strong_xls_bundle(detections):
            return detections, ["XLS_STRONG_BUNDLE"]

        if any(marker in combined for marker in XLS_DECLARATION_MARKERS):
            return [], ["XLS_DECLARATION_WEAK_BUNDLE"]

        if self._has_only_name_or_contact_xls_signals(detections):
            return [], ["XLS_WEAK_SIGNALS_ONLY"]

        return detections, []

    def _has_strong_xls_bundle(self, detections: list[DetectionResult]) -> bool:
        anchors = self._personal_anchor_categories(detections)
        companions = self._ordinary_categories(detections).intersection(PERSONAL_COMPANION_CATEGORIES)

        if anchors.intersection(PERSONAL_STANDALONE_STRONG_CATEGORIES):
            return True

        if anchors and companions:
            return True

        return False

    def _looks_like_org_contact_xls(self, combined: str, detections: list[DetectionResult]) -> bool:
        categories = {detection.category for detection in detections}
        has_contact_mix = bool(categories.intersection({"email", "phone"})) and "person_name" in categories
        return has_contact_mix and any(marker in combined for marker in XLS_ORG_CONTACT_MARKERS)

    def _is_mass_org_contact_xls(self, detections: list[DetectionResult]) -> bool:
        counts = Counter()
        for detection in detections:
            counts[detection.category] += detection.occurrences

        contact_volume = counts["email"] + counts["phone"] + counts["person_name"]
        high_trust_personal = {
            "passport_series",
            "passport_number",
            "passport_series_number",
            "snils",
            "mrz",
            "bank_card",
            "birth_date",
            "birth_place",
            "address",
        }
        return contact_volume >= 10 and not any(counts[category] > 0 for category in high_trust_personal)

    def _has_only_name_or_contact_xls_signals(self, detections: list[DetectionResult]) -> bool:
        weak_categories = {"person_name", "email", "phone"}
        return all(detection.category in weak_categories for detection in detections)

    def _apply_docx_selection(
        self,
        descriptor: FileDescriptor,
        sample_text: str,
        detections: list[DetectionResult],
    ) -> tuple[list[DetectionResult], list[str]]:
        if descriptor.detected_format != FileFormat.DOCX:
            return detections, []

        if not detections:
            return detections, []

        decoded_path = unquote(descriptor.rel_path).lower()
        combined = f"{decoded_path}\n{sample_text.lower()}"

        if self._has_strong_docx_bundle(detections):
            return detections, ["DOCX_STRONG_BUNDLE"]

        if any(marker in decoded_path for marker in DOCX_SITE_MARKERS):
            return [], ["DOCX_SITE_PUBLIC_PATH"]

        if any(marker in decoded_path for marker in DOCX_EXCLUDE_MARKERS):
            return [], ["DOCX_PUBLIC_OR_TEMPLATE_PATH"]

        if not any(marker in decoded_path for marker in DOCX_SHORTLIST_MARKERS):
            return [], ["DOCX_PATH_NOT_SHORTLISTED"]

        if self._has_only_name_or_contact_docx_signals(detections):
            return [], ["DOCX_WEAK_SIGNALS_ONLY"]

        return [], ["DOCX_NO_STRONG_BUNDLE"]

    def _apply_pdf_selection(
        self,
        descriptor: FileDescriptor,
        sample_text: str,
        detections: list[DetectionResult],
    ) -> tuple[list[DetectionResult], list[str]]:
        if descriptor.detected_format != FileFormat.PDF:
            return detections, []

        if not detections:
            return detections, []

        decoded_path = unquote(descriptor.rel_path).lower()
        combined = f"{decoded_path}\n{sample_text.lower()}"

        if any(marker in decoded_path for marker in PDF_PUBLIC_SOURCE_MARKERS):
            return [], ["PDF_PUBLIC_SOURCE"]

        if self._looks_like_public_or_official_pdf(combined):
            return [], ["PDF_PUBLIC_LEGAL_OR_REPORT"]

        if self._looks_like_org_contact_pdf(combined, detections):
            return [], ["PDF_ORG_CONTACT_ONLY"]

        if self._looks_like_mass_registry_pdf(combined, detections):
            return [], ["PDF_PUBLIC_REGISTRY_OR_PROTOCOL"]

        if self._has_only_weak_pdf_signals(detections):
            return [], ["PDF_WEAK_SIGNALS_ONLY"]

        if self._has_narrative_only_pdf_signals(detections):
            return [], ["PDF_NARRATIVE_NO_PERSON_LINKAGE"]

        if self._has_strong_pdf_bundle(detections):
            return detections, ["PDF_STRONG_BUNDLE"]

        return [], ["PDF_NO_STRONG_BUNDLE"]

    def _apply_office_selection(
        self,
        descriptor: FileDescriptor,
        sample_text: str,
        detections: list[DetectionResult],
    ) -> tuple[list[DetectionResult], list[str]]:
        if descriptor.detected_format not in {FileFormat.RTF, FileFormat.DOC}:
            return detections, []

        if not detections:
            return detections, []

        decoded_path = unquote(descriptor.rel_path).lower()
        combined = f"{decoded_path}\n{sample_text.lower()}"

        if self._has_strong_docx_bundle(detections):
            return detections, ["OFFICE_STRONG_BUNDLE"]

        if any(marker in decoded_path for marker in DOCX_SITE_MARKERS):
            return [], ["OFFICE_SITE_PUBLIC_PATH"]

        if any(marker in decoded_path for marker in DOCX_EXCLUDE_MARKERS):
            return [], ["OFFICE_PUBLIC_OR_TEMPLATE_PATH"]

        if not any(marker in decoded_path for marker in DOCX_SHORTLIST_MARKERS):
            return [], ["OFFICE_PATH_NOT_SHORTLISTED"]

        if self._has_only_name_or_contact_docx_signals(detections):
            return [], ["OFFICE_WEAK_SIGNALS_ONLY"]

        if self._looks_like_public_or_official_pdf(combined):
            return [], ["OFFICE_PUBLIC_OR_TEMPLATE_PATH"]

        return [], ["OFFICE_NO_STRONG_BUNDLE"]

    def _has_strong_docx_bundle(self, detections: list[DetectionResult]) -> bool:
        ordinary = self._ordinary_categories(detections)
        anchors = self._personal_anchor_categories(detections)

        if any(detection.family in {"special", "biometric"} for detection in detections):
            return True

        if anchors.intersection(PERSONAL_STANDALONE_STRONG_CATEGORIES):
            return True

        if anchors and ordinary.intersection(PERSONAL_COMPANION_CATEGORIES):
            return True

        return False

    def _has_only_name_or_contact_docx_signals(self, detections: list[DetectionResult]) -> bool:
        weak_categories = {"person_name", "email", "phone", "address", "bank_account", "bik", "inn_legal_entity"}
        return all(detection.category in weak_categories for detection in detections)

    def _has_strong_pdf_bundle(self, detections: list[DetectionResult]) -> bool:
        ordinary = self._ordinary_categories(detections)
        anchors = self._personal_anchor_categories(detections).intersection(PDF_LINKABLE_ANCHORS)
        companions = ordinary.intersection(PERSONAL_COMPANION_CATEGORIES)

        if any(detection.family in {"special", "biometric"} for detection in detections) and anchors:
            return True

        if anchors.intersection(PDF_STANDALONE_HARD_ANCHORS):
            return True

        if anchors and companions:
            return True

        return False

    def _apply_image_selection(
        self,
        descriptor: FileDescriptor,
        sample_text: str,
        detections: list[DetectionResult],
    ) -> tuple[list[DetectionResult], list[str]]:
        if descriptor.detected_format != FileFormat.IMAGE:
            return detections, []

        if not detections:
            return detections, []

        combined = f"{descriptor.rel_path}\n{sample_text.lower()}"
        if self._looks_like_public_image_doc(combined) and not self._has_strong_image_bundle(detections):
            return [], ["IMAGE_PUBLIC_DOC_NO_STRONG_BUNDLE"]

        if self._has_strong_image_bundle(detections):
            return detections, ["IMAGE_STRONG_BUNDLE"]

        if self._has_only_weak_image_signals(detections):
            return [], ["IMAGE_WEAK_SIGNALS_ONLY"]

        return [], ["IMAGE_NO_STRONG_BUNDLE"]

    def _looks_like_public_image_doc(self, combined: str) -> bool:
        return any(marker in combined for marker in IMAGE_PUBLIC_MARKERS) or self._looks_like_public_or_official_pdf(combined)

    def _has_strong_image_bundle(self, detections: list[DetectionResult]) -> bool:
        ordinary = self._ordinary_categories(detections)
        anchors = self._personal_anchor_categories(detections)

        if any(detection.family in {"special", "biometric"} for detection in detections) and anchors:
            return True

        if anchors.intersection(PDF_STANDALONE_HARD_ANCHORS.union({"passport_series_number", "bank_card"})):
            return True

        if anchors and ordinary.intersection(PERSONAL_COMPANION_CATEGORIES):
            return True

        return False

    def _has_only_weak_image_signals(self, detections: list[DetectionResult]) -> bool:
        weak_categories = {"email", "phone", "address", "inn_legal_entity", "person_name"}
        return all(detection.category in weak_categories for detection in detections)

    def _looks_like_public_or_official_pdf(self, combined: str) -> bool:
        public_hits = sum(1 for marker in PDF_PUBLIC_MARKERS if marker in combined)
        official_hits = sum(1 for marker in PDF_OFFICIAL_MARKERS if marker in combined)
        return public_hits >= 2 or (public_hits >= 1 and official_hits >= 1)

    def _looks_like_org_contact_pdf(self, combined: str, detections: list[DetectionResult]) -> bool:
        categories = {detection.category for detection in detections}
        weak_contact_mix = categories.intersection({"email", "phone", "address"}) and not self._personal_anchor_categories(detections)
        return bool(weak_contact_mix) and any(marker in combined for marker in PDF_ORG_CONTACT_MARKERS)

    def _looks_like_mass_registry_pdf(self, combined: str, detections: list[DetectionResult]) -> bool:
        categories = {detection.category for detection in detections}
        has_registry_shape = any(marker in combined for marker in ("протокол", "реестр", "реестров", "выписка", "registry", "extract"))
        has_mass_identifier_only = (
            categories.intersection({"snils", "passport_series_number", "inn_individual"})
            and not categories.intersection({"person_name", "birth_date", "birth_place"})
        )
        return has_registry_shape and has_mass_identifier_only

    def _has_only_weak_pdf_signals(self, detections: list[DetectionResult]) -> bool:
        weak_categories = {"email", "phone", "address", "bank_account", "bik", "inn_legal_entity"}
        return all(detection.category in weak_categories for detection in detections)

    def _has_narrative_only_pdf_signals(self, detections: list[DetectionResult]) -> bool:
        categories = {detection.category for detection in detections}
        return categories.issubset(PDF_NARRATIVE_ONLY_CATEGORIES)

    def _ordinary_categories(self, detections: list[DetectionResult]) -> set[str]:
        return {
            detection.category
            for detection in detections
            if detection.family == "ordinary" and detection.confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM}
        }

    def _personal_anchor_categories(self, detections: list[DetectionResult]) -> set[str]:
        anchors: set[str] = set()
        for detection in detections:
            if detection.category == "person_name" and detection.confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM}:
                anchors.add(detection.category)
                continue
            if detection.category not in PERSONAL_ANCHOR_CATEGORIES:
                continue
            if detection.family == "government" and detection.validation_status == ValidationStatus.INVALID:
                continue
            if detection.family == "payment" and detection.validation_status != ValidationStatus.VALID:
                continue
            anchors.add(detection.category)
        return anchors

    def _boost_confidence_from_schema(self, detection: DetectionResult, chunk_lower: str) -> DetectionResult:
        hints = STRONG_SCHEMA_HINTS.get(detection.category, ())
        if not any(hint in chunk_lower for hint in hints):
            return detection

        new_confidence = detection.confidence
        if detection.confidence == ConfidenceLevel.LOW:
            new_confidence = ConfidenceLevel.MEDIUM
        elif detection.confidence == ConfidenceLevel.MEDIUM and detection.validation_status == ValidationStatus.VALID:
            new_confidence = ConfidenceLevel.HIGH

        if new_confidence == detection.confidence:
            return detection

        return detection.model_copy(update={"confidence": new_confidence})

    def _should_suppress_structured_noise(self, detection: DetectionResult, chunk_lower: str) -> bool:
        hints = STRONG_SCHEMA_HINTS.get(detection.category, ())
        if any(hint in chunk_lower for hint in hints):
            return False

        id_heavy = sum(1 for marker in ID_HEAVY_FIELD_MARKERS if marker in chunk_lower)
        if detection.category in {"inn_individual", "inn_legal_entity", "snils", "bank_card", "phone"} and id_heavy >= 2:
            return True

        if detection.category == "birth_date" and not any(hint in chunk_lower for hint in STRONG_SCHEMA_HINTS["birth_date"]):
            return True

        if detection.category == "person_name" and "name:" in chunk_lower and not any(
            hint in chunk_lower for hint in PERSON_NAME_SCHEMA_HINTS + ("person",)
        ):
            return True

        return False

    def _looks_like_non_personal_name(self, chunk: str, detection: DetectionResult) -> bool:
        lowered = chunk.lower()
        raw_value = (detection.raw_value or "").lower()
        if "живого журнала" in raw_value:
            return True
        if any(marker in lowered for marker in ("privacy", "rules", "policy", "cookies", "journal")) and not any(
            hint in lowered for hint in PERSON_NAME_SCHEMA_HINTS
        ):
            return True
        return False

    def _has_birth_context(self, chunk_lower: str) -> bool:
        return any(marker in chunk_lower for marker in STRONG_SCHEMA_HINTS["birth_date"])

    def _resolve_chunk(self, extraction: ExtractedContent, detection: DetectionResult) -> str:
        for hint in detection.location_hints:
            if not hint.startswith("chunk:"):
                continue
            match = re.match(r"chunk:(\d+)", hint)
            if not match:
                continue
            index = int(match.group(1))
            if 0 <= index < len(extraction.text_chunks):
                return extraction.text_chunks[index]
        return ""

    def _validated_entities_count(self, detections: list[DetectionResult]) -> int:
        count = 0
        for detection in detections:
            if detection.validation_status == ValidationStatus.VALID:
                count += detection.occurrences
        return count

    def _suspicious_entities_count(self, detections: list[DetectionResult]) -> int:
        count = 0
        for detection in detections:
            if detection.validation_status == ValidationStatus.INVALID or detection.confidence == ConfidenceLevel.LOW:
                count += detection.occurrences
        return count

    def _confidence_summary(self, detections: list[DetectionResult]) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for detection in detections:
            counter[detection.confidence.value] += detection.occurrences
        return dict(counter)

    def _is_subject_signal(self, detection: DetectionResult) -> bool:
        return detection.category in {"person_name", "address", "birth_date", "birth_place"} and detection.confidence in {
            ConfidenceLevel.HIGH,
            ConfidenceLevel.MEDIUM,
        }

    def _is_trusted_detection(self, detection: DetectionResult) -> bool:
        if detection.family in {"government", "payment"} and detection.validation_status == ValidationStatus.VALID:
            return True
        return detection.confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM} and detection.category in {
            "person_name",
            "address",
            "birth_date",
            "birth_place",
        }
