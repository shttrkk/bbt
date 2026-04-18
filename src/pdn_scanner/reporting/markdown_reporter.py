from __future__ import annotations

from pathlib import Path

from pdn_scanner.config import AppConfig
from pdn_scanner.models import FileScanResult, RunSummary


def write_markdown_report(
    output_dir: Path, summary: RunSummary, results: list[FileScanResult], config: AppConfig
) -> Path:
    output_path = output_dir / config.reporting.markdown_report_name
    top_files = sorted(results, key=lambda item: sum(d.occurrences for d in item.detections), reverse=True)[:10]

    lines = [
        "# PDN Scan Report",
        "",
        f"- Run ID: `{summary.run_id}`",
        f"- Version: `{summary.version}`",
        f"- Input: `{summary.input_dir}`",
        f"- Files discovered: `{summary.files_discovered}`",
        f"- Files processed: `{summary.files_processed}`",
        f"- Files with detections: `{summary.files_with_detections}`",
        f"- Files with errors: `{summary.files_with_errors}`",
        "",
        "## UZ Distribution",
        "",
    ]

    if summary.totals_by_uz:
        for key, value in sorted(summary.totals_by_uz.items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- no results")

    lines.extend(["", "## Top Files", ""])

    if top_files:
        for result in top_files:
            total = sum(detection.occurrences for detection in result.detections)
            lines.append(
                f"- `{result.file.rel_path}` -> {result.assigned_uz.value}, detections={total}, categories={_format_categories(result)}"
            )
    else:
        lines.append("- no files with detections")

    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in summary.notes or ["report is privacy-safe and excludes raw PII"])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def _format_categories(result: FileScanResult) -> str:
    if not result.counts_by_category:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(result.counts_by_category.items()))
