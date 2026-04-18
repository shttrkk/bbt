from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ContentStatus, FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor

from .base import BaseExtractor
from .utils import read_text_with_best_effort


class HTMLExtractor(BaseExtractor):
    formats = (FileFormat.HTML,)
    name = "html"

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        text, warnings = read_text_with_best_effort(Path(file_descriptor.path))
        soup = BeautifulSoup(text, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        visible_text = soup.get_text(separator=" ", strip=True)
        chunks = [visible_text] if visible_text else []
        status = ContentStatus.OK if chunks else ContentStatus.EMPTY
        return ExtractedContent(
            file_path=file_descriptor.path,
            status=status,
            text_chunks=chunks,
            warnings=warnings,
            metadata={"extractor": self.name},
        )
