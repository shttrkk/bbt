from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote

from PIL import Image, ImageFilter, ImageOps

from pdn_scanner.config import AppConfig

OCR_RENDER_DPI = 200
OCR_TIMEOUT_SECONDS = 20
OCR_MAX_EDGE_PX = 2500
OCR_BINARIZE_THRESHOLD = 170
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
    "scan",
    "скан",
    "curriculum vitae",
    "resume",
    "cv",
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

    if suffix in {".tif", ".tiff"}:
        return True

    if suffix in {".jpg", ".jpeg", ".png", ".bmp"} and any(
        marker in normalized for marker in ("архив сканы", "scan", "скан", "passport", "паспорт")
    ):
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
    available = available_tesseract_languages()
    if not available:
        return OCRExecutionResult(text="", language="", warnings=["OCR unavailable: tesseract not found"])

    warnings: list[str] = []
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

    language = "+".join(selected)
    prepared = _prepare_image_for_ocr(image, min_edge_px=config.ocr.min_image_edge_px)
    candidates: list[tuple[float, OCRExecutionResult, str, int]] = []
    for variant_name, variant in _prepare_ocr_variants(prepared):
        for variant_psm in _psm_sequence(psm):
            candidate = _run_tesseract_once(variant, language=language, psm=variant_psm)
            score = _score_ocr_text(candidate.text)
            candidates.append((score, candidate, variant_name, variant_psm))

    if not candidates:
        return OCRExecutionResult(text="", language=language, warnings=warnings)

    best_score, best_candidate, best_variant, best_psm = max(
        candidates,
        key=lambda item: (item[0], len(item[1].text)),
    )
    merged_warnings = [*warnings, *best_candidate.warnings]
    if best_score > 0 and (best_variant != "base" or best_psm != psm):
        merged_warnings.append(f"OCR selected best variant '{best_variant}' with psm={best_psm}")

    return OCRExecutionResult(
        text=best_candidate.text,
        language=best_candidate.language,
        warnings=sorted(set(merged_warnings)),
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


def _prepare_ocr_variants(image: Image.Image) -> list[tuple[str, Image.Image]]:
    return [
        ("base", image),
        ("binary", image.point(lambda value: 255 if value >= OCR_BINARIZE_THRESHOLD else 0)),
        ("sharpen", image.filter(ImageFilter.SHARPEN)),
    ]


def _psm_sequence(psm: int) -> tuple[int, ...]:
    variants = [psm]
    for fallback in (11, 4):
        if fallback not in variants:
            variants.append(fallback)
    return tuple(variants)


def _run_tesseract_once(image: Image.Image, *, language: str, psm: int) -> OCRExecutionResult:
    warnings: list[str] = []
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        image.save(tmp.name)
        try:
            proc = subprocess.run(
                ["tesseract", tmp.name, "stdout", "-l", language, "--psm", str(psm)],
                capture_output=True,
                text=True,
                timeout=OCR_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            warnings.append(f"OCR timed out after {OCR_TIMEOUT_SECONDS}s")
            return OCRExecutionResult(text="", language=language, warnings=warnings)

    if proc.returncode != 0:
        error_text = (proc.stderr or "").strip() or "unknown tesseract error"
        warnings.append(f"OCR failed: {error_text}")
        return OCRExecutionResult(text="", language=language, warnings=warnings)

    return OCRExecutionResult(
        text=" ".join(proc.stdout.split()),
        language=language,
        warnings=warnings,
    )


def _score_ocr_text(text: str) -> float:
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return -1.0

    tokens = [token.strip(".,:;()[]{}<>\"'") for token in normalized.split()]
    alpha_chars = sum(char.isalpha() for char in normalized)
    digit_chars = sum(char.isdigit() for char in normalized)
    good_tokens = 0
    noisy_tokens = 0
    for token in tokens:
        alpha_in_token = sum(char.isalpha() for char in token)
        digit_in_token = sum(char.isdigit() for char in token)
        if alpha_in_token >= 3 or digit_in_token >= 5:
            good_tokens += 1
        if alpha_in_token and digit_in_token:
            noisy_tokens += 1

    return (
        good_tokens * 6
        + min(len(tokens), 40)
        + alpha_chars * 0.03
        + digit_chars * 0.08
        - noisy_tokens * 1.5
    )


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
