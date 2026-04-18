from __future__ import annotations

import mimetypes
from pathlib import Path

from pdn_scanner.enums import FileFormat

try:
    import magic  # type: ignore
except ImportError:  # pragma: no cover - optional dependency path
    magic = None


EXTENSION_MAP: dict[str, FileFormat] = {
    "txt": FileFormat.TXT,
    "csv": FileFormat.CSV,
    "json": FileFormat.JSON,
    "parquet": FileFormat.PARQUET,
    "pdf": FileFormat.PDF,
    "doc": FileFormat.DOC,
    "docx": FileFormat.DOCX,
    "rtf": FileFormat.RTF,
    "xls": FileFormat.XLS,
    "xlsx": FileFormat.XLS,
    "html": FileFormat.HTML,
    "htm": FileFormat.HTML,
    "jpg": FileFormat.IMAGE,
    "jpeg": FileFormat.IMAGE,
    "png": FileFormat.IMAGE,
    "gif": FileFormat.IMAGE,
    "tif": FileFormat.IMAGE,
    "tiff": FileFormat.IMAGE,
    "bmp": FileFormat.IMAGE,
    "mp4": FileFormat.VIDEO,
}

MIME_MAP: dict[str, FileFormat] = {
    "text/plain": FileFormat.TXT,
    "text/csv": FileFormat.CSV,
    "application/json": FileFormat.JSON,
    "application/pdf": FileFormat.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileFormat.DOCX,
    "application/msword": FileFormat.DOC,
    "application/rtf": FileFormat.RTF,
    "application/vnd.ms-excel": FileFormat.XLS,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileFormat.XLS,
    "text/html": FileFormat.HTML,
    "application/xhtml+xml": FileFormat.HTML,
    "image/jpeg": FileFormat.IMAGE,
    "image/png": FileFormat.IMAGE,
    "image/gif": FileFormat.IMAGE,
    "image/tiff": FileFormat.IMAGE,
    "video/mp4": FileFormat.VIDEO,
}


def detect_format(file_path: str | Path, use_mime_detection: bool = True) -> tuple[FileFormat, str | None, list[str]]:
    path = Path(file_path)
    warnings: list[str] = []
    extension = path.suffix.lower().lstrip(".")
    ext_format = EXTENSION_MAP.get(extension)

    mime_type: str | None = None
    if use_mime_detection:
        if magic is not None:
            try:
                mime_type = magic.from_file(str(path), mime=True)
            except Exception as exc:  # pragma: no cover - depends on host libmagic
                warnings.append(f"MIME detection failed: {exc}")
        else:
            warnings.append("python-magic unavailable; fallback to mimetypes/extension")

    if mime_type is None:
        mime_type, _ = mimetypes.guess_type(path.name)

    mime_format = MIME_MAP.get(mime_type or "")
    detected = ext_format or mime_format or FileFormat.UNKNOWN
    return detected, mime_type, warnings
