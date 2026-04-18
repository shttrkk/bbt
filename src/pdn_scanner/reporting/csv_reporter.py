from __future__ import annotations

import csv
from pathlib import Path

from pdn_scanner.config import AppConfig
from pdn_scanner.models import FileScanResult, RunSummary


def write_summary_csv(output_dir: Path, summary: RunSummary, results: list[FileScanResult], config: AppConfig) -> Path:
    output_path = output_dir / config.reporting.summary_csv_name
    fieldnames = [
        "run_id",
        "rel_path",
        "format",
        "size_bytes",
        "extraction_status",
        "assigned_uz",
        "detections_total",
        "counts_by_category",
        "validated_counts_by_category",
        "template_like",
        "ocr_used",
        "classification_reasons",
        "error_count",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "run_id": summary.run_id,
                    "rel_path": result.file.rel_path,
                    "format": result.file.detected_format.value,
                    "size_bytes": result.file.size_bytes,
                    "extraction_status": result.extraction.status.value,
                    "assigned_uz": result.assigned_uz.value,
                    "detections_total": sum(detection.occurrences for detection in result.detections),
                    "counts_by_category": _format_mapping(result.counts_by_category),
                    "validated_counts_by_category": _format_mapping(result.validated_counts_by_category),
                    "template_like": result.template_like,
                    "ocr_used": result.ocr_used,
                    "classification_reasons": ";".join(result.classification_reasons),
                    "error_count": len(result.errors),
                }
            )

    return output_path


def write_result_csv(output_dir: Path, results: list[FileScanResult], config: AppConfig) -> Path:
    output_path = output_dir / config.reporting.result_csv_name
    fieldnames = ["path", "categories", "uz", "total_hits", "ext"]

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "path": result.file.rel_path,
                    "categories": _format_legacy_categories(result.counts_by_family),
                    "uz": _format_legacy_uz(result.assigned_uz.value),
                    "total_hits": sum(detection.occurrences for detection in result.detections),
                    "ext": result.file.detected_format.value,
                }
            )

    return output_path


def _format_mapping(values: dict[str, int]) -> str:
    return ";".join(f"{key}={value}" for key, value in sorted(values.items()))


def _format_legacy_categories(values: dict[str, int]) -> str:
    if not values:
        return "{}"

    family_map = {
        "ordinary": "обычные",
        "government": "государственные",
        "payment": "платёжные",
        "biometric": "биометрические",
        "special": "специальные",
    }
    ordered = {
        family_map.get(key, key): values[key]
        for key in sorted(values)
        if values.get(key, 0) > 0
    }
    parts = [f'"{key}": {value}' for key, value in ordered.items()]
    return "{" + ", ".join(parts) + "}"


def _format_legacy_uz(value: str) -> str:
    return "нет признаков" if value == "NO_PDN" else value
