from __future__ import annotations

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor

from .base import UnsupportedExtractor


class VideoExtractor(UnsupportedExtractor):
    formats = (FileFormat.VIDEO,)
    name = "video"

    def __init__(self) -> None:
        super().__init__(FileFormat.VIDEO)

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        content = super().extract(file_descriptor, config)
        content.warnings.append("MP4 processing is best-effort planned and not part of v0.1.0 core")
        return content
