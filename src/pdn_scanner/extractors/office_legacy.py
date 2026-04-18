from __future__ import annotations

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor

from .base import UnsupportedExtractor


class LegacyOfficeExtractor(UnsupportedExtractor):
    formats = (FileFormat.DOC,)
    name = "office_legacy"

    def __init__(self) -> None:
        super().__init__(FileFormat.DOC)

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        content = super().extract(file_descriptor, config)
        content.warnings.append("Legacy DOC fallback chain is planned for later versions")
        return content
