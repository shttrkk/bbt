from __future__ import annotations

from collections import defaultdict

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ConfidenceLevel, UZLevel, ValidationStatus
from pdn_scanner.models import DetectionResult


class UZClassifier:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def classify(self, detections: list[DetectionResult]) -> tuple[UZLevel, list[str], dict[str, dict[str, int]]]:
        family_summary = self._build_family_summary(detections)
        reasons: list[str] = []

        ordinary_present = self._family_present("ordinary", detections)
        government_present = self._family_present("government", detections)
        payment_present = any(
            detection.family == "payment" and detection.validation_status == ValidationStatus.VALID for detection in detections
        )
        special_present = self._family_present("special", detections)
        biometric_present = self._family_present("biometric", detections)

        if special_present or biometric_present:
            reasons.append("SPECIAL_OR_BIOMETRIC_PRESENT")
            return UZLevel.UZ1, reasons, family_summary

        if payment_present:
            reasons.append("VALIDATED_PAYMENT_PRESENT")
            return UZLevel.UZ2, reasons, family_summary

        if self._is_large("government", family_summary):
            reasons.append("GOVERNMENT_LARGE_VOLUME")
            return UZLevel.UZ2, reasons, family_summary

        if government_present:
            reasons.append("GOVERNMENT_PRESENT")
            return UZLevel.UZ3, reasons, family_summary

        if self._is_large("ordinary", family_summary):
            reasons.append("ORDINARY_LARGE_VOLUME")
            return UZLevel.UZ3, reasons, family_summary

        if ordinary_present:
            reasons.append("ORDINARY_PRESENT")
            return UZLevel.UZ4, reasons, family_summary

        reasons.append("NO_STRONG_PDN_SIGNALS")
        return UZLevel.NO_PDN, reasons, family_summary

    def _family_present(self, family: str, detections: list[DetectionResult]) -> bool:
        for detection in detections:
            if detection.family != family:
                continue
            if family == "payment" and detection.validation_status != ValidationStatus.VALID:
                continue
            if family == "government" and detection.validation_status == ValidationStatus.INVALID:
                continue
            if detection.confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM}:
                return True
        return False

    def _build_family_summary(self, detections: list[DetectionResult]) -> dict[str, dict[str, int]]:
        summary: dict[str, dict[str, int]] = defaultdict(lambda: {"occurrences": 0, "unique": 0, "rows": 0})
        unique_by_family: dict[str, set[str]] = defaultdict(set)
        rows_by_family: dict[str, set[str]] = defaultdict(set)

        for detection in detections:
            if detection.family == "payment" and detection.validation_status != ValidationStatus.VALID:
                continue
            if detection.family == "government" and detection.validation_status == ValidationStatus.INVALID:
                continue
            if detection.confidence not in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM}:
                continue

            summary[detection.family]["occurrences"] += detection.occurrences
            if detection.value_hash:
                unique_by_family[detection.family].add(detection.value_hash)
            rows_by_family[detection.family].update(detection.location_hints)

        for family in summary:
            summary[family]["unique"] = len(unique_by_family[family])
            summary[family]["rows"] = len(rows_by_family[family])

        return dict(summary)

    def _is_large(self, family: str, summary: dict[str, dict[str, int]]) -> bool:
        family_data = summary.get(family, {})
        thresholds = self.config.uz_thresholds

        if family == "ordinary":
            return (
                family_data.get("unique", 0) >= thresholds.ordinary_large_unique
                or family_data.get("occurrences", 0) >= thresholds.ordinary_large_occurrences
                or family_data.get("rows", 0) >= thresholds.ordinary_large_rows
            )

        if family == "government":
            return (
                family_data.get("unique", 0) >= thresholds.government_large_unique
                or family_data.get("occurrences", 0) >= thresholds.government_large_occurrences
                or family_data.get("rows", 0) >= thresholds.government_large_rows
            )

        if family == "payment":
            return (
                family_data.get("unique", 0) >= thresholds.payment_large_unique
                or family_data.get("occurrences", 0) >= thresholds.payment_large_occurrences
                or family_data.get("rows", 0) >= thresholds.payment_large_rows
            )

        return False
