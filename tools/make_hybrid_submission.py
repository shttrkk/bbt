from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge positive files from one or more partial report.json runs into a legacy submission csv."
    )
    parser.add_argument("--report", dest="reports", action="append", required=True, help="Path to report.json")
    parser.add_argument("--out", required=True, help="Output csv path")
    parser.add_argument(
        "--added-only-against",
        dest="base_reports",
        action="append",
        default=[],
        help="Only keep positives not already present in the provided base report.json files",
    )
    return parser.parse_args()


def load_positive_paths(report_path: Path) -> dict[str, dict]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    positives: dict[str, dict] = {}
    input_dir = str(report.get("summary", {}).get("input_dir", ""))
    for item in report.get("files", []):
        if item.get("assigned_uz") == "NO_PDN":
            continue
        file_info = item["file"]
        full_path = _resolve_existing_path(report_path.parent, file_info["path"])
        key = _identity_key(input_dir, file_info)
        positives[key] = {
            "file_info": file_info,
            "path": str(full_path),
        }
    return positives


def _identity_key(input_dir: str, file_info: dict) -> str:
    raw_path = Path(file_info["path"])
    if "share" in raw_path.parts:
        share_index = raw_path.parts.index("share")
        return "/".join(raw_path.parts[share_index + 1 :])

    normalized_input_dir = input_dir.replace("\\", "/").strip("/")
    rel_path = str(file_info["rel_path"]).replace("\\", "/").strip("/")
    if normalized_input_dir == "share":
        return rel_path
    if normalized_input_dir.startswith("share/"):
        prefix = normalized_input_dir[len("share/") :].strip("/")
        return f"{prefix}/{rel_path}" if prefix else rel_path
    return rel_path


def _resolve_existing_path(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.exists():
        return path.resolve()
    resolved = (base_dir / raw_path).resolve()
    if resolved.exists():
        return resolved
    return path


def _submission_row(path: Path, fallback_size: int) -> dict[str, str | int]:
    stat = path.stat() if path.exists() else None
    size = stat.st_size if stat is not None else fallback_size
    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%b %d %H:%M").lower() if stat is not None else ""
    return {
        "size": size,
        "time": mtime,
        "name": path.name,
    }


def main() -> None:
    args = parse_args()
    positives: dict[str, dict] = {}
    for raw_report_path in args.reports:
        positives.update(load_positive_paths(Path(raw_report_path)))

    base_positive_paths: set[str] = set()
    for raw_report_path in args.base_reports:
        base_positive_paths.update(load_positive_paths(Path(raw_report_path)))

    rows = []
    for identity_key, payload in sorted(positives.items()):
        if identity_key in base_positive_paths:
            continue
        file_info = payload["file_info"]
        rows.append(_submission_row(Path(payload["path"]), fallback_size=file_info.get("size_bytes", 0)))

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["size", "time", "name"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
