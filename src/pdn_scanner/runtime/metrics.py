from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from pdn_scanner.models import FileScanResult, ProcessingError


@dataclass
class ScanMetrics:
    totals_by_format: Counter[str] = field(default_factory=Counter)
    totals_by_uz: Counter[str] = field(default_factory=Counter)
    totals_by_category: Counter[str] = field(default_factory=Counter)
    errors: list[ProcessingError] = field(default_factory=list)
    files_with_detections: int = 0
    files_with_errors: int = 0

    def record_file_result(self, result: FileScanResult) -> None:
        self.totals_by_format[result.file.detected_format.value] += 1
        self.totals_by_uz[result.assigned_uz.value] += 1

        if result.detections:
            self.files_with_detections += 1

        if result.errors or result.extraction.status == "error":
            self.files_with_errors += 1
            self.errors.extend(result.errors)

        for category, count in result.counts_by_category.items():
            self.totals_by_category[category] += count

    def extend_errors(self, errors: list[ProcessingError]) -> None:
        if errors:
            self.errors.extend(errors)
            self.files_with_errors += len(errors)
