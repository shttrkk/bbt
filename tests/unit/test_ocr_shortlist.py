from __future__ import annotations

from pathlib import Path

from pdn_scanner.config import load_config
from pdn_scanner.extractors.ocr import should_attempt_image_ocr, should_attempt_pdf_ocr


def test_pdf_ocr_shortlist_requires_marker_or_override_in_auto_mode() -> None:
    config = load_config("configs/ocr.yaml")

    assert should_attempt_pdf_ocr("Прочее/random_doc.pdf", config, page_count=1) is True
    assert should_attempt_pdf_ocr("Прочее/random_doc.pdf", config, page_count=20) is False
    assert should_attempt_pdf_ocr("Прочее/анкета_сотрудника.pdf", config, page_count=1) is True


def test_pdf_ocr_shortlist_manifest_can_force_specific_paths(tmp_path: Path) -> None:
    config = load_config("configs/ocr.yaml")
    manifest_path = tmp_path / "ocr_shortlist.txt"
    manifest_path.write_text("Прочее/special_batch/\n", encoding="utf-8")
    config.ocr.shortlist_manifest_path = str(manifest_path)

    assert should_attempt_pdf_ocr("Прочее/special_batch/doc001.pdf", config, page_count=20) is True
    assert should_attempt_pdf_ocr("Прочее/other/doc002.pdf", config, page_count=20) is False


def test_image_ocr_shortlist_keeps_archive_tiff_and_honors_skip_patterns() -> None:
    config = load_config("configs/ocr.yaml")

    assert should_attempt_image_ocr("Архив сканы/a/zza94a00/2063196920.tif", config) is True
    assert should_attempt_image_ocr("Прочее/scanned_form.tif", config) is True
    assert should_attempt_image_ocr("Выгрузки/Сайты/public_cv.png", config) is False
