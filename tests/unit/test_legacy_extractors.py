from __future__ import annotations

from pathlib import Path

from pdn_scanner.config import load_config
from pdn_scanner.enums import ContentStatus, FileFormat
from pdn_scanner.extractors.office_legacy import LegacyOfficeExtractor
from pdn_scanner.extractors.rtf import RTFExtractor
from pdn_scanner.extractors.textutil import TextutilExtractionResult
from pdn_scanner.models import FileDescriptor


def test_rtf_extractor_uses_textutil_result(tmp_path: Path, monkeypatch) -> None:
    config = load_config("configs/default.yaml")
    file_path = tmp_path / "consent.rtf"
    file_path.write_text("{\\rtf1 test}", encoding="utf-8")

    monkeypatch.setattr(
        "pdn_scanner.extractors.rtf.extract_text_with_textutil",
        lambda path, input_format, max_chunks: TextutilExtractionResult(
            chunks=["ФИО: Иванов Иван Иванович", "Телефон: +7 999 123-45-67"],
            warnings=[],
            available=True,
        ),
    )

    extractor = RTFExtractor()
    descriptor = FileDescriptor(
        path=str(file_path),
        rel_path="consent.rtf",
        size_bytes=file_path.stat().st_size,
        extension=".rtf",
        detected_format=FileFormat.RTF,
    )

    extracted = extractor.extract(descriptor, config)

    assert extracted.status == ContentStatus.OK
    assert extracted.text_chunks == ["ФИО: Иванов Иван Иванович", "Телефон: +7 999 123-45-67"]


def test_legacy_doc_extractor_returns_unsupported_when_textutil_missing(tmp_path: Path, monkeypatch) -> None:
    config = load_config("configs/default.yaml")
    file_path = tmp_path / "legacy.doc"
    file_path.write_bytes(b"doc")

    monkeypatch.setattr(
        "pdn_scanner.extractors.office_legacy.extract_text_with_textutil",
        lambda path, input_format, max_chunks: TextutilExtractionResult(
            chunks=[],
            warnings=["textutil is not available on this system"],
            available=False,
        ),
    )

    extractor = LegacyOfficeExtractor()
    descriptor = FileDescriptor(
        path=str(file_path),
        rel_path="legacy.doc",
        size_bytes=file_path.stat().st_size,
        extension=".doc",
        detected_format=FileFormat.DOC,
    )

    extracted = extractor.extract(descriptor, config)

    assert extracted.status == ContentStatus.UNSUPPORTED
    assert extracted.warnings == ["textutil is not available on this system"]
