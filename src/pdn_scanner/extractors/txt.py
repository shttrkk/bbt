from __future__ import annotations

from pathlib import Path

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ContentStatus, FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor

from .base import BaseExtractor
from .utils import read_text_with_best_effort


class TXTExtractor(BaseExtractor):
    formats = (FileFormat.TXT,)
    name = "txt"

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        text, warnings = read_text_with_best_effort(Path(file_descriptor.path))
        chunks = [text] if text.strip() else []
        status = ContentStatus.OK if chunks else ContentStatus.EMPTY
        return ExtractedContent(
            file_path=file_descriptor.path,
            status=status,
            text_chunks=chunks,
            warnings=warnings,
            metadata={"extractor": self.name},
        )
