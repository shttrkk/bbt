from __future__ import annotations

import json
from pathlib import Path

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ContentStatus, FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor

from .base import BaseExtractor

try:
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover - optional dependency path
    pq = None


class ParquetExtractor(BaseExtractor):
    formats = (FileFormat.PARQUET,)
    name = "parquet"

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        if pq is None:
            return ExtractedContent(
                file_path=file_descriptor.path,
                status=ContentStatus.UNSUPPORTED,
                text_chunks=[],
                warnings=["pyarrow is unavailable; parquet extraction skipped"],
                metadata={"extractor": self.name},
            )

        path = Path(file_descriptor.path)
        warnings: list[str] = []

        try:
            parquet_file = pq.ParquetFile(path)
            header = list(parquet_file.schema_arrow.names)
            row_limit = config.detection.max_text_chunks_per_file
            batch_size = max(1, min(config.scan.csv_chunk_size, row_limit))
            chunks: list[str] = []

            for batch in parquet_file.iter_batches(batch_size=batch_size):
                for row in batch.to_pylist():
                    if len(chunks) >= row_limit:
                        warnings.append("Parquet chunk limit reached; extraction truncated")
                        break

                    chunk = _format_row(row, header)
                    if chunk:
                        chunks.append(chunk)

                if len(chunks) >= row_limit:
                    break

            status = ContentStatus.OK if chunks else ContentStatus.EMPTY
            return ExtractedContent(
                file_path=file_descriptor.path,
                status=status,
                text_chunks=chunks,
                structured_rows_scanned=len(chunks),
                warnings=warnings,
                metadata={
                    "extractor": self.name,
                    "header": header,
                    "schema": [f"{field.name}:{field.type}" for field in parquet_file.schema_arrow],
                },
            )
        except Exception as exc:
            return ExtractedContent(
                file_path=file_descriptor.path,
                status=ContentStatus.ERROR,
                text_chunks=[],
                warnings=[f"Parquet extraction failed: {exc}"],
                metadata={"extractor": self.name},
            )


def _format_row(row: dict[str, object], header: list[str]) -> str:
    pieces: list[str] = []
    for column in header:
        value = _stringify_value(row.get(column))
        if value:
            pieces.append(f"{column}: {value}")
    return " | ".join(pieces)


def _stringify_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return " ".join(value.decode("utf-8", errors="ignore").split())
    if isinstance(value, (list, tuple, dict, set)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return " ".join(str(value).split())
