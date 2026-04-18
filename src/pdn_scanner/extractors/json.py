from __future__ import annotations

from pathlib import Path

import orjson

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ContentStatus, FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor

from .base import BaseExtractor
from .utils import flatten_json_to_chunks, read_text_with_best_effort


class JSONExtractor(BaseExtractor):
    formats = (FileFormat.JSON,)
    name = "json"

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        text, warnings = read_text_with_best_effort(Path(file_descriptor.path))
        try:
            payload = orjson.loads(text)
        except orjson.JSONDecodeError:
            return ExtractedContent(
                file_path=file_descriptor.path,
                status=ContentStatus.ERROR,
                text_chunks=[],
                warnings=warnings + ["Invalid JSON payload"],
                metadata={"extractor": self.name},
            )

        chunks = list(flatten_json_to_chunks(payload))
        if len(chunks) > config.detection.max_text_chunks_per_file:
            warnings.append("JSON chunk limit reached; extraction truncated")
            chunks = chunks[: config.detection.max_text_chunks_per_file]

        status = ContentStatus.OK if chunks else ContentStatus.EMPTY
        return ExtractedContent(
            file_path=file_descriptor.path,
            status=status,
            text_chunks=chunks,
            structured_rows_scanned=len(chunks),
            warnings=warnings,
            metadata={"extractor": self.name, "root_type": type(payload).__name__},
        )
