from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import typer

from pdn_scanner.classify import UZClassifier
from pdn_scanner.config import load_config, validate_config
from pdn_scanner.detectors import DetectionEngine
from pdn_scanner.enums import ContentStatus, ValidationStatus
from pdn_scanner.models import ExtractedContent, FileDescriptor, FileScanResult, RunSummary
from pdn_scanner.quality import QualityLayer
from pdn_scanner.reporting import write_json_report, write_markdown_report, write_result_csv, write_summary_csv
from pdn_scanner.runtime import ScanMetrics, setup_logging, to_processing_error
from pdn_scanner.scanner import ExtractorDispatcher, detect_format, walk_directory
from pdn_scanner.submission import apply_cross_file_promotion
from pdn_scanner.version import __version__

app = typer.Typer(help="Privacy-safe CLI scanner for personal data discovery.")
logger = logging.getLogger(__name__)


@app.command()
def version() -> None:
    typer.echo(__version__)


@app.command("validate-config")
def validate_config_command(config_path: Path) -> None:
    config = validate_config(config_path)
    typer.echo(f"Config is valid: {config_path}")
    typer.echo(f"Supported formats: {', '.join(config.supported_formats)}")


@app.command()
def scan(
    input_dir: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, readable=True),
    out: Path = typer.Option(..., "--out", help="Output directory for reports."),
    config: Path = typer.Option(Path("configs/default.yaml"), "--config", help="Path to YAML config."),
) -> None:
    started_at = datetime.now(timezone.utc)
    run_id = uuid4().hex[:12]
    cfg = load_config(config)
    setup_logging(cfg)

    out.mkdir(parents=True, exist_ok=True)
    logger.info("Run %s started. input=%s output=%s", run_id, input_dir, out)

    descriptors, walker_errors = walk_directory(input_dir, cfg)
    dispatcher = ExtractorDispatcher()
    engine = DetectionEngine(cfg)
    classifier = UZClassifier(cfg)
    quality_layer = QualityLayer(cfg)
    metrics = ScanMetrics()
    metrics.extend_errors(walker_errors)

    results: list[FileScanResult] = []

    for descriptor in descriptors:
        try:
            results.append(_process_file(descriptor, cfg, dispatcher, engine, classifier, quality_layer))
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            error_result = _build_error_result(descriptor, exc)
            results.append(error_result)
            if not cfg.scan.continue_on_error:
                raise typer.Exit(code=1) from exc

    results = apply_cross_file_promotion(results, cfg)

    for result in results:
        metrics.record_file_result(result)

    finished_at = datetime.now(timezone.utc)
    summary = RunSummary(
        run_id=run_id,
        version=__version__,
        started_at=started_at,
        finished_at=finished_at,
        input_dir=str(input_dir),
        output_dir=str(out),
        config_path=str(config),
        files_discovered=len(descriptors),
        files_processed=len(results),
        files_with_detections=metrics.files_with_detections,
        files_with_errors=metrics.files_with_errors,
        skipped_files=max(0, len(descriptors) - len(results)),
        totals_by_format=dict(metrics.totals_by_format),
        totals_by_uz=dict(metrics.totals_by_uz),
        totals_by_category=dict(metrics.totals_by_category),
        errors=metrics.errors,
        duration_seconds=(finished_at - started_at).total_seconds(),
        notes=[
            "reports exclude raw PII",
            "OCR is not part of the v0.1.1 default execution path",
        ],
    )

    artifacts: dict[str, str] = {}
    if cfg.reporting.create_csv:
        artifacts["summary_csv"] = str(write_summary_csv(out, summary, results, cfg))
        artifacts["result_csv"] = str(write_result_csv(out, results, cfg))
    summary.artifacts = artifacts

    if cfg.reporting.create_json:
        artifacts["report_json"] = str(write_json_report(out, summary, results, cfg))
    if cfg.reporting.create_markdown:
        artifacts["report_md"] = str(write_markdown_report(out, summary, results, cfg))
    summary.artifacts = artifacts

    logger.info(
        "Run %s completed. files=%s detections=%s errors=%s",
        run_id,
        summary.files_processed,
        summary.files_with_detections,
        summary.files_with_errors,
    )
    typer.echo(f"Run completed: {run_id}")
    for artifact_name, artifact_path in summary.artifacts.items():
        typer.echo(f"{artifact_name}: {artifact_path}")


def _process_file(
    descriptor: FileDescriptor,
    config,
    dispatcher: ExtractorDispatcher,
    engine: DetectionEngine,
    classifier: UZClassifier,
    quality_layer: QualityLayer,
) -> FileScanResult:
    file_format, mime_type, format_warnings = detect_format(descriptor.path, config.scan.use_mime_detection)
    updated_descriptor = descriptor.model_copy(update={"detected_format": file_format, "mime_type": mime_type})
    extractor = dispatcher.get_extractor(file_format)
    extraction = extractor.extract(updated_descriptor, config)
    extraction.warnings.extend(format_warnings)

    detections = engine.detect(extraction) if extraction.status not in {ContentStatus.ERROR, ContentStatus.UNSUPPORTED} else []
    quality = quality_layer.assess(updated_descriptor, extraction, detections)
    assigned_uz, reasons, _ = classifier.classify(
        quality.detections,
        storage_class=quality.storage_class,
        primary_genre=quality.primary_genre,
        risk_score=quality.risk_score,
        justification_score=quality.justification_score,
        noise_score=quality.noise_score,
        is_template=quality.is_template,
        is_public_doc=quality.is_public_doc,
        is_reference_data=quality.is_reference_data,
        quality_reasons=quality.reasons,
    )
    errors = []
    if extraction.status == ContentStatus.ERROR:
        errors.append(
            to_processing_error(
                Exception("Extractor returned error status"),
                stage="extractor",
                path=updated_descriptor.path,
            )
        )

    return FileScanResult(
        file=updated_descriptor,
        extraction=extraction,
        detections=quality.detections,
        scan_status=_scan_status(extraction, errors),
        assigned_uz=assigned_uz,
        classification_reasons=reasons,
        storage_class=quality.storage_class,
        primary_genre=quality.primary_genre,
        genre_tags=quality.genre_tags,
        risk_score=quality.risk_score,
        justification_score=quality.justification_score,
        noise_score=quality.noise_score,
        counts_by_category=_counts_by_category(quality.detections),
        counts_by_family=_counts_by_family(quality.detections),
        validated_counts_by_category=_validated_counts_by_category(quality.detections),
        validated_entities_count=quality.validated_entities_count,
        suspicious_entities_count=quality.suspicious_entities_count,
        confidence_summary=quality.confidence_summary,
        is_template=quality.is_template,
        is_public_doc=quality.is_public_doc,
        is_reference_data=quality.is_reference_data,
        template_like=quality.is_template,
        ocr_used=bool(extraction.metadata.get("ocr_used", False)),
        errors=errors,
    )


def _build_error_result(descriptor: FileDescriptor, exc: Exception) -> FileScanResult:
    return FileScanResult(
        file=descriptor,
        extraction=ExtractedContent(
            file_path=descriptor.path,
            status=ContentStatus.ERROR,
            text_chunks=[],
            warnings=[str(exc)],
            metadata={"extractor": "runtime_guard"},
        ),
        detections=[],
        scan_status="error",
        errors=[to_processing_error(exc, stage="runtime", path=descriptor.path)],
    )


def _counts_by_category(detections) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for detection in detections:
        counter[detection.category] += detection.occurrences
    return dict(counter)


def _counts_by_family(detections) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for detection in detections:
        counter[detection.family] += detection.occurrences
    return dict(counter)


def _validated_counts_by_category(detections) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for detection in detections:
        if detection.validation_status == ValidationStatus.VALID:
            counter[detection.category] += detection.occurrences
    return dict(counter)


def _scan_status(extraction: ExtractedContent, errors: list) -> str:
    if errors or extraction.status == ContentStatus.ERROR:
        return "error"
    if extraction.status == ContentStatus.UNSUPPORTED:
        return "skipped"
    return "ok"


if __name__ == "__main__":
    app()
