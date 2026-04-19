from __future__ import annotations

from pdn_scanner.config import load_config
from pdn_scanner.enums import ConfidenceLevel, ContentStatus, FileFormat, StorageClass, UZLevel
from pdn_scanner.models import DetectionResult, ExtractedContent, FileDescriptor, FileScanResult
from pdn_scanner.submission import apply_cross_file_promotion


def _result(
    *,
    rel_path: str,
    file_format: FileFormat,
    assigned_uz: UZLevel,
    counts_by_category: dict[str, int],
    storage_class: StorageClass = StorageClass.TARGET_LEAK,
    detections: list[DetectionResult] | None = None,
) -> FileScanResult:
    return FileScanResult(
        file=FileDescriptor(
            path=rel_path,
            rel_path=rel_path,
            size_bytes=0,
            extension=f".{file_format.value}",
            detected_format=file_format,
        ),
        extraction=ExtractedContent(file_path=rel_path, status=ContentStatus.OK, text_chunks=[]),
        detections=detections or [],
        assigned_uz=assigned_uz,
        storage_class=storage_class,
        primary_genre="personal_export",
        genre_tags=["personal_export"],
        counts_by_category=counts_by_category,
        counts_by_family={"ordinary": sum(counts_by_category.values())} if counts_by_category else {},
        classification_reasons=["ORDINARY_LARGE_VOLUME"] if assigned_uz != UZLevel.NO_PDN else [],
    )


def _detection(category: str, *, value_hash: str | None = None) -> DetectionResult:
    return DetectionResult(
        category=category,
        family="ordinary",
        entity_category="ordinary",
        entity_subtype=category,
        detector_id=f"test.{category}",
        confidence=ConfidenceLevel.HIGH,
        value_hash=value_hash,
    )


def test_name_only_large_file_is_demoted_without_cross_file_pair() -> None:
    config = load_config("configs/default.yaml")
    results = [
        _result(
            rel_path="dataset/customers.csv",
            file_format=FileFormat.CSV,
            assigned_uz=UZLevel.UZ3,
            counts_by_category={"person_name": 1601},
        )
    ]

    adjusted = apply_cross_file_promotion(results, config)

    assert adjusted[0].assigned_uz == UZLevel.NO_PDN
    assert "WEAK_ORDINARY_ONLY" in adjusted[0].classification_reasons
    assert "CROSS_FILE_PERSON_ADDRESS_BUNDLE" not in adjusted[0].classification_reasons


def test_name_and_address_files_in_same_directory_are_promoted_together() -> None:
    config = load_config("configs/default.yaml")
    results = [
        _result(
            rel_path="dataset/customers.csv",
            file_format=FileFormat.CSV,
            assigned_uz=UZLevel.UZ3,
            counts_by_category={"person_name": 1601},
        ),
        _result(
            rel_path="dataset/logistics.csv",
            file_format=FileFormat.CSV,
            assigned_uz=UZLevel.UZ3,
            counts_by_category={"address": 1803},
        ),
    ]

    adjusted = apply_cross_file_promotion(results, config)

    assert adjusted[0].assigned_uz == UZLevel.UZ3
    assert adjusted[1].assigned_uz == UZLevel.UZ3
    assert "CROSS_FILE_PERSON_ADDRESS_BUNDLE" in adjusted[0].classification_reasons
    assert "CROSS_FILE_PERSON_ADDRESS_BUNDLE" in adjusted[1].classification_reasons


def test_cross_file_promotion_does_not_join_different_directories() -> None:
    config = load_config("configs/default.yaml")
    results = [
        _result(
            rel_path="dataset_a/customers.csv",
            file_format=FileFormat.CSV,
            assigned_uz=UZLevel.UZ3,
            counts_by_category={"person_name": 1601},
        ),
        _result(
            rel_path="dataset_b/logistics.csv",
            file_format=FileFormat.CSV,
            assigned_uz=UZLevel.UZ3,
            counts_by_category={"address": 1803},
        ),
    ]

    adjusted = apply_cross_file_promotion(results, config)

    assert adjusted[0].assigned_uz == UZLevel.NO_PDN
    assert adjusted[1].assigned_uz == UZLevel.NO_PDN
    assert "CROSS_FILE_PERSON_ADDRESS_BUNDLE" not in adjusted[0].classification_reasons
    assert "CROSS_FILE_PERSON_ADDRESS_BUNDLE" not in adjusted[1].classification_reasons


def test_shared_linkage_bundle_promotes_files_with_matching_hashes() -> None:
    config = load_config("configs/default.yaml")
    results = [
        _result(
            rel_path="bundle/person.txt",
            file_format=FileFormat.TXT,
            assigned_uz=UZLevel.NO_PDN,
            counts_by_category={"person_name": 1, "email": 1},
            detections=[
                _detection("person_name", value_hash="person-1"),
                _detection("email", value_hash="link-1"),
            ],
        ),
        _result(
            rel_path="bundle/contact.txt",
            file_format=FileFormat.TXT,
            assigned_uz=UZLevel.NO_PDN,
            counts_by_category={"address": 1, "email": 1},
            detections=[
                _detection("address"),
                _detection("email", value_hash="link-1"),
            ],
        ),
    ]

    adjusted = apply_cross_file_promotion(results, config)

    assert adjusted[0].assigned_uz == UZLevel.UZ4
    assert adjusted[1].assigned_uz == UZLevel.UZ4
    assert "CROSS_FILE_SHARED_LINKAGE_BUNDLE" in adjusted[0].classification_reasons
    assert "CROSS_FILE_SHARED_LINKAGE_BUNDLE" in adjusted[1].classification_reasons


def test_small_directory_bundle_promotes_weak_files_together() -> None:
    config = load_config("configs/default.yaml")
    results = [
        _result(
            rel_path="small_bundle/name.txt",
            file_format=FileFormat.TXT,
            assigned_uz=UZLevel.NO_PDN,
            counts_by_category={"person_name": 1},
            detections=[_detection("person_name")],
        ),
        _result(
            rel_path="small_bundle/phone.txt",
            file_format=FileFormat.TXT,
            assigned_uz=UZLevel.NO_PDN,
            counts_by_category={"phone": 1},
            detections=[_detection("phone")],
        ),
    ]

    adjusted = apply_cross_file_promotion(results, config)

    assert adjusted[0].assigned_uz == UZLevel.UZ4
    assert adjusted[1].assigned_uz == UZLevel.UZ4
    assert "CROSS_FILE_SMALL_DIRECTORY_BUNDLE" in adjusted[0].classification_reasons
    assert "CROSS_FILE_SMALL_DIRECTORY_BUNDLE" in adjusted[1].classification_reasons


def test_cross_file_does_not_promote_justified_storage() -> None:
    config = load_config("configs/default.yaml")
    results = [
        _result(
            rel_path="public_directory/unit_a.pdf",
            file_format=FileFormat.PDF,
            assigned_uz=UZLevel.NO_PDN,
            storage_class=StorageClass.PD_BUT_JUSTIFIED_STORAGE,
            counts_by_category={"person_name": 1, "phone": 1},
            detections=[_detection("person_name"), _detection("phone", value_hash="shared-1")],
        ),
        _result(
            rel_path="public_directory/unit_b.pdf",
            file_format=FileFormat.PDF,
            assigned_uz=UZLevel.NO_PDN,
            storage_class=StorageClass.PD_BUT_JUSTIFIED_STORAGE,
            counts_by_category={"email": 1},
            detections=[_detection("email", value_hash="shared-1")],
        ),
    ]

    adjusted = apply_cross_file_promotion(results, config)

    assert adjusted[0].assigned_uz == UZLevel.NO_PDN
    assert adjusted[1].assigned_uz == UZLevel.NO_PDN
    assert "CROSS_FILE_SHARED_LINKAGE_BUNDLE" not in adjusted[0].classification_reasons
