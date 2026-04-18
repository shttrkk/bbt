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

    assert [item for item in detections if item.category == "inn"] == []


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
