from __future__ import annotations

from pdn_scanner.enums import FileFormat
from pdn_scanner.extractors import (
    CSVExtractor,
    DOCXExtractor,
    HTMLExtractor,
    ImageExtractor,
    JSONExtractor,
    LegacyOfficeExtractor,
    ParquetExtractor,
    PDFExtractor,
    RTFExtractor,
    TXTExtractor,
    UnsupportedExtractor,
    VideoExtractor,
    XLSExtractor,
)
from pdn_scanner.extractors.base import BaseExtractor


class ExtractorDispatcher:
    def __init__(self) -> None:
        self._registry: dict[FileFormat, BaseExtractor] = {
            FileFormat.TXT: TXTExtractor(),
            FileFormat.CSV: CSVExtractor(),
            FileFormat.JSON: JSONExtractor(),
            FileFormat.HTML: HTMLExtractor(),
            FileFormat.PDF: PDFExtractor(),
            FileFormat.DOCX: DOCXExtractor(),
            FileFormat.RTF: RTFExtractor(),
            FileFormat.XLS: XLSExtractor(),
            FileFormat.PARQUET: ParquetExtractor(),
            FileFormat.IMAGE: ImageExtractor(),
            FileFormat.DOC: LegacyOfficeExtractor(),
            FileFormat.VIDEO: VideoExtractor(),
        }

    def get_extractor(self, file_format: FileFormat) -> BaseExtractor:
        return self._registry.get(file_format, UnsupportedExtractor(file_format))
