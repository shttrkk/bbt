from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageSequence

from pdn_scanner.config import AppConfig
from pdn_scanner.enums import ContentStatus, FileFormat
from pdn_scanner.models import ExtractedContent, FileDescriptor

from .base import BaseExtractor, UnsupportedExtractor
from .ocr import run_tesseract_ocr, should_attempt_image_ocr

IMAGE_PRECHECK_READ_BYTES = 128
IMAGE_SIGNATURES = (
    b"\xff\xd8\xff",
    b"\x89PNG\r\n\x1a\n",
    b"GIF87a",
    b"GIF89a",
    b"BM",
    b"II*\x00",
    b"MM\x00*",
)
HTMLISH_SIGNATURES = (b"<!doctype", b"<html", b"<?xml", b"<svg", b"<h1>")


class ImageExtractor(BaseExtractor):
    formats = (FileFormat.IMAGE,)
    name = "image"

    def __init__(self) -> None:
        self._unsupported = UnsupportedExtractor(FileFormat.IMAGE)

    def extract(self, file_descriptor: FileDescriptor, config: AppConfig) -> ExtractedContent:
        if not config.feature_flags.enable_ocr:
            content = self._unsupported.extract(file_descriptor, config)
            content.warnings.append("Image OCR is disabled by current config")
            return content

        path = Path(file_descriptor.path)
        warnings: list[str] = []
        text_chunks: list[str] = []
        frames_scanned = 0
        frames_with_text = 0
        errors = 0

        signature_kind = _probe_image_signature(path)
        if signature_kind != "image":
            return ExtractedContent(
                file_path=file_descriptor.path,
                status=ContentStatus.EMPTY,
                text_chunks=[],
                warnings=[],
                metadata={
                    "extractor": self.name,
                    "ocr_used": False,
                    "image_summary": {
                        "frames_scanned": 0,
                        "frames_with_text": 0,
                        "error_frames": 0,
                        "signature_precheck": signature_kind,
                        "ocr_shortlisted": False,
                    },
                },
            )

        shortlisted = should_attempt_image_ocr(file_descriptor.rel_path, config)
        if not shortlisted:
            return ExtractedContent(
                file_path=file_descriptor.path,
                status=ContentStatus.EMPTY,
                text_chunks=[],
                warnings=["Image OCR skipped by shortlist policy"],
                metadata={
                    "extractor": self.name,
                    "ocr_used": False,
                    "image_summary": {
                        "frames_scanned": 0,
                        "frames_with_text": 0,
                        "error_frames": 0,
                        "signature_precheck": signature_kind,
                        "ocr_shortlisted": False,
                    },
                },
            )

        try:
            with Image.open(path) as image:
                for frame in ImageSequence.Iterator(image):
                    if frames_scanned >= config.ocr.max_images_per_file:
                        warnings.append("Image OCR frame limit reached")
                        break

                    frames_scanned += 1
                    try:
                        result = run_tesseract_ocr(frame.copy(), config)
                    except Exception as exc:  # pragma: no cover - defensive runtime guard
                        warnings.append(f"Image OCR failed on frame {frames_scanned}: {exc}")
                        errors += 1
                        text_chunks.append("")
                        continue

                    warnings.extend(result.warnings)
                    text_chunks.append(result.text)
                    if result.text:
                        frames_with_text += 1
        except Exception as exc:
            return ExtractedContent(
                file_path=file_descriptor.path,
                status=ContentStatus.ERROR,
                text_chunks=[],
                warnings=[f"Image extraction failed: {exc}"],
                metadata={"extractor": self.name},
            )

        if frames_scanned == 0 or frames_with_text == 0:
            status = ContentStatus.EMPTY
        elif errors > 0:
            status = ContentStatus.PARTIAL
        else:
            status = ContentStatus.OK

        return ExtractedContent(
            file_path=file_descriptor.path,
            status=status,
            text_chunks=text_chunks,
            warnings=sorted(set(warnings)),
            metadata={
                "extractor": self.name,
                "ocr_used": True,
                "ocr_engine": "tesseract",
                "image_summary": {
                    "frames_scanned": frames_scanned,
                    "frames_with_text": frames_with_text,
                    "error_frames": errors,
                    "signature_precheck": signature_kind,
                    "ocr_shortlisted": True,
                },
            },
        )


def _probe_image_signature(path: Path) -> str:
    head = path.read_bytes()[:IMAGE_PRECHECK_READ_BYTES]
    if not head:
        return "empty_file"

    stripped = head.lstrip(b"\x00\t\r\n\f ")
    if any(stripped.startswith(signature) for signature in IMAGE_SIGNATURES):
        return "image"
    if stripped.startswith((b"{", b"[")):
        return "json"
    lowered = stripped.lower()
    if any(lowered.startswith(signature) for signature in HTMLISH_SIGNATURES):
        return "html"
    return "non_image"
