from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from pdn_scanner.config import load_config
from pdn_scanner.enums import ContentStatus
from pdn_scanner.extractors.xls import XLSExtractor
from pdn_scanner.models import FileDescriptor


def test_xlsx_extractor_reads_header_labeled_rows(tmp_path: Path) -> None:
    path = tmp_path / "contacts.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Staff"
    worksheet.append(["Фамилия, имя, отчество", "E-mail", "Телефон"])
    worksheet.append(["Иванов Иван Иванович", "ivanov@example.com", "+7 999 123-45-67"])
    workbook.save(path)
    workbook.close()

    extractor = XLSExtractor()
    config = load_config("configs/default.yaml")
    descriptor = FileDescriptor(
        path=str(path),
        rel_path=path.name,
        size_bytes=path.stat().st_size,
        extension="xlsx",
    )

    extraction = extractor.extract(descriptor, config)

    assert extraction.status == ContentStatus.OK
    assert extraction.text_chunks
    assert "ФИО: Иванов Иван Иванович" in extraction.text_chunks[0]
    assert "email: ivanov@example.com" in extraction.text_chunks[0]
    assert "телефон: +7 999 123-45-67" in extraction.text_chunks[0]


def test_html_error_page_xls_is_skipped(tmp_path: Path) -> None:
    path = tmp_path / "broken.xls"
    path.write_text(
        "<!DOCTYPE html><html><body><h1>Oops! An Error Occurred</h1><h2>404 Not Found</h2></body></html>",
        encoding="utf-8",
    )

    extractor = XLSExtractor()
    config = load_config("configs/default.yaml")
    descriptor = FileDescriptor(
        path=str(path),
        rel_path=path.name,
        size_bytes=path.stat().st_size,
        extension="xls",
    )

    extraction = extractor.extract(descriptor, config)

    assert extraction.status == ContentStatus.EMPTY
    assert extraction.text_chunks == []
