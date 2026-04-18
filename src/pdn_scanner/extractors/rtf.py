from __future__ import annotations

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor

from .base import UnsupportedExtractor


class RTFExtractor(UnsupportedExtractor):
    formats = (FileFormat.RTF,)
    name = "rtf"

    def __init__(self) -> None:
        super().__init__(FileFormat.RTF)

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        content = super().extract(file_descriptor, config)
        content.warnings.append("RTF extraction hook is present but not implemented yet")
        return content
