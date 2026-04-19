from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from pypdf import PdfReader
from PIL import Image

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ContentStatus, FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor

from .base import BaseExtractor
from .ocr import OCR_RENDER_DPI, run_tesseract_ocr, should_attempt_pdf_ocr

TOKEN_RE = re.compile(r"\b[\w-]+\b", flags=re.UNICODE)
PDF_SIGNATURE_PREFIX = b"%PDF-"
PDF_PRECHECK_READ_BYTES = 1024
PDF_LEADING_TRIM = b"\x00\t\r\n\f "
HTMLISH_SIGNATURES = (
    b"<!doctype html",
    b"<!doctype",
    b"<!doc",
    b"<html",
    b"<?xml",
    b"<svg",
    b"<h1>",
)


@dataclass(slots=True)
class PageExtractionResult:
    page_number: int
    backend: str
    text: str
    status: str
    score: float
    length: int
    printable_ratio: float
    alpha_ratio: float
    word_count: int
    avg_token_length: float
    error: str | None = None


class PDFExtractor(BaseExtractor):
    formats = (FileFormat.PDF,)
    name = "pdf"

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        path = Path(file_descriptor.path)
        signature = _probe_pdf_signature(path)
        if not signature.is_pdf:
            return ExtractedContent(
                file_path=file_descriptor.path,
                status=ContentStatus.EMPTY,
                text_chunks=[],
                pages_scanned=0,
                warnings=[],
                metadata=_build_precheck_only_metadata(signature.kind),
            )

        try:
            page_results, metadata, warnings = _extract_pdf_pages(path, file_descriptor.rel_path, config)
        except Exception as exc:
            return ExtractedContent(
                file_path=file_descriptor.path,
                status=ContentStatus.ERROR,
                text_chunks=[],
                warnings=[f"PDF extraction failed: {exc}"],
                metadata={"extractor": self.name},
            )

        page_texts = [result.text for result in page_results]
        non_empty_pages = sum(1 for result in page_results if result.status in {"good", "suspicious"} and result.text.strip())
        error_pages = sum(1 for result in page_results if result.status == "error")

        if not page_results or non_empty_pages == 0:
            status = ContentStatus.EMPTY
        elif error_pages > 0:
            status = ContentStatus.PARTIAL
        else:
            status = ContentStatus.OK

        metadata["extractor"] = self.name
        return ExtractedContent(
            file_path=file_descriptor.path,
            status=status,
            text_chunks=page_texts,
            pages_scanned=len(page_results),
            warnings=warnings,
            metadata=metadata,
        )


def _extract_pdf_pages(path: Path, rel_path: str, config: AppConfig) -> tuple[list[PageExtractionResult], dict, list[str]]:
    warnings: list[str] = []
    page_results: list[PageExtractionResult] = []
    page_metadata: list[dict] = []
    status_counts = {"good": 0, "suspicious": 0, "empty": 0, "error": 0}
    ocr_candidate_pages: list[int] = []
    fallback_attempted_pages = 0
    fallback_selected_pages = 0
    ocr_attempted_pages = 0
    ocr_selected_pages = 0

    primary_reader = PdfReader(str(path))
    page_count = min(len(primary_reader.pages), config.detection.max_text_chunks_per_file)
    ocr_shortlisted = should_attempt_pdf_ocr(rel_path, config, page_count=page_count)
    fallback_doc: pdfplumber.PDF | None = None

    try:
        for page_index in range(page_count):
            candidates: list[PageExtractionResult] = []
            fallback_attempted = False

            primary_candidate = _extract_page_with_pypdf(primary_reader, page_index)
            candidates.append(primary_candidate)

            if primary_candidate.status in {"empty", "suspicious", "error"}:
                fallback_attempted = True
                fallback_attempted_pages += 1
                if fallback_doc is None:
                    fallback_doc = pdfplumber.open(str(path))
                fallback_candidate = _extract_page_with_pdfplumber(fallback_doc, page_index)
                candidates.append(fallback_candidate)

            ocr_attempted = False
            if (
                ocr_shortlisted
                and len([candidate for candidate in candidates if candidate.status in {"empty", "suspicious", "error"}]) == len(candidates)
                and ocr_attempted_pages < config.ocr.max_pages_per_file
            ):
                if fallback_doc is None:
                    fallback_doc = pdfplumber.open(str(path))
                ocr_attempted = True
                ocr_attempted_pages += 1
                candidates.append(_extract_page_with_ocr(fallback_doc, page_index, config))

            selected = _select_best_page_result(candidates)
            page_results.append(selected)
            status_counts[selected.status] += 1
            if selected.backend == "pdfplumber" and selected.error is None:
                fallback_selected_pages += 1
            if selected.backend == "ocr" and selected.error is None:
                ocr_selected_pages += 1
            if selected.status in {"empty", "suspicious"}:
                ocr_candidate_pages.append(selected.page_number)

            page_metadata.append(
                {
                    "page_number": selected.page_number,
                    "selected_backend": selected.backend,
                    "selected_status": selected.status,
                    "selected_score": round(selected.score, 4),
                    "length": selected.length,
                    "printable_ratio": round(selected.printable_ratio, 4),
                    "alpha_ratio": round(selected.alpha_ratio, 4),
                    "word_count": selected.word_count,
                    "avg_token_length": round(selected.avg_token_length, 4),
                    "fallback_attempted": fallback_attempted,
                    "ocr_attempted": ocr_attempted,
                    "backends": [
                        {
                            "backend": candidate.backend,
                            "status": candidate.status,
                            "score": round(candidate.score, 4),
                            "length": candidate.length,
                            "word_count": candidate.word_count,
                            "error": candidate.error,
                        }
                        for candidate in candidates
                    ],
                }
            )

        metadata = {
            "pdf_summary": {
                "page_count": page_count,
                "status_counts": status_counts,
                "fallback_attempted_pages": fallback_attempted_pages,
                "fallback_selected_pages": fallback_selected_pages,
                "ocr_attempted_pages": ocr_attempted_pages,
                "ocr_selected_pages": ocr_selected_pages,
                "ocr_candidate_pages": ocr_candidate_pages,
                "has_selective_ocr_candidates": bool(ocr_candidate_pages),
                "signature_precheck": "passed",
                "ocr_enabled": config.feature_flags.enable_ocr,
                "ocr_shortlisted": ocr_shortlisted,
            },
            "page_extraction": page_metadata,
            "ocr_used": ocr_selected_pages > 0,
        }

        if ocr_candidate_pages:
            warnings.append(f"Selective OCR may help on pages: {','.join(map(str, ocr_candidate_pages[:20]))}")

        return page_results, metadata, warnings
    finally:
        if fallback_doc is not None:
            fallback_doc.close()


@dataclass(slots=True)
class PDFSignatureProbe:
    is_pdf: bool
    kind: str


def _probe_pdf_signature(path: Path) -> PDFSignatureProbe:
    head = path.read_bytes()[:PDF_PRECHECK_READ_BYTES]
    if not head:
        return PDFSignatureProbe(is_pdf=False, kind="empty_file")

    stripped = head.lstrip(PDF_LEADING_TRIM)
    if stripped.startswith(PDF_SIGNATURE_PREFIX):
        return PDFSignatureProbe(is_pdf=True, kind="pdf")

    lowered = stripped[:128].lower()
    if stripped.startswith((b"{", b"[")):
        return PDFSignatureProbe(is_pdf=False, kind="json")
    if any(lowered.startswith(prefix) for prefix in HTMLISH_SIGNATURES):
        return PDFSignatureProbe(is_pdf=False, kind="html")

    return PDFSignatureProbe(is_pdf=False, kind="non_pdf")


def _build_precheck_only_metadata(signature_kind: str) -> dict:
    return {
        "extractor": PDFExtractor.name,
        "pdf_summary": {
            "page_count": 0,
            "status_counts": {"good": 0, "suspicious": 0, "empty": 0, "error": 0},
            "fallback_attempted_pages": 0,
            "fallback_selected_pages": 0,
            "ocr_attempted_pages": 0,
            "ocr_selected_pages": 0,
            "ocr_candidate_pages": [],
            "has_selective_ocr_candidates": False,
            "signature_precheck": signature_kind,
            "ocr_enabled": False,
            "ocr_shortlisted": False,
        },
        "page_extraction": [],
        "ocr_used": False,
    }


def _extract_page_with_pypdf(reader: PdfReader, page_index: int) -> PageExtractionResult:
    try:
        text = reader.pages[page_index].extract_text() or ""
        return _evaluate_page_text(page_index + 1, "pypdf", text)
    except Exception as exc:
        return _error_page_result(page_index + 1, "pypdf", exc)


def _extract_page_with_pdfplumber(document: pdfplumber.PDF, page_index: int) -> PageExtractionResult:
    try:
        text = document.pages[page_index].extract_text() or ""
        return _evaluate_page_text(page_index + 1, "pdfplumber", text)
    except Exception as exc:
        return _error_page_result(page_index + 1, "pdfplumber", exc)


def _extract_page_with_ocr(document: pdfplumber.PDF, page_index: int, config: AppConfig) -> PageExtractionResult:
    try:
        image = _render_pdf_page_image(document, page_index)
        result = run_tesseract_ocr(image, config)
        candidate = _evaluate_page_text(page_index + 1, "ocr", result.text)
        if result.warnings:
            candidate.error = "; ".join(result.warnings)
        return candidate
    except Exception as exc:
        return _error_page_result(page_index + 1, "ocr", exc)


def _render_pdf_page_image(document: pdfplumber.PDF, page_index: int) -> Image.Image:
    page_image = document.pages[page_index].to_image(resolution=OCR_RENDER_DPI)
    return page_image.original


def _evaluate_page_text(page_number: int, backend: str, text: str) -> PageExtractionResult:
    normalized = " ".join(text.split())
    metrics = _compute_text_metrics(normalized)
    status = _classify_page(metrics)
    return PageExtractionResult(
        page_number=page_number,
        backend=backend,
        text=normalized,
        status=status,
        score=metrics["score"],
        length=metrics["length"],
        printable_ratio=metrics["printable_ratio"],
        alpha_ratio=metrics["alpha_ratio"],
        word_count=metrics["word_count"],
        avg_token_length=metrics["avg_token_length"],
    )


def _error_page_result(page_number: int, backend: str, exc: Exception) -> PageExtractionResult:
    return PageExtractionResult(
        page_number=page_number,
        backend=backend,
        text="",
        status="error",
        score=0.0,
        length=0,
        printable_ratio=0.0,
        alpha_ratio=0.0,
        word_count=0,
        avg_token_length=0.0,
        error=str(exc),
    )


def _compute_text_metrics(text: str) -> dict[str, float | int]:
    length = len(text)
    if length == 0:
        return {
            "length": 0,
            "printable_ratio": 0.0,
            "alpha_ratio": 0.0,
            "word_count": 0,
            "avg_token_length": 0.0,
            "score": 0.0,
        }

    printable_chars = sum(1 for char in text if char.isprintable() or char.isspace())
    visible_chars = sum(1 for char in text if not char.isspace()) or 1
    alpha_chars = sum(1 for char in text if char.isalpha())
    tokens = TOKEN_RE.findall(text)
    token_lengths = [len(token) for token in tokens]
    word_count = len(tokens)
    avg_token_length = (sum(token_lengths) / word_count) if word_count else 0.0
    printable_ratio = printable_chars / length
    alpha_ratio = alpha_chars / visible_chars

    token_shape_score = 1.0
    if word_count == 0:
        token_shape_score = 0.0
    elif avg_token_length < 2:
        token_shape_score = avg_token_length / 2
    elif avg_token_length > 15:
        token_shape_score = max(0.0, 1 - ((avg_token_length - 15) / 15))

    score = (
        min(length / 1200, 1.0) * 0.3
        + printable_ratio * 0.2
        + alpha_ratio * 0.2
        + min(word_count / 120, 1.0) * 0.2
        + token_shape_score * 0.1
    )

    return {
        "length": length,
        "printable_ratio": printable_ratio,
        "alpha_ratio": alpha_ratio,
        "word_count": word_count,
        "avg_token_length": avg_token_length,
        "score": score,
    }


def _classify_page(metrics: dict[str, float | int]) -> str:
    if metrics["length"] == 0:
        return "empty"

    if metrics["word_count"] == 0:
        return "empty"

    if (
        metrics["score"] >= 0.45
        and metrics["printable_ratio"] >= 0.85
        and metrics["alpha_ratio"] >= 0.3
        and metrics["word_count"] >= 5
        and 2 <= metrics["avg_token_length"] <= 15
    ):
        return "good"

    return "suspicious"


def _select_best_page_result(candidates: list[PageExtractionResult]) -> PageExtractionResult:
    status_rank = {"good": 3, "suspicious": 2, "empty": 1, "error": 0}
    return max(
        candidates,
        key=lambda item: (
            status_rank.get(item.status, 0),
            item.score,
            item.word_count,
            item.length,
            1 if item.backend == "pypdf" else 0,
        ),
    )
