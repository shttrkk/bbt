from __future__ import annotations

from pdn_scanner.config import load_config
from pdn_scanner.enums import ContentStatus, FileFormat, UZLevel
from pdn_scanner.models import ExtractedContent, FileDescriptor, FileScanResult
from pdn_scanner.submission import apply_cross_file_promotion


def _result(
    *,
    rel_path: str,
    file_format: FileFormat,
    assigned_uz: UZLevel,
    counts_by_category: dict[str, int],
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
        assigned_uz=assigned_uz,
        counts_by_category=counts_by_category,
        counts_by_family={"ordinary": sum(counts_by_category.values())} if counts_by_category else {},
        classification_reasons=["ORDINARY_LARGE_VOLUME"] if assigned_uz != UZLevel.NO_PDN else [],
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
