from __future__ import annotations

from pathlib import Path

import orjson

from pdn_scanner.config import AppConfig
from pdn_scanner.models import FileScanResult, RunSummary


def write_json_report(output_dir: Path, summary: RunSummary, results: list[FileScanResult], config: AppConfig) -> Path:
    output_path = output_dir / config.reporting.json_report_name
    payload = {
        "summary": summary.model_dump(mode="json"),
        "files": [
            result.model_dump(
                mode="json",
                exclude={
                    "extraction": {"text_chunks"},
                },
            )
            for result in results
        ],
    }
    output_path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))
    return output_path
