from __future__ import annotations

import csv
import io
from pathlib import Path

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ContentStatus, FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor

from .base import BaseExtractor
from .utils import read_text_with_best_effort


class CSVExtractor(BaseExtractor):
    formats = (FileFormat.CSV,)
    name = "csv"

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        text, warnings = read_text_with_best_effort(Path(file_descriptor.path))
        sample = text[:2048]
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel

        rows_scanned = 0
        chunks: list[str] = []
        reader = csv.reader(io.StringIO(text), dialect)
        header = next(reader, None)

        for rows_scanned, row in enumerate(reader, start=1):
            if rows_scanned > config.detection.max_text_chunks_per_file:
                warnings.append("CSV chunk limit reached; extraction truncated")
                break

            if header and len(header) == len(row):
                chunk = " | ".join(f"{column}: {value}" for column, value in zip(header, row, strict=True) if value)
            else:
                chunk = " | ".join(value for value in row if value)

            if chunk:
                chunks.append(chunk)

        status = ContentStatus.OK if chunks else ContentStatus.EMPTY
        return ExtractedContent(
            file_path=file_descriptor.path,
            status=status,
            text_chunks=chunks,
            structured_rows_scanned=rows_scanned,
            warnings=warnings,
            metadata={"extractor": self.name, "header": header or []},
        )
