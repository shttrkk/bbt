from __future__ import annotations

from pathlib import Path

from pdn_scanner.config import load_config
from pdn_scanner.enums import ContentStatus, FileFormat
from pdn_scanner.extractors.pdf import (
    PDFExtractor,
    PageExtractionResult,
    _classify_page,
    _compute_text_metrics,
    _select_best_page_result,
)
from pdn_scanner.models import FileDescriptor


def _write_simple_pdf(path: Path, pages: list[str]) -> None:
    objects: list[str] = []
    page_ids: list[int] = []
    content_ids: list[int] = []

    def add_object(body: str) -> int:
        objects.append(body)
        return len(objects)

    font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    pages_root_id = add_object("<< /Type /Pages /Kids [] /Count 0 >>")

    for text in pages:
        escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 50 150 Td ({escaped_text}) Tj ET"
        content_id = add_object(f"<< /Length {len(stream.encode('utf-8'))} >>\nstream\n{stream}\nendstream")
        page_id = add_object(
            f"<< /Type /Page /Parent {pages_root_id} 0 R /MediaBox [0 0 300 300] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
        content_ids.append(content_id)
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_root_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>"
    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_root_id} 0 R >>")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n{body}\nendobj\n".encode("utf-8"))

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("utf-8"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("utf-8"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("utf-8")
    )
    path.write_bytes(bytes(pdf))


def test_pdf_quality_metrics_classify_good_and_suspicious() -> None:
    good_metrics = _compute_text_metrics("Иванов Иван Иванович Телефон +7 999 123-45-67 Email ivanov@example.com")
    suspicious_metrics = _compute_text_metrics("A1 B2 C3")
    empty_metrics = _compute_text_metrics("")

    assert _classify_page(good_metrics) == "good"
    assert _classify_page(suspicious_metrics) == "suspicious"
    assert _classify_page(empty_metrics) == "empty"


def test_pdf_extractor_collects_page_metadata(tmp_path: Path) -> None:
    config = load_config("configs/default.yaml")
    file_path = tmp_path / "sample.pdf"
    _write_simple_pdf(file_path, ["Customer John Smith Phone +7 999 123-45-67", ""])

    extractor = PDFExtractor()
    descriptor = FileDescriptor(
        path=str(file_path),
        rel_path="sample.pdf",
        size_bytes=file_path.stat().st_size,
        extension=".pdf",
        detected_format=FileFormat.PDF,
    )

    extracted = extractor.extract(descriptor, config)

    assert extracted.status == ContentStatus.OK
    assert extracted.pages_scanned == 2
    assert len(extracted.text_chunks) == 2
    assert extracted.metadata["pdf_summary"]["page_count"] == 2
    assert (
        extracted.metadata["pdf_summary"]["status_counts"]["good"]
        + extracted.metadata["pdf_summary"]["status_counts"]["suspicious"]
    ) >= 1
    assert extracted.metadata["pdf_summary"]["status_counts"]["empty"] >= 1
    assert extracted.metadata["pdf_summary"]["has_selective_ocr_candidates"] is True
    assert extracted.metadata["pdf_summary"]["fallback_attempted_pages"] >= 1


def test_pdf_precheck_skips_html_masquerading_as_pdf(tmp_path: Path) -> None:
    config = load_config("configs/default.yaml")
    file_path = tmp_path / "fake.pdf"
    file_path.write_text("<!DOCTYPE html><html><body>403 Forbidden</body></html>", encoding="utf-8")

    extractor = PDFExtractor()
    descriptor = FileDescriptor(
        path=str(file_path),
        rel_path="fake.pdf",
        size_bytes=file_path.stat().st_size,
        extension=".pdf",
        detected_format=FileFormat.PDF,
    )

    extracted = extractor.extract(descriptor, config)

    assert extracted.status == ContentStatus.EMPTY
    assert extracted.text_chunks == []
    assert extracted.pages_scanned == 0
    assert extracted.metadata["pdf_summary"]["signature_precheck"] == "html"
    assert extracted.metadata["page_extraction"] == []


def test_select_best_page_result_prefers_higher_quality_fallback() -> None:
    primary = PageExtractionResult(
        page_number=1,
        backend="pypdf",
        text="A1 B2 C3",
        status="suspicious",
        score=0.21,
        length=8,
        printable_ratio=1.0,
        alpha_ratio=0.5,
        word_count=3,
        avg_token_length=2.0,
    )
    fallback = PageExtractionResult(
        page_number=1,
        backend="pdfplumber",
        text="Иванов Иван Иванович Телефон +7 999 123-45-67",
        status="good",
        score=0.72,
        length=46,
        printable_ratio=1.0,
        alpha_ratio=0.78,
        word_count=7,
        avg_token_length=5.14,
    )

    selected = _select_best_page_result([primary, fallback])

    assert selected.backend == "pdfplumber"
    assert selected.status == "good"


def test_pdf_extractor_uses_ocr_for_empty_page_when_enabled(tmp_path: Path, monkeypatch) -> None:
    config = load_config("configs/ocr.yaml")
    config.ocr.max_pages_per_file = 1
    file_path = tmp_path / "blank.pdf"
    _write_simple_pdf(file_path, [""])

    monkeypatch.setattr(
        "pdn_scanner.extractors.pdf._extract_page_with_ocr",
        lambda document, page_index, config: PageExtractionResult(
            page_number=page_index + 1,
            backend="ocr",
            text="ИНН 500100732259 Телефон +7 910 245-63-18",
            status="good",
            score=0.9,
            length=40,
            printable_ratio=1.0,
            alpha_ratio=0.5,
            word_count=4,
            avg_token_length=5.0,
        ),
    )

    extractor = PDFExtractor()
    descriptor = FileDescriptor(
        path=str(file_path),
        rel_path="forms/anketa_blank.pdf",
        size_bytes=file_path.stat().st_size,
        extension=".pdf",
        detected_format=FileFormat.PDF,
    )

    extracted = extractor.extract(descriptor, config)

    assert extracted.status == ContentStatus.OK
    assert extracted.metadata["ocr_used"] is True
    assert extracted.metadata["pdf_summary"]["ocr_attempted_pages"] == 1
    assert extracted.metadata["pdf_summary"]["ocr_selected_pages"] == 1
    assert extracted.metadata["pdf_summary"]["ocr_shortlisted"] is True
