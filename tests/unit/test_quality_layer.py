from __future__ import annotations

from pdn_scanner.classify import UZClassifier
from pdn_scanner.config import load_config
from pdn_scanner.detectors.engine import DetectionEngine
from pdn_scanner.enums import ConfidenceLevel, ContentStatus, FileFormat, UZLevel
from pdn_scanner.models import ExtractedContent, FileDescriptor
from pdn_scanner.quality import QualityLayer


def _pipeline(
    *,
    rel_path: str,
    file_format: FileFormat,
    chunks: list[str],
    extractor: str,
    metadata: dict | None = None,
):
    config = load_config("configs/default.yaml")
    engine = DetectionEngine(config)
    quality_layer = QualityLayer(config)
    classifier = UZClassifier(config)

    descriptor = FileDescriptor(
        path=rel_path,
        rel_path=rel_path,
        size_bytes=0,
        extension=f".{file_format.value}",
        detected_format=file_format,
    )
    extraction = ExtractedContent(
        file_path=rel_path,
        status=ContentStatus.OK,
        text_chunks=chunks,
        metadata={"extractor": extractor, **(metadata or {})},
    )

    detections = engine.detect(extraction)
    quality = quality_layer.assess(descriptor, extraction, detections)
    assigned_uz, reasons, _ = classifier.classify(
        quality.detections,
        is_template=quality.is_template,
        is_public_doc=quality.is_public_doc,
        is_reference_data=quality.is_reference_data,
        quality_reasons=quality.reasons,
    )
    return detections, quality, assigned_uz, reasons


def test_template_document_is_suppressed_and_not_promoted() -> None:
    _, quality, assigned_uz, reasons = _pipeline(
        rel_path="forms/anketa.txt",
        file_format=FileFormat.TXT,
        extractor="txt",
        chunks=["ФИО: __________ Адрес: __________ Подпись: __________ Дата рождения: __________"],
    )

    assert quality.is_template is True
    assert quality.detections == []
    assert assigned_uz == UZLevel.NO_PDN
    assert "TEMPLATE_SUPPRESSED" in reasons


def test_public_policy_weak_signals_do_not_raise_risk() -> None:
    _, quality, assigned_uz, reasons = _pipeline(
        rel_path="sites/privacy_policy.html",
        file_format=FileFormat.HTML,
        extractor="html",
        chunks=[
            "Privacy policy and terms of service. Cookies. Обработка персональных данных. "
            "Contact email: privacy@example.com Телефон: +7 (495) 111-22-33"
        ],
    )

    assert quality.is_public_doc is True
    assert quality.detections == []
    assert assigned_uz == UZLevel.NO_PDN
    assert "PUBLIC_DOC_WEAK_SIGNALS_ONLY" in reasons


def test_reference_plan_json_stays_negative_even_with_id_like_valid_inn() -> None:
    _, quality, assigned_uz, reasons = _pipeline(
        rel_path="Billing/plan.json",
        file_format=FileFormat.JSON,
        extractor="json",
        chunks=["plan_id: 500100732259 | product_code: BASIC | service_name: Internet Max | status: active"],
    )

    assert quality.is_reference_data is True
    assert [item for item in quality.detections if item.category in {"inn_individual", "inn_legal_entity"}] == []
    assert assigned_uz == UZLevel.NO_PDN
    assert "REFERENCE_DATA_WEAK_SIGNALS_ONLY" in reasons


def test_incidents_json_noise_does_not_become_positive() -> None:
    _, quality, assigned_uz, _ = _pipeline(
        rel_path="Billing/incidents.json",
        file_format=FileFormat.JSON,
        extractor="json",
        chunks=[
            "incident_id: 500100732259 | number: 1782113629924000856 | "
            "created: 2025-09-18T16:03:13+00:00 | updated: 2025-09-18T17:04:13+00:00"
        ],
    )

    assert quality.is_reference_data is True
    assert quality.detections == []
    assert assigned_uz == UZLevel.NO_PDN


def test_html_noise_suppresses_token_like_phone_and_inn_hits() -> None:
    _, quality, assigned_uz, _ = _pipeline(
        rel_path="cache/page.html",
        file_format=FileFormat.HTML,
        extractor="html",
        chunks=[
            "window.__INITIAL_STATE__ token 550e8400-e29b-41d4-a716-446655440000 "
            "phone: +7 (495) 111-22-33 inn: 500100732259 gtag(function(){return true;})"
        ],
    )

    assert [item for item in quality.detections if item.category in {"phone", "inn_individual", "inn_legal_entity"}] == []
    assert assigned_uz == UZLevel.NO_PDN


def test_structured_birth_date_hint_increases_confidence() -> None:
    _, quality, _, _ = _pipeline(
        rel_path="customers.json",
        file_format=FileFormat.JSON,
        extractor="json",
        chunks=["customer_id: 42 | customer_name: Иванов Иван Иванович | date_of_birth: 01.02.2000"],
    )

    birth_dates = [item for item in quality.detections if item.category == "birth_date"]

    assert birth_dates
    assert birth_dates[0].confidence in {ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH}


def test_substring_false_positive_regressions_do_not_return_entities() -> None:
    _, quality, assigned_uz, _ = _pipeline(
        rel_path="notes.txt",
        file_format=FileFormat.TXT,
        extractor="txt",
        chunks=[
            "Отчество: Аркадьевич. Лицевой счет: 123456. Адрес доставки: город Радужный, квартал Северный.",
        ],
    )

    assert quality.detections == []
    assert assigned_uz == UZLevel.NO_PDN


def test_special_and_biometric_signals_raise_uz1() -> None:
    _, quality, assigned_uz, _ = _pipeline(
        rel_path="hr/profile.txt",
        file_format=FileFormat.TXT,
        extractor="txt",
        chunks=[
            "Сотрудник: Иванов Иван Иванович | отпечатки пальцев: сданы | состояние здоровья: хроническое заболевание"
        ],
    )

    assert any(item.family == "biometric" for item in quality.detections)
    assert any(item.family == "special" for item in quality.detections)
    assert assigned_uz == UZLevel.UZ1


def test_livejournal_public_page_health_noise_is_suppressed() -> None:
    _, quality, assigned_uz, _ = _pipeline(
        rel_path="sites/page_443.html",
        file_format=FileFormat.HTML,
        extractor="html",
        chunks=[
            "LiveJournal Top Main Top Interesting Follow us on Twitter Telegram comments tags "
            "НЕсахарный диабет - чаще исключаем, чем ставим такой диагноз."
        ],
    )

    assert quality.detections == []
    assert assigned_uz == UZLevel.NO_PDN


def test_livejournal_public_page_contact_email_is_suppressed() -> None:
    _, quality, assigned_uz, _ = _pipeline(
        rel_path="sites/page_436.html",
        file_format=FileFormat.HTML,
        extractor="html",
        chunks=[
            "LiveJournal Top Main Top Interesting Follow us on Twitter Telegram Applications iOS Android "
            "По вопросам рекламы обращаться: mail@smapse.com Или по номеру: 8-800-775-54-97"
        ],
    )

    assert quality.detections == []
    assert assigned_uz == UZLevel.NO_PDN


def test_livejournal_public_page_passport_story_is_suppressed() -> None:
    _, quality, assigned_uz, _ = _pipeline(
        rel_path="sites/page_456.html",
        file_format=FileFormat.HTML,
        extractor="html",
        chunks=[
            "LiveJournal Top Main Top Interesting Follow us on Twitter Telegram comments tags "
            "дата рождения: 01.02.2000 паспорт серии 45 10 № 123456 адрес: г. Москва, ул. Лесная, д. 1"
        ],
    )

    assert quality.detections == []
    assert assigned_uz == UZLevel.NO_PDN


def test_form_like_html_with_person_bundle_survives_selection() -> None:
    _, quality, assigned_uz, reasons = _pipeline(
        rel_path="profiles/employee_card.html",
        file_format=FileFormat.HTML,
        extractor="html",
        chunks=[
            "Employee profile ФИО: Иванов Иван Иванович Email: ivanov@example.com Телефон: +7 999 123-45-67"
        ],
    )

    categories = {item.category for item in quality.detections}
    assert {"person_name", "email", "phone"}.issubset(categories)
    assert assigned_uz == UZLevel.UZ4
    assert "HTML_STRONG_BUNDLE" in reasons


def test_declaration_like_xls_with_name_only_is_suppressed() -> None:
    _, quality, assigned_uz, reasons = _pipeline(
        rel_path="Прочее/Декларация 2016г Новошахтинск.xls",
        file_format=FileFormat.XLS,
        extractor="xls",
        chunks=[
            "sheet: Лист1 | ФИО: Пилипенко Лидия Ивановна | "
            "Объекты недвижимости, находящиеся в собственности / вид объекта: Жилой дом"
        ],
    )

    assert quality.detections == []
    assert assigned_uz == UZLevel.NO_PDN
    assert "XLS_DECLARATION_WEAK_BUNDLE" in reasons


def test_staff_contact_xls_with_name_phone_email_is_suppressed() -> None:
    _, quality, assigned_uz, reasons = _pipeline(
        rel_path="Прочее/sostav_gr.xls",
        file_format=FileFormat.XLS,
        extractor="xls",
        chunks=[
            "sheet: НИпроекты | ФИО: Шаханова Ангелина Владимировна | "
            "ВУЗ: Адыгейский государственный университет | Должность: Проректор по научной работе | "
            "email: nisadgu@yandex.ru | телефон: 8 918 420 10 21"
        ],
    )

    assert quality.detections == []
    assert assigned_uz == UZLevel.NO_PDN
    assert "XLS_PUBLIC_CONTACTS_WEAK_BUNDLE" in reasons


def test_person_bundle_xls_with_name_and_birth_date_survives_selection() -> None:
    _, quality, assigned_uz, reasons = _pipeline(
        rel_path="profiles/employees.xls",
        file_format=FileFormat.XLS,
        extractor="xls",
        chunks=[
            "sheet: Лист1 | ФИО: Иванов Иван Иванович | дата рождения: 01.02.2000 | должность: менеджер"
        ],
    )

    categories = {item.category for item in quality.detections}
    assert {"person_name", "birth_date"}.issubset(categories)
    assert assigned_uz == UZLevel.UZ4
    assert "XLS_STRONG_BUNDLE" in reasons


def test_docx_person_bundle_survives_shortlist_selection() -> None:
    _, quality, assigned_uz, reasons = _pipeline(
        rel_path="Прочее/Анкета кандидата.docx",
        file_format=FileFormat.DOCX,
        extractor="docx",
        chunks=[
            "ФИО: Иванов Иван Иванович",
            "Телефон: +7 999 123-45-67",
            "Email: ivanov@example.com",
        ],
    )

    categories = {item.category for item in quality.detections}
    assert {"person_name", "phone", "email"}.issubset(categories)
    assert assigned_uz == UZLevel.UZ4
    assert "DOCX_STRONG_BUNDLE" in reasons


def test_public_policy_docx_is_suppressed_by_shortlist() -> None:
    _, quality, assigned_uz, reasons = _pipeline(
        rel_path="Прочее/politika-obrabotki-dannyh-tassru.docx",
        file_format=FileFormat.DOCX,
        extractor="docx",
        chunks=[
            "Политика обработки персональных данных. Contact email: privacy@example.com Телефон: +7 495 111-22-33"
        ],
    )

    assert quality.detections == []
    assert assigned_uz == UZLevel.NO_PDN
    assert "DOCX_PUBLIC_OR_TEMPLATE_PATH" in reasons


def test_docx_org_contract_requisites_without_person_bundle_is_suppressed() -> None:
    _, quality, assigned_uz, reasons = _pipeline(
        rel_path="Прочее/Договор.docx",
        file_format=FileFormat.DOCX,
        extractor="docx",
        chunks=[
            "ДОГОВОР. ИНН: 6163027810 БИК: 046015602 расчетный счет: 40702810952090000494"
        ],
    )

    categories = {item.category for item in quality.detections}
    assert categories == set()
    assert assigned_uz == UZLevel.NO_PDN
    assert "DOCX_WEAK_SIGNALS_ONLY" in reasons
