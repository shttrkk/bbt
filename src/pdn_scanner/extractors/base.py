from __future__ import annotations

from abc import ABC, abstractmethod

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ContentStatus, FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor


class BaseExtractor(ABC):
    formats: tuple[FileFormat, ...] = ()
    name: str = "base"

    @abstractmethod
    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        raise NotImplementedError


class UnsupportedExtractor(BaseExtractor):
    name = "unsupported"

    def __init__(self, format_name: FileFormat | None = None) -> None:
        self.format_name = format_name or FileFormat.UNKNOWN

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        return ExtractedContent(
            file_path=file_descriptor.path,
            status=ContentStatus.UNSUPPORTED,
            text_chunks=[],
            warnings=[f"Extractor for format '{self.format_name.value}' is not implemented in v0.1.0"],
            metadata={"extractor": self.name},
        )
