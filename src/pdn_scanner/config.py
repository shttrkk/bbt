from __future__ import annotations

from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class ScanConfig(BaseModel):
    continue_on_error: bool = True
    include_hidden: bool = False
    follow_symlinks: bool = False
    use_mime_detection: bool = True
    max_file_size_mb: int = 256
    csv_chunk_size: int = 1000
    workers: int = 1


class FeatureFlags(BaseModel):
    include_masked_samples: bool = True
    enable_sensitive_detectors: bool = False
    enable_template_heuristics: bool = True
    enable_ocr: bool = False


class DetectionConfig(BaseModel):
    context_window: int = 60
    phone_min_digits: int = 10
    phone_max_digits: int = 11
    max_text_chunks_per_file: int = 2000


class OCRConfig(BaseModel):
    mode: str = "off"
    language: str = "rus+eng"
    max_pages_per_file: int = 5
    max_images_per_file: int = 10
    min_image_edge_px: int = 800


class ReportingConfig(BaseModel):
    create_csv: bool = True
    create_json: bool = True
    create_markdown: bool = True
    summary_csv_name: str = "summary.csv"
    result_csv_name: str = "result.csv"
    json_report_name: str = "report.json"
    markdown_report_name: str = "report.md"


class MaskingConfig(BaseModel):
    enabled: bool = True
    secret_env_var: str = "PDN_MASKING_SECRET"
    default_salt: str = "local-dev-salt"
    hash_length: int = 16
    preview_prefix: int = 2
    preview_suffix: int = 2


class LoggingConfig(BaseModel):
    level: str = "INFO"
    rich_tracebacks: bool = True
    show_path: bool = False


class UZThresholds(BaseModel):
    ordinary_large_unique: int = 20
    ordinary_large_occurrences: int = 100
    ordinary_large_rows: int = 50
    government_large_unique: int = 5
    government_large_occurrences: int = 20
    government_large_rows: int = 10
    payment_large_unique: int = 3
    payment_large_occurrences: int = 5
    payment_large_rows: int = 3


class AppConfig(BaseModel):
    supported_formats: list[str] = Field(default_factory=list)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    feature_flags: FeatureFlags = Field(default_factory=FeatureFlags)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    masking: MaskingConfig = Field(default_factory=MaskingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    uz_thresholds: UZThresholds = Field(default_factory=UZThresholds)


def load_config(path: str | Path) -> AppConfig:
    load_dotenv()
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    return AppConfig.model_validate(data)


def validate_config(path: str | Path) -> AppConfig:
    return load_config(path)
