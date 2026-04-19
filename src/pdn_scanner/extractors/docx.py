from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ContentStatus, FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor

from .base import BaseExtractor

WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
DOCX_XML_PARTS = ("word/document.xml",)


class DOCXExtractor(BaseExtractor):
    formats = (FileFormat.DOCX,)
    name = "docx"

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        path = Path(file_descriptor.path)
        warnings: list[str] = []

        try:
            chunks = _extract_docx_chunks(path, config)
        except BadZipFile:
            return ExtractedContent(
                file_path=file_descriptor.path,
                status=ContentStatus.EMPTY,
                text_chunks=[],
                warnings=["DOCX archive is corrupted or not a valid zip package"],
                metadata={"extractor": self.name},
            )
        except Exception as exc:
            return ExtractedContent(
                file_path=file_descriptor.path,
                status=ContentStatus.ERROR,
                text_chunks=[],
                warnings=[f"DOCX text extraction failed: {exc}"],
                metadata={"extractor": self.name},
            )

        status = ContentStatus.OK if chunks else ContentStatus.EMPTY
        return ExtractedContent(
            file_path=file_descriptor.path,
            status=status,
            text_chunks=chunks,
            warnings=warnings,
            metadata={"extractor": self.name},
        )


def _extract_docx_chunks(path: Path, config: AppConfig) -> list[str]:
    chunks: list[str] = []
    with ZipFile(path) as archive:
        parts = [name for name in archive.namelist() if name in DOCX_XML_PARTS or _is_header_footer(name)]
        for part_name in parts:
            xml_payload = archive.read(part_name)
            chunks.extend(_extract_paragraph_chunks(xml_payload))
            if len(chunks) >= config.detection.max_text_chunks_per_file:
                return chunks[: config.detection.max_text_chunks_per_file]
    return chunks[: config.detection.max_text_chunks_per_file]


def _extract_paragraph_chunks(xml_payload: bytes) -> list[str]:
    root = ET.fromstring(xml_payload)
    chunks: list[str] = []

    for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
        texts = [node.text for node in paragraph.findall(".//w:t", WORD_NAMESPACE) if node.text]
        if not texts:
            continue
        value = " ".join(" ".join(texts).split())
        if value:
            chunks.append(value)

    return chunks


def _is_header_footer(name: str) -> bool:
    return name.startswith("word/header") or name.startswith("word/footer")
