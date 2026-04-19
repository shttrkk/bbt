from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from pdn_scanner.cli import app

runner = CliRunner()


def test_cli_scan_handles_empty_directory(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()

    config_path = Path(__file__).resolve().parents[2] / "configs" / "default.yaml"
    result = runner.invoke(app, ["scan", str(input_dir), "--out", str(output_dir), "--config", str(config_path)])

    assert result.exit_code == 0
    assert (output_dir / "result.csv").exists()
    assert (output_dir / "summary.csv").exists()
    assert (output_dir / "report.json").exists()
    assert (output_dir / "report.md").exists()


def test_cli_scan_generates_privacy_safe_reports(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()

    sample_file = input_dir / "person.txt"
    sample_file.write_text(
        "Email: user@example.com\n"
        "Телефон: +7 (999) 123-45-67\n"
        "СНИЛС: 112-233-445 95\n"
        "Карта: 4111 1111 1111 1111\n",
        encoding="utf-8",
    )

    config_path = Path(__file__).resolve().parents[2] / "configs" / "default.yaml"
    result = runner.invoke(app, ["scan", str(input_dir), "--out", str(output_dir), "--config", str(config_path)])

    assert result.exit_code == 0

    report_json = output_dir / "report.json"
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    serialized = json.dumps(payload, ensure_ascii=False)

    assert payload["summary"]["files_processed"] == 1
    file_result = payload["files"][0]
    assert "scan_status" in file_result
    assert "validated_entities_count" in file_result
    assert "suspicious_entities_count" in file_result
    assert "confidence_summary" in file_result
    assert "is_template" in file_result
    assert "is_public_doc" in file_result
    assert "is_reference_data" in file_result
    assert "storage_class" in file_result
    assert "primary_genre" in file_result
    assert "genre_tags" in file_result
    assert file_result["detections"]
    first_detection = file_result["detections"][0]
    assert "entity_category" in first_detection
    assert "entity_subtype" in first_detection
    assert "source_fragment" in first_detection
    assert "start_char" in first_detection
    assert "end_char" in first_detection
    assert "matches" in first_detection
    assert "user@example.com" not in serialized
    assert "112-233-445 95" not in serialized
    assert "4111 1111 1111 1111" not in serialized
