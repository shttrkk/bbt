from __future__ import annotations

from pathlib import Path

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ContentStatus, FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor

from .base import BaseExtractor
from .textutil import extract_text_with_textutil


class RTFExtractor(BaseExtractor):
    formats = (FileFormat.RTF,)
    name = "rtf"

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        result = extract_text_with_textutil(
            Path(file_descriptor.path),
            input_format="rtf",
            max_chunks=config.detection.max_text_chunks_per_file,
        )
        if not result.available:
            return ExtractedContent(
                file_path=file_descriptor.path,
                status=ContentStatus.UNSUPPORTED,
                text_chunks=[],
                warnings=result.warnings,
                metadata={"extractor": self.name},
            )

        status = ContentStatus.OK if result.chunks else ContentStatus.EMPTY
        return ExtractedContent(
            file_path=file_descriptor.path,
            status=status,
            text_chunks=result.chunks,
            warnings=result.warnings,
            metadata={"extractor": self.name},
        )
