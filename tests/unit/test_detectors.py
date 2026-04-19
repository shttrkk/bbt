from pdn_scanner.config import load_config
from pdn_scanner.detectors.engine import DetectionEngine
from pdn_scanner.enums import ContentStatus
from pdn_scanner.models import ExtractedContent


def _engine() -> DetectionEngine:
    return DetectionEngine(load_config("configs/default.yaml"))


def test_phone_detector_rejects_timestamp_like_values() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="plan.json",
        status=ContentStatus.OK,
        text_chunks=["CreatedAt: 1606089600 | UpdatedAt: 1606867200 | Description: internet plan"],
    )

    detections = engine.detect(content)

    assert [item for item in detections if item.category == "phone"] == []


def test_payment_detector_rejects_identifier_numbers_without_card_context() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="incidents.json",
        status=ContentStatus.OK,
        text_chunks=["number: 1782113629924000856 | created: 2025-09-18T16:03:13+00:00"],
    )

    detections = engine.detect(content)

    assert [item for item in detections if item.category == "bank_card"] == []


def test_government_detector_rejects_invalid_inn_without_context() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="subscribers.csv",
        status=ContentStatus.OK,
        text_chunks=["IdClient: 24fadd55-526a-46a6-b994-3b4433777a11 | SomeNumber: 460211238537 | Status: ON"],
    )

    detections = engine.detect(content)

    assert [item for item in detections if item.category in {"inn_individual", "inn_legal_entity"}] == []


def test_person_name_detector_uses_customer_name_field_not_city() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="customers.csv",
        status=ContentStatus.OK,
        text_chunks=[
            "customer_id: 1 | customer_name: Филипп Елизарович Воробьев | customer_type: Физическое лицо | city: Нижний Новгород"
        ],
    )

    detections = engine.detect(content)
    names = [item.raw_value for item in detections if item.category == "person_name"]

    assert names == ["Филипп Елизарович Воробьев"]


def test_address_detector_uses_destination_address_field() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="logistics.csv",
        status=ContentStatus.OK,
        text_chunks=[
            "destination_address: г. Буденновск, бул. Ленинский, д. 3, 900842 | carrier: ЛогистикПро"
        ],
    )

    detections = engine.detect(content)
    addresses = [item.raw_value for item in detections if item.category == "address"]

    assert addresses == ["г. Буденновск, бул. Ленинский, д. 3, 900842"]


def test_government_detectors_classify_passport_and_inn_subtypes() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="person.txt",
        status=ContentStatus.OK,
        text_chunks=[
            "Паспорт РФ серия 4510 номер 123456 | ИНН: 500100732259 | ИНН организации: 7707083893"
        ],
    )

    detections = engine.detect(content)
    subtypes = {item.entity_subtype for item in detections}

    assert "passport_series" in subtypes
    assert "passport_number" in subtypes
    assert "passport_series_number" in subtypes
    assert "inn_individual" in subtypes
    assert "inn_legal_entity" in subtypes


def test_payment_detectors_classify_account_bik_and_cvv() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="bank.txt",
        status=ContentStatus.OK,
        text_chunks=[
            "Карта: 4111 1111 1111 1111 | CVV: 123 | расчетный счет: 40702810900000000001 | БИК: 044525225"
        ],
    )

    detections = engine.detect(content)
    subtypes = {item.entity_subtype for item in detections}

    assert "bank_card" in subtypes
    assert "cvv_cvc" in subtypes
    assert "bank_account" in subtypes
    assert "bik" in subtypes


def test_sensitive_detectors_classify_biometric_and_special_categories() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="sensitive.txt",
        status=ContentStatus.OK,
        text_chunks=[
            "Сотрудник. отпечатки пальцев: сданы | состояние здоровья: диабет | политические убеждения: не указаны"
        ],
    )

    detections = engine.detect(content)
    subtypes = {item.entity_subtype for item in detections}

    assert "fingerprints" in subtypes
    assert "health_data" in subtypes
    assert "political_beliefs" in subtypes


def test_person_name_detector_handles_multiline_label_with_org_header() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="pass.txt",
        status=ContentStatus.OK,
        text_chunks=[
            "Управляющая компания ЖК «Речной Квартал»\n"
            "Заказчик пропуска (житель):\n"
            "Чернов Максим Олегович\n"
            "адрес: 410047, г. Саратов, ул. Летняя Долина, д. 15"
        ],
    )

    detections = engine.detect(content)
    names = [item.raw_value for item in detections if item.category == "person_name"]

    assert "Чернов Максим Олегович" in names


def test_person_name_detector_handles_requester_field_in_service_export() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="ticket.txt",
        status=ContentStatus.OK,
        text_chunks=[
            "ServiceDesk Export\nRequester: Голубева Марина Юрьевна\nEmployee ID: 013905\nEmail: m.golubeva@corp-example.local"
        ],
    )

    detections = engine.detect(content)
    names = [item.raw_value for item in detections if item.category == "person_name"]

    assert names == ["Голубева Марина Юрьевна"]


def test_phone_detector_accepts_contact_number_context() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="delivery.txt",
        status=ContentStatus.OK,
        text_chunks=[
            "Получатель: Кулагин Антон Владиславович. Контактный номер для курьера: +7 (912) 604-77-42."
        ],
    )

    detections = engine.detect(content)
    phones = [item.raw_value for item in detections if item.category == "phone"]

    assert phones == ["+7 (912) 604-77-42"]
