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


def test_driver_license_detector_does_not_trigger_on_vuz_substring() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="rules.pdf",
        status=ContentStatus.OK,
        text_chunks=[
            "ФГБОУ ВО ВУЗ. ИНН: 7707083893. Настоящие правила приема опубликованы на сайте университета."
        ],
    )

    detections = engine.detect(content)

    assert [item for item in detections if item.category == "driver_license"] == []


def test_passport_detector_uses_local_context_not_distant_passport_word() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="info.pdf",
        status=ContentStatus.OK,
        text_chunks=[
            "Director: Varduni Tatiana Viktorovna. Tel. 89045016276. Development of genetic passports of wild crops."
        ],
    )

    detections = engine.detect(content)

    assert [item for item in detections if item.category == "passport_series_number"] == []


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


def test_english_personal_form_detects_name_address_and_international_phone() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="request.txt",
        status=ContentStatus.OK,
        text_chunks=[
            "Requester: John Michael Carter\n"
            "Phone: +1 (202) 555-0147\n"
            "Mailing Address: 221B Baker Street, Apt 5, London NW1 6XE"
        ],
    )

    detections = engine.detect(content)
    names = [item.raw_value for item in detections if item.category == "person_name"]
    phones = [item.raw_value for item in detections if item.category == "phone"]
    addresses = [item.raw_value for item in detections if item.category == "address"]

    assert names == ["John Michael Carter"]
    assert phones == ["+1 (202) 555-0147"]
    assert addresses == ["221B Baker Street, Apt 5, London NW1 6XE"]


def test_english_birth_place_detector_accepts_labeled_location() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="profile.txt",
        status=ContentStatus.OK,
        text_chunks=["Full Name: Alice Monroe\nPlace of Birth: New York, USA"],
    )

    detections = engine.detect(content)
    birth_places = [item.raw_value for item in detections if item.category == "birth_place"]

    assert birth_places == ["New York, USA"]


def test_english_split_name_fields_and_date_of_birth_are_detected() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="profile.txt",
        status=ContentStatus.OK,
        text_chunks=[
            "First Name: John\n"
            "Middle Name: Edward\n"
            "Last Name: Carter\n"
            "Date of Birth: 14-03-1988\n"
            "Residence Address: 77 King Street, Apt 12, Manchester M2 4WU\n"
            "Mobile Phone: +44 20 7946 0958"
        ],
    )

    detections = engine.detect(content)
    names = [item.raw_value for item in detections if item.category == "person_name"]
    birth_dates = [item.raw_value for item in detections if item.category == "birth_date"]
    addresses = [item.raw_value for item in detections if item.category == "address"]
    phones = [item.raw_value for item in detections if item.category == "phone"]

    assert names == ["John Edward Carter"]
    assert birth_dates == ["14-03-1988"]
    assert addresses == ["77 King Street, Apt 12, Manchester M2 4WU"]
    assert phones == ["+44 20 7946 0958"]


def test_passport_detector_accepts_passport_no_label() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="passport.txt",
        status=ContentStatus.OK,
        text_chunks=["Passport Series: 4510 | Passport No: 123456"],
    )

    detections = engine.detect(content)
    subtypes = {item.entity_subtype for item in detections}

    assert "passport_series" in subtypes
    assert "passport_number" in subtypes


def test_english_name_detector_rejects_company_name() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="vendor.txt",
        status=ContentStatus.OK,
        text_chunks=["Customer Name: Bright Future LLC | Address: 1200 Elm Street, Suite 400, Springfield, IL 62704"],
    )

    detections = engine.detect(content)

    assert [item for item in detections if item.category == "person_name"] == []


def test_address_detector_handles_multiline_labeled_value() -> None:
    engine = _engine()
    content = ExtractedContent(
        file_path="service.txt",
        status=ContentStatus.OK,
        text_chunks=[
            "ServiceDesk Export\n"
            "Requester: Голубева Марина Юрьевна\n"
            "Адрес выезда инженера:\n"
            "394026, г. Воронеж, ул. Школьная Гавань, д. 28, кв. 43\n"
            "Основной контакт: +7 920 455-61-27"
        ],
    )

    detections = engine.detect(content)
    addresses = [item.raw_value for item in detections if item.category == "address"]

    assert addresses == ["394026, г. Воронеж, ул. Школьная Гавань, д. 28, кв. 43"]
