from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from pdn_scanner.config import load_config
from pdn_scanner.enums import ContentStatus, FileFormat
from pdn_scanner.extractors.docx import DOCXExtractor
from pdn_scanner.models import FileDescriptor


def _write_minimal_docx(path: Path, paragraphs: list[str]) -> None:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(f"<w:p><w:r><w:t>{paragraph}</w:t></w:r></w:p>" for paragraph in paragraphs)
        + "</w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )

    with ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document_xml)


def test_docx_extractor_reads_paragraph_text(tmp_path: Path) -> None:
    config = load_config("configs/default.yaml")
    file_path = tmp_path / "person.docx"
    _write_minimal_docx(file_path, ["ФИО: Иванов Иван Иванович", "Телефон: +7 999 123-45-67"])

    extractor = DOCXExtractor()
    descriptor = FileDescriptor(
        path=str(file_path),
        rel_path="person.docx",
        size_bytes=file_path.stat().st_size,
        extension=".docx",
        detected_format=FileFormat.DOCX,
    )

    extracted = extractor.extract(descriptor, config)

    assert extracted.status == ContentStatus.OK
    assert extracted.text_chunks == ["ФИО: Иванов Иван Иванович", "Телефон: +7 999 123-45-67"]


def test_docx_extractor_returns_empty_for_invalid_archive(tmp_path: Path) -> None:
    config = load_config("configs/default.yaml")
    file_path = tmp_path / "broken.docx"
    file_path.write_text("not-a-docx", encoding="utf-8")

    extractor = DOCXExtractor()
    descriptor = FileDescriptor(
        path=str(file_path),
        rel_path="broken.docx",
        size_bytes=file_path.stat().st_size,
        extension=".docx",
        detected_format=FileFormat.DOCX,
    )

    extracted = extractor.extract(descriptor, config)

    assert extracted.status == ContentStatus.EMPTY
