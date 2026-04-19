from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import FileFormat, UZLevel
from pdn_scanner.models import FileScanResult

STRUCTURED_CORRELATION_FORMATS = {FileFormat.CSV, FileFormat.JSON, FileFormat.PARQUET, FileFormat.XLS}
WEAK_ORDINARY_ONLY_CATEGORIES = {frozenset({"person_name"}), frozenset({"address"})}


def apply_cross_file_promotion(results: list[FileScanResult], config: AppConfig) -> list[FileScanResult]:
    adjusted = [_demote_weak_ordinary_only(result) for result in results]
    grouped: dict[str, list[tuple[int, FileScanResult]]] = defaultdict(list)

    for index, result in enumerate(adjusted):
        if result.file.detected_format not in STRUCTURED_CORRELATION_FORMATS:
            continue
        grouped[str(Path(result.file.rel_path).parent)].append((index, result))

    for directory_results in grouped.values():
        name_candidates = [
            index
            for index, result in directory_results
            if _is_large_weak_candidate(result, target_category="person_name", config=config)
        ]
        address_candidates = [
            index
            for index, result in directory_results
            if _is_large_weak_candidate(result, target_category="address", config=config)
        ]

        if not name_candidates or not address_candidates:
            continue

        for candidate_index in name_candidates + address_candidates:
            adjusted[candidate_index] = _promote_cross_file_bundle(adjusted[candidate_index])

    return adjusted


def _demote_weak_ordinary_only(result: FileScanResult) -> FileScanResult:
    categories = frozenset(result.counts_by_category)
    if categories not in WEAK_ORDINARY_ONLY_CATEGORIES:
        return result

    if result.assigned_uz == UZLevel.NO_PDN:
        return _append_reason(result, "WEAK_ORDINARY_ONLY")

    return result.model_copy(
        update={
            "assigned_uz": UZLevel.NO_PDN,
            "classification_reasons": _merged_reasons(result.classification_reasons, "WEAK_ORDINARY_ONLY"),
        }
    )


def _is_large_weak_candidate(result: FileScanResult, *, target_category: str, config: AppConfig) -> bool:
    if frozenset(result.counts_by_category) != frozenset({target_category}):
        return False

    occurrences = result.counts_by_category.get(target_category, 0)
    return occurrences >= config.uz_thresholds.ordinary_large_occurrences


def _promote_cross_file_bundle(result: FileScanResult) -> FileScanResult:
    if "CROSS_FILE_PERSON_ADDRESS_BUNDLE" in result.classification_reasons and result.assigned_uz == UZLevel.UZ3:
        return result

    return result.model_copy(
        update={
            "assigned_uz": UZLevel.UZ3,
            "classification_reasons": _merged_reasons(
                result.classification_reasons,
                "CROSS_FILE_PERSON_ADDRESS_BUNDLE",
            ),
        }
    )


def _append_reason(result: FileScanResult, reason: str) -> FileScanResult:
    if reason in result.classification_reasons:
        return result
    return result.model_copy(update={"classification_reasons": [*result.classification_reasons, reason]})


def _merged_reasons(reasons: list[str], reason: str) -> list[str]:
    if reason in reasons:
        return reasons
    return [*reasons, reason]
