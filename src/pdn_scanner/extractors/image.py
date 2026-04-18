from __future__ import annotations

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor

from .base import UnsupportedExtractor


class ImageExtractor(UnsupportedExtractor):
    formats = (FileFormat.IMAGE,)
    name = "image"

    def __init__(self) -> None:
        super().__init__(FileFormat.IMAGE)

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        content = super().extract(file_descriptor, config)
        if config.feature_flags.enable_ocr:
            content.warnings.append("OCR mode configured, but image OCR implementation is deferred to v0.3.0")
        else:
            content.warnings.append("Image OCR is intentionally disabled in v0.1.0 baseline")
        return content
