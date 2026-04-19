from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import FileFormat, StorageClass, UZLevel
from pdn_scanner.models import FileScanResult

STRUCTURED_CORRELATION_FORMATS = {FileFormat.CSV, FileFormat.JSON, FileFormat.PARQUET, FileFormat.XLS}
CORRELATION_FORMATS = {
    FileFormat.CSV,
    FileFormat.JSON,
    FileFormat.PARQUET,
    FileFormat.XLS,
    FileFormat.TXT,
    FileFormat.DOCX,
    FileFormat.RTF,
    FileFormat.PDF,
    FileFormat.IMAGE,
    FileFormat.DOC,
}
WEAK_SINGLETON_CATEGORIES = {
    frozenset({"person_name"}),
    frozenset({"address"}),
    frozenset({"phone"}),
    frozenset({"email"}),
    frozenset({"birth_date"}),
    frozenset({"birth_place"}),
}
SOFT_ANCHORS = {"person_name"}
HARD_ANCHORS = {
    "snils",
    "passport_series",
    "passport_number",
    "passport_series_number",
    "inn_individual",
    "bank_card",
    "driver_license",
    "mrz",
}
COMPANIONS = {"address", "phone", "email", "birth_date", "birth_place"}
LINKABLE_HASH_CATEGORIES = SOFT_ANCHORS | HARD_ANCHORS | {"phone", "email"}
SMALL_DIRECTORY_MAX_FILES = 6
UZ_RANK = {
    UZLevel.UZ1: 4,
    UZLevel.UZ2: 3,
    UZLevel.UZ3: 2,
    UZLevel.UZ4: 1,
    UZLevel.NO_PDN: 0,
}


def apply_cross_file_promotion(results: list[FileScanResult], config: AppConfig) -> list[FileScanResult]:
    adjusted = [_demote_weak_singletons(result) for result in results]
    grouped: dict[str, list[tuple[int, FileScanResult]]] = defaultdict(list)

    for index, result in enumerate(adjusted):
        if result.file.detected_format not in CORRELATION_FORMATS:
            continue
        grouped[str(Path(result.file.rel_path).parent)].append((index, result))

    for directory_results in grouped.values():
        _apply_large_structured_pair_promotion(adjusted, directory_results, config)
        _apply_shared_linkage_promotion(adjusted, directory_results)
        _apply_small_directory_bundle_promotion(adjusted, directory_results)

    return adjusted


def _demote_weak_singletons(result: FileScanResult) -> FileScanResult:
    if result.storage_class != StorageClass.TARGET_LEAK:
        return result

    categories = frozenset(result.counts_by_category)
    if categories not in WEAK_SINGLETON_CATEGORIES:
        return result

    if result.assigned_uz == UZLevel.NO_PDN:
        return _append_reason(result, "WEAK_ORDINARY_ONLY")

    return result.model_copy(
        update={
            "assigned_uz": UZLevel.NO_PDN,
            "classification_reasons": _merged_reasons(result.classification_reasons, "WEAK_ORDINARY_ONLY"),
        }
    )


def _apply_large_structured_pair_promotion(
    adjusted: list[FileScanResult],
    directory_results: list[tuple[int, FileScanResult]],
    config: AppConfig,
) -> None:
    structured = [
        (index, result)
        for index, result in directory_results
        if result.file.detected_format in STRUCTURED_CORRELATION_FORMATS and _eligible_for_leak_promotion(result)
    ]
    name_candidates = [
        index
        for index, result in structured
        if _is_large_weak_candidate(result, target_category="person_name", config=config)
    ]
    address_candidates = [
        index
        for index, result in structured
        if _is_large_weak_candidate(result, target_category="address", config=config)
    ]

    if not name_candidates or not address_candidates:
        return

    for candidate_index in name_candidates + address_candidates:
        adjusted[candidate_index] = _promote_cross_file_bundle(
            adjusted[candidate_index],
            UZLevel.UZ3,
            "CROSS_FILE_PERSON_ADDRESS_BUNDLE",
        )


def _apply_shared_linkage_promotion(
    adjusted: list[FileScanResult],
    directory_results: list[tuple[int, FileScanResult]],
) -> None:
    links: dict[str, set[int]] = defaultdict(set)
    present_indexes = {index for index, result in directory_results if result.detections}
    for index, result in directory_results:
        if not _eligible_for_leak_promotion(result):
            continue
        for detection in result.detections:
            if detection.category not in LINKABLE_HASH_CATEGORIES or not detection.value_hash:
                continue
            links[detection.value_hash].add(index)

    adjacency: dict[int, set[int]] = {index: set() for index in present_indexes}
    for indexes in links.values():
        if len(indexes) < 2:
            continue
        for index in indexes:
            adjacency[index].update(indexes - {index})

    visited: set[int] = set()
    for index in present_indexes:
        if index in visited or not adjacency.get(index):
            continue

        stack = [index]
        component: set[int] = set()
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            stack.extend(adjacency.get(current, set()) - visited)

        if len(component) < 2:
            continue

        categories = _component_categories(adjusted, component)
        if not _has_promotable_bundle(categories):
            continue

        target_level = _cross_file_target_level(categories)
        for component_index in component:
            adjusted[component_index] = _promote_cross_file_bundle(
                adjusted[component_index],
                target_level,
                "CROSS_FILE_SHARED_LINKAGE_BUNDLE",
            )


def _apply_small_directory_bundle_promotion(
    adjusted: list[FileScanResult],
    directory_results: list[tuple[int, FileScanResult]],
) -> None:
    candidates = [
        index
        for index, result in directory_results
        if result.detections and result.file.detected_format in CORRELATION_FORMATS and _eligible_for_leak_promotion(result)
    ]
    if len(candidates) < 2 or len(candidates) > SMALL_DIRECTORY_MAX_FILES:
        return

    categories = _component_categories(adjusted, set(candidates))
    if not _has_promotable_bundle(categories):
        return

    contributors = 0
    for index in candidates:
        file_categories = set(adjusted[index].counts_by_category)
        if file_categories.intersection(SOFT_ANCHORS | HARD_ANCHORS | COMPANIONS):
            contributors += 1
    if contributors < 2:
        return

    target_level = _cross_file_target_level(categories)
    for candidate_index in candidates:
        adjusted[candidate_index] = _promote_cross_file_bundle(
            adjusted[candidate_index],
            target_level,
            "CROSS_FILE_SMALL_DIRECTORY_BUNDLE",
        )


def _component_categories(adjusted: list[FileScanResult], component: set[int]) -> set[str]:
    categories: set[str] = set()
    for index in component:
        categories.update(adjusted[index].counts_by_category)
    return categories


def _has_promotable_bundle(categories: set[str]) -> bool:
    if categories.intersection(HARD_ANCHORS):
        return True
    if categories.intersection(SOFT_ANCHORS) and categories.intersection(COMPANIONS):
        return True
    return False


def _cross_file_target_level(categories: set[str]) -> UZLevel:
    if categories.intersection({"health_data", "religious_beliefs", "political_beliefs", "race_data", "nationality_data"}):
        return UZLevel.UZ1
    if categories.intersection({"bank_card"}):
        return UZLevel.UZ2
    if categories.intersection(HARD_ANCHORS):
        return UZLevel.UZ3
    return UZLevel.UZ4


def _is_large_weak_candidate(result: FileScanResult, *, target_category: str, config: AppConfig) -> bool:
    if frozenset(result.counts_by_category) != frozenset({target_category}):
        return False

    occurrences = result.counts_by_category.get(target_category, 0)
    return occurrences >= config.uz_thresholds.ordinary_large_occurrences


def _promote_cross_file_bundle(result: FileScanResult, target_level: UZLevel, reason: str) -> FileScanResult:
    merged_reasons = _merged_reasons(result.classification_reasons, reason)
    if UZ_RANK.get(result.assigned_uz, 0) >= UZ_RANK.get(target_level, 0):
        return result.model_copy(
            update={
                "classification_reasons": merged_reasons,
                "storage_class": StorageClass.TARGET_LEAK,
            }
        )

    return result.model_copy(
        update={
            "assigned_uz": target_level,
            "classification_reasons": merged_reasons,
            "storage_class": StorageClass.TARGET_LEAK,
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


def _eligible_for_leak_promotion(result: FileScanResult) -> bool:
    return result.storage_class == StorageClass.TARGET_LEAK
