from __future__ import annotations

from collections import defaultdict

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ConfidenceLevel, UZLevel, ValidationStatus
from pdn_scanner.models import DetectionResult


class UZClassifier:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def classify(
        self,
        detections: list[DetectionResult],
        *,
        is_template: bool = False,
        is_public_doc: bool = False,
        is_reference_data: bool = False,
        quality_reasons: list[str] | None = None,
    ) -> tuple[UZLevel, list[str], dict[str, dict[str, int]]]:
        family_summary = self._build_family_summary(detections)
        reasons: list[str] = list(quality_reasons or [])

        if is_template and not self._has_trusted_detections(detections):
            reasons.append("TEMPLATE_SUPPRESSED")
            return UZLevel.NO_PDN, reasons, family_summary

        if is_public_doc and self._public_doc_weak_signals_only(detections):
            reasons.append("PUBLIC_DOC_WEAK_SIGNALS_ONLY")
            return UZLevel.NO_PDN, reasons, family_summary

        if is_reference_data and not self._has_trusted_detections(detections):
            reasons.append("REFERENCE_DATA_WEAK_SIGNALS_ONLY")
            return UZLevel.NO_PDN, reasons, family_summary

        ordinary_present = self._family_present("ordinary", detections)
        government_present = self._family_present("government", detections)
        payment_present = any(
            detection.family == "payment" and detection.validation_status == ValidationStatus.VALID for detection in detections
        )
        special_present = self._family_present("special", detections)
        biometric_present = self._family_present("biometric", detections)

        if special_present or biometric_present:
            reasons.append("SPECIAL_OR_BIOMETRIC_PRESENT")
            return self._apply_quality_caps(UZLevel.UZ1, reasons, ordinary_present, is_template, is_public_doc, is_reference_data), reasons, family_summary

        if payment_present:
            reasons.append("VALIDATED_PAYMENT_PRESENT")
            return self._apply_quality_caps(UZLevel.UZ2, reasons, ordinary_present, is_template, is_public_doc, is_reference_data), reasons, family_summary

        if self._is_large("government", family_summary):
            reasons.append("GOVERNMENT_LARGE_VOLUME")
            return self._apply_quality_caps(UZLevel.UZ2, reasons, ordinary_present, is_template, is_public_doc, is_reference_data), reasons, family_summary

        if government_present:
            reasons.append("GOVERNMENT_PRESENT")
            return self._apply_quality_caps(UZLevel.UZ3, reasons, ordinary_present, is_template, is_public_doc, is_reference_data), reasons, family_summary

        if self._is_large("ordinary", family_summary):
            reasons.append("ORDINARY_LARGE_VOLUME")
            return self._apply_quality_caps(UZLevel.UZ3, reasons, ordinary_present, is_template, is_public_doc, is_reference_data), reasons, family_summary

        if ordinary_present:
            reasons.append("ORDINARY_PRESENT")
            return self._apply_quality_caps(UZLevel.UZ4, reasons, ordinary_present, is_template, is_public_doc, is_reference_data), reasons, family_summary

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

    def _public_doc_weak_signals_only(self, detections: list[DetectionResult]) -> bool:
        if not detections:
            return True

        return not any(
            detection.category in {"person_name", "address", "birth_date_candidate"}
            or (detection.family in {"government", "payment"} and detection.validation_status == ValidationStatus.VALID)
            for detection in detections
        )

    def _has_trusted_detections(self, detections: list[DetectionResult]) -> bool:
        return any(
            (detection.family in {"government", "payment"} and detection.validation_status == ValidationStatus.VALID)
            or (
                detection.category in {"person_name", "address", "birth_date_candidate"}
                and detection.confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM}
            )
            for detection in detections
        )

    def _apply_quality_caps(
        self,
        level: UZLevel,
        reasons: list[str],
        ordinary_present: bool,
        is_template: bool,
        is_public_doc: bool,
        is_reference_data: bool,
    ) -> UZLevel:
        if is_template and level in {UZLevel.UZ1, UZLevel.UZ2, UZLevel.UZ3}:
            reasons.append("TEMPLATE_RISK_REDUCED")
            return UZLevel.UZ4 if ordinary_present else UZLevel.NO_PDN

        if is_public_doc and level in {UZLevel.UZ1, UZLevel.UZ2, UZLevel.UZ3}:
            reasons.append("PUBLIC_DOC_RISK_REDUCED")
            return UZLevel.UZ4 if ordinary_present else UZLevel.NO_PDN

        if is_reference_data and level in {UZLevel.UZ2, UZLevel.UZ3}:
            reasons.append("REFERENCE_DATA_RISK_REDUCED")
            return UZLevel.UZ4 if ordinary_present else UZLevel.NO_PDN

        return level
