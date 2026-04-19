from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from pdn_scanner.config import load_config
from pdn_scanner.extractors.ocr import _matches_shortlist, _normalized_rel_path, should_attempt_image_ocr, should_attempt_pdf_ocr

DOC_LIKE_SUFFIXES = {".doc", ".docx", ".rtf", ".xls", ".xlsx", ".pdf", ".txt"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Copy a shortlist corpus into a small working directory.")
    parser.add_argument("--input-dir", required=True, help="Source corpus directory")
    parser.add_argument("--config", required=True, help="Config with shortlist settings")
    parser.add_argument("--out-dir", required=True, help="Destination shortlist corpus directory")
    return parser.parse_args()


def should_copy(path: Path, input_dir: Path, config) -> bool:
    rel_path = path.relative_to(input_dir).as_posix()
    suffix = path.suffix.lower()
    normalized = _normalized_rel_path(rel_path)

    if suffix == ".pdf":
        return should_attempt_pdf_ocr(rel_path, config, page_count=0)
    if suffix in IMAGE_SUFFIXES:
        return should_attempt_image_ocr(rel_path, config)
    if suffix in DOC_LIKE_SUFFIXES:
        return _matches_shortlist(normalized, config)
    return False


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.out_dir)
    config = load_config(args.config)

    copied = 0
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in input_dir.rglob("*"):
        if not path.is_file() or not should_copy(path, input_dir, config):
            continue
        destination = output_dir / path.relative_to(input_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied += 1

    print(f"copied {copied} files into {output_dir}")


if __name__ == "__main__":
    main()
