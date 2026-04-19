from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .enums import ConfidenceLevel, ContentStatus, FileFormat, StorageClass, UZLevel, ValidationStatus


class FileDescriptor(BaseModel):
    path: str
    rel_path: str
    size_bytes: int
    extension: str
    mime_type: str | None = None
    detected_format: FileFormat = FileFormat.UNKNOWN
    file_hash: str | None = None


class ExtractedContent(BaseModel):
    file_path: str
    status: ContentStatus
    text_chunks: list[str] = Field(default_factory=list)
    structured_rows_scanned: int = 0
    pages_scanned: int | None = None
    sheets_scanned: int | None = None
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DetectionMatch(BaseModel):
    chunk_index: int
    start_char: int
    end_char: int
    fragment: str


class DetectionResult(BaseModel):
    category: str
    family: str
    entity_category: str
    entity_subtype: str
    detector_id: str
    confidence: ConfidenceLevel
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    value_hash: str | None = None
    masked_preview: str | None = None
    occurrences: int = 1
    chunk_index: int | None = None
    start_char: int | None = None
    end_char: int | None = None
    source_fragment: str | None = None
    matches: list[DetectionMatch] = Field(default_factory=list)
    location_hints: list[str] = Field(default_factory=list)
    context_keywords: list[str] = Field(default_factory=list)
    raw_value: str | None = Field(default=None, exclude=True)
    normalized_value: str | None = Field(default=None, exclude=True)


class ProcessingError(BaseModel):
    code: str
    stage: str
    message: str
    path: str | None = None
    recoverable: bool = True
    details: dict[str, Any] = Field(default_factory=dict)


class FileScanResult(BaseModel):
    file: FileDescriptor
    extraction: ExtractedContent
    detections: list[DetectionResult] = Field(default_factory=list)
    scan_status: str = "ok"
    assigned_uz: UZLevel = UZLevel.NO_PDN
    classification_reasons: list[str] = Field(default_factory=list)
    storage_class: StorageClass = StorageClass.NON_TARGET
    primary_genre: str = "unknown"
    genre_tags: list[str] = Field(default_factory=list)
    risk_score: int = 0
    justification_score: int = 0
    noise_score: int = 0
    counts_by_category: dict[str, int] = Field(default_factory=dict)
    counts_by_family: dict[str, int] = Field(default_factory=dict)
    validated_counts_by_category: dict[str, int] = Field(default_factory=dict)
    validated_entities_count: int = 0
    suspicious_entities_count: int = 0
    confidence_summary: dict[str, int] = Field(default_factory=dict)
    is_template: bool = False
    is_public_doc: bool = False
    is_reference_data: bool = False
    template_like: bool = False
    ocr_used: bool = False
    errors: list[ProcessingError] = Field(default_factory=list)


class RunSummary(BaseModel):
    run_id: str
    version: str
    started_at: datetime
    finished_at: datetime
    input_dir: str
    output_dir: str
    config_path: str
    files_discovered: int = 0
    files_processed: int = 0
    files_with_detections: int = 0
    files_with_errors: int = 0
    skipped_files: int = 0
    totals_by_format: dict[str, int] = Field(default_factory=dict)
    totals_by_uz: dict[str, int] = Field(default_factory=dict)
    totals_by_category: dict[str, int] = Field(default_factory=dict)
    errors: list[ProcessingError] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
