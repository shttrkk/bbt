from __future__ import annotations

from pathlib import Path

from PIL import Image

from pdn_scanner.config import load_config
from pdn_scanner.enums import ContentStatus, FileFormat
from pdn_scanner.extractors.image import ImageExtractor
from pdn_scanner.extractors.ocr import OCRExecutionResult
from pdn_scanner.models import FileDescriptor


def test_image_extractor_runs_ocr_when_enabled(tmp_path: Path, monkeypatch) -> None:
    config = load_config("configs/ocr.yaml")
    image_path = tmp_path / "scan.png"
    Image.new("RGB", (800, 600), color="white").save(image_path)

    monkeypatch.setattr(
        "pdn_scanner.extractors.image.run_tesseract_ocr",
        lambda image, config: OCRExecutionResult(
            text="ФИО: Иванов Иван Иванович Телефон: +7 999 123-45-67",
            language="rus+eng",
            warnings=[],
        ),
    )

    extractor = ImageExtractor()
    descriptor = FileDescriptor(
        path=str(image_path),
        rel_path="anketa_scan.png",
        size_bytes=image_path.stat().st_size,
        extension=".png",
        detected_format=FileFormat.IMAGE,
    )

    extracted = extractor.extract(descriptor, config)

    assert extracted.status == ContentStatus.OK
    assert extracted.metadata["ocr_used"] is True
    assert extracted.metadata["image_summary"]["ocr_shortlisted"] is True
    assert extracted.text_chunks == ["ФИО: Иванов Иван Иванович Телефон: +7 999 123-45-67"]


def test_image_extractor_stays_unsupported_when_ocr_disabled(tmp_path: Path) -> None:
    config = load_config("configs/default.yaml")
    image_path = tmp_path / "scan.png"
    Image.new("RGB", (800, 600), color="white").save(image_path)

    extractor = ImageExtractor()
    descriptor = FileDescriptor(
        path=str(image_path),
        rel_path="scan.png",
        size_bytes=image_path.stat().st_size,
        extension=".png",
        detected_format=FileFormat.IMAGE,
    )

    extracted = extractor.extract(descriptor, config)

    assert extracted.status == ContentStatus.UNSUPPORTED
    assert any("disabled" in warning.lower() for warning in extracted.warnings)


def test_image_extractor_skips_html_masquerading_as_jpg(tmp_path: Path) -> None:
    config = load_config("configs/ocr.yaml")
    image_path = tmp_path / "fake.jpg"
    image_path.write_text("<!DOCTYPE html><html><body>403</body></html>", encoding="utf-8")

    extractor = ImageExtractor()
    descriptor = FileDescriptor(
        path=str(image_path),
        rel_path="fake.jpg",
        size_bytes=image_path.stat().st_size,
        extension=".jpg",
        detected_format=FileFormat.IMAGE,
    )

    extracted = extractor.extract(descriptor, config)

    assert extracted.status == ContentStatus.EMPTY
    assert extracted.metadata["image_summary"]["signature_precheck"] == "html"
