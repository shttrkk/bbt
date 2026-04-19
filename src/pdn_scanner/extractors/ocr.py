from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote

from PIL import Image, ImageOps

from pdn_scanner.config import AppConfig

OCR_RENDER_DPI = 200
OCR_TIMEOUT_SECONDS = 20
OCR_MAX_EDGE_PX = 2500
OCR_SHORTLIST_MARKERS = (
    "anket",
    "anketa",
    "анкет",
    "zayav",
    "заяв",
    "soglas",
    "соглас",
    "passport",
    "паспорт",
    "snils",
    "снилс",
    "dms",
    "дмс",
    "dover",
    "довер",
    "raspis",
    "расписк",
    "propusk",
    "пропуск",
    "dostav",
    "достав",
    "kurier",
    "курьер",
    "kadry",
    "кадр",
    "личн",
    "consent",
    "questionnaire",
    "home_office",
)
OCR_PUBLIC_SKIP_MARKERS = (
    "выгрузки/сайты",
    "документы партнеров",
    "privacy",
    "policy",
    "terms",
    "cookies",
    "report",
    "отчет",
    "отчёт",
    "protocol",
    "протокол",
    "реестр",
    "реестров",
    "выписка",
    "mediakit",
    "медиакит",
    "brochure",
    "presentation",
    "license",
    "лиценз",
    "аккредит",
    "rules",
    "правила",
)


@dataclass(slots=True)
class OCRExecutionResult:
    text: str
    language: str
    warnings: list[str]


def should_attempt_pdf_ocr(rel_path: str | Path, config: AppConfig, *, page_count: int) -> bool:
    if not config.feature_flags.enable_ocr:
        return False

    mode = config.ocr.mode.lower()
    if mode == "off":
        return False
    if mode in {"force", "full"}:
        return True

    normalized = _normalized_rel_path(rel_path)
    if _matches_any_pattern(normalized, [*OCR_PUBLIC_SKIP_MARKERS, *config.ocr.skip_path_contains]):
        return False

    if _matches_shortlist(normalized, config):
        return True

    return config.ocr.auto_pdf_page_limit > 0 and page_count <= config.ocr.auto_pdf_page_limit


def should_attempt_image_ocr(rel_path: str | Path, config: AppConfig) -> bool:
    if not config.feature_flags.enable_ocr:
        return False

    mode = config.ocr.mode.lower()
    if mode == "off":
        return False
    if mode in {"force", "full"}:
        return True

    normalized = _normalized_rel_path(rel_path)
    suffix = Path(str(rel_path)).suffix.lower()

    if _matches_any_pattern(normalized, [*OCR_PUBLIC_SKIP_MARKERS, *config.ocr.skip_path_contains]):
        return False

    if _matches_shortlist(normalized, config):
        return True

    if suffix in {".tif", ".tiff"} and "архив сканы" in normalized:
        return True

    return False


@lru_cache(maxsize=1)
def available_tesseract_languages() -> set[str]:
    try:
        proc = subprocess.run(
            ["tesseract", "--list-langs"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return set()

    languages: set[str] = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("List of available languages"):
            continue
        languages.add(line)
    return languages


def run_tesseract_ocr(image: Image.Image, config: AppConfig, *, psm: int = 6) -> OCRExecutionResult:
    warnings: list[str] = []
    available = available_tesseract_languages()
    if not available:
        return OCRExecutionResult(text="", language="", warnings=["OCR unavailable: tesseract not found"])

    requested = [part.strip() for part in config.ocr.language.split("+") if part.strip()]
    selected = [language for language in requested if language in available]
    if not selected:
        fallback = "eng" if "eng" in available else next(iter(sorted(available)), "")
        if not fallback:
            return OCRExecutionResult(text="", language="", warnings=["OCR unavailable: no tesseract languages available"])
        warnings.append(f"OCR languages unavailable for requested set '{config.ocr.language}', fallback='{fallback}'")
        selected = [fallback]
    elif len(selected) != len(requested):
        warnings.append(
            f"OCR partial language match for requested set '{config.ocr.language}', used='{'+'.join(selected)}'"
        )

    prepared = _prepare_image_for_ocr(image, min_edge_px=config.ocr.min_image_edge_px)
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        prepared.save(tmp.name)
        try:
            proc = subprocess.run(
                ["tesseract", tmp.name, "stdout", "-l", "+".join(selected), "--psm", str(psm)],
                capture_output=True,
                text=True,
                timeout=OCR_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            warnings.append(f"OCR timed out after {OCR_TIMEOUT_SECONDS}s")
            return OCRExecutionResult(text="", language="+".join(selected), warnings=warnings)

    if proc.returncode != 0:
        error_text = (proc.stderr or "").strip() or "unknown tesseract error"
        warnings.append(f"OCR failed: {error_text}")
        return OCRExecutionResult(text="", language="+".join(selected), warnings=warnings)

    return OCRExecutionResult(
        text=" ".join(proc.stdout.split()),
        language="+".join(selected),
        warnings=warnings,
    )


def _prepare_image_for_ocr(image: Image.Image, *, min_edge_px: int) -> Image.Image:
    prepared = ImageOps.exif_transpose(image)
    if prepared.mode in {"P", "RGBA", "LA"}:
        prepared = prepared.convert("RGBA").convert("RGB")
    else:
        prepared = prepared.convert("RGB")
    prepared = prepared.convert("L")
    prepared = ImageOps.autocontrast(prepared)

    max_edge = max(prepared.size)
    if max_edge > OCR_MAX_EDGE_PX:
        scale = OCR_MAX_EDGE_PX / max_edge
        new_size = (
            max(1, round(prepared.size[0] * scale)),
            max(1, round(prepared.size[1] * scale)),
        )
        prepared = prepared.resize(new_size, Image.Resampling.LANCZOS)
        max_edge = max(prepared.size)

    if max_edge < min_edge_px and max_edge > 0:
        scale = min_edge_px / max_edge
        new_size = (
            max(1, round(prepared.size[0] * scale)),
            max(1, round(prepared.size[1] * scale)),
        )
        prepared = prepared.resize(new_size, Image.Resampling.LANCZOS)

    return prepared


def _normalized_rel_path(rel_path: str | Path) -> str:
    return unquote(str(rel_path)).replace("\\", "/").lower()


def _matches_shortlist(normalized_rel_path: str, config: AppConfig) -> bool:
    patterns = [
        *OCR_SHORTLIST_MARKERS,
        *_normalized_patterns(config.ocr.shortlist_path_contains),
        *_manifest_patterns(config.ocr.shortlist_manifest_path),
    ]
    return _matches_any_pattern(normalized_rel_path, patterns)


def _matches_any_pattern(normalized_rel_path: str, patterns: list[str] | tuple[str, ...]) -> bool:
    return any(pattern and pattern in normalized_rel_path for pattern in patterns)


def _normalized_patterns(patterns: list[str]) -> list[str]:
    return [_normalized_rel_path(pattern) for pattern in patterns if pattern.strip()]


@lru_cache(maxsize=16)
def _manifest_patterns(manifest_path: str | None) -> tuple[str, ...]:
    if not manifest_path:
        return ()

    path = Path(manifest_path)
    if not path.exists():
        return ()

    patterns: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        patterns.append(_normalized_rel_path(stripped))
    return tuple(patterns)
