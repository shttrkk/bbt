from __future__ import annotations

from collections import defaultdict

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ConfidenceLevel, StorageClass, UZLevel, ValidationStatus
from pdn_scanner.models import DetectionResult


class UZClassifier:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def classify(
        self,
        detections: list[DetectionResult],
        *,
        storage_class: StorageClass = StorageClass.NON_TARGET,
        primary_genre: str = "unknown",
        risk_score: int = 0,
        justification_score: int = 0,
        noise_score: int = 0,
        is_template: bool = False,
        is_public_doc: bool = False,
        is_reference_data: bool = False,
        quality_reasons: list[str] | None = None,
    ) -> tuple[UZLevel, list[str], dict[str, dict[str, int]]]:
        family_summary = self._build_family_summary(detections)
        reasons: list[str] = list(quality_reasons or [])
        reasons.extend(
            [
                f"STORAGE_CLASS:{storage_class.value}",
                f"PRIMARY_GENRE:{primary_genre}",
                f"RISK_SCORE:{risk_score}",
                f"JUSTIFICATION_SCORE:{justification_score}",
                f"NOISE_SCORE:{noise_score}",
            ]
        )

        if storage_class == StorageClass.PD_BUT_JUSTIFIED_STORAGE:
            reasons.append("JUSTIFIED_STORAGE_SUPPRESSED")
            return UZLevel.NO_PDN, sorted(set(reasons)), family_summary

        if storage_class != StorageClass.TARGET_LEAK:
            reasons.append("NON_LEAK_CONTEXT_SUPPRESSED")
            return UZLevel.NO_PDN, sorted(set(reasons)), family_summary

        if is_template and not self._has_trusted_detections(detections):
            reasons.append("TEMPLATE_SUPPRESSED")
            return UZLevel.NO_PDN, sorted(set(reasons)), family_summary

        if is_public_doc and not self._has_validated_or_sensitive(detections):
            reasons.append("PUBLIC_DOC_SUPPRESSED")
            return UZLevel.NO_PDN, sorted(set(reasons)), family_summary

        if is_reference_data and not self._has_trusted_detections(detections):
            reasons.append("REFERENCE_DATA_SUPPRESSED")
            return UZLevel.NO_PDN, sorted(set(reasons)), family_summary

        ordinary_present = self._family_present("ordinary", detections)
        government_present = self._family_present("government", detections)
        payment_present = any(
            detection.family == "payment" and detection.validation_status == ValidationStatus.VALID for detection in detections
        )
        special_present = self._family_present("special", detections)
        biometric_present = self._family_present("biometric", detections)

        if special_present or biometric_present:
            reasons.append("LEAK_SPECIAL_OR_BIOMETRIC")
            return UZLevel.UZ1, sorted(set(reasons)), family_summary

        if payment_present:
            reasons.append("LEAK_VALIDATED_PAYMENT")
            return UZLevel.UZ2, sorted(set(reasons)), family_summary

        if self._is_large("government", family_summary):
            reasons.append("LEAK_GOVERNMENT_LARGE_VOLUME")
            return UZLevel.UZ2, sorted(set(reasons)), family_summary

        if government_present:
            reasons.append("LEAK_GOVERNMENT_PRESENT")
            return UZLevel.UZ3, sorted(set(reasons)), family_summary

        if self._is_large("ordinary", family_summary):
            reasons.append("LEAK_ORDINARY_LARGE_VOLUME")
            return UZLevel.UZ3, sorted(set(reasons)), family_summary

        if ordinary_present:
            reasons.append("LEAK_ORDINARY_PRESENT")
            return UZLevel.UZ4, sorted(set(reasons)), family_summary

        reasons.append("LEAK_CONTEXT_WITHOUT_TRUSTED_PDN")
        return UZLevel.NO_PDN, sorted(set(reasons)), family_summary

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

    def _has_trusted_detections(self, detections: list[DetectionResult]) -> bool:
        return any(
            (detection.family in {"government", "payment"} and detection.validation_status == ValidationStatus.VALID)
            or (
                detection.category in {"person_name", "address", "birth_date", "birth_place"}
                and detection.confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM}
            )
            for detection in detections
        )

    def _has_validated_or_sensitive(self, detections: list[DetectionResult]) -> bool:
        return any(
            detection.family in {"special", "biometric"}
            or (detection.family in {"government", "payment"} and detection.validation_status == ValidationStatus.VALID)
            for detection in detections
        )
