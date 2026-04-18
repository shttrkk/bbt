from __future__ import annotations

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor

from .base import UnsupportedExtractor


class XLSExtractor(UnsupportedExtractor):
    formats = (FileFormat.XLS,)
    name = "xls"

    def __init__(self) -> None:
        super().__init__(FileFormat.XLS)

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        content = super().extract(file_descriptor, config)
        content.warnings.append("XLS/XLSX extraction is planned for v0.2.0")
        return content
