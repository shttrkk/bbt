from __future__ import annotations

import os
from pathlib import Path

from pdn_scanner.config import AppConfig
from pdn_scanner.models import FileDescriptor, ProcessingError
from pdn_scanner.runtime.errors import ErrorCode


def walk_directory(input_dir: Path, config: AppConfig) -> tuple[list[FileDescriptor], list[ProcessingError]]:
    descriptors: list[FileDescriptor] = []
    errors: list[ProcessingError] = []

    for root, dirnames, filenames in os.walk(input_dir, followlinks=config.scan.follow_symlinks):
        if not config.scan.include_hidden:
            dirnames[:] = [name for name in dirnames if not name.startswith(".")]
            filenames = [name for name in filenames if not name.startswith(".")]

        for filename in filenames:
            path = Path(root) / filename
            try:
                stat = path.stat()
            except OSError as exc:
                errors.append(
                    ProcessingError(
                        code=ErrorCode.WALKER_ERROR.value,
                        stage="walker",
                        message=str(exc),
                        path=str(path),
                        recoverable=True,
                    )
                )
                continue

            descriptors.append(
                FileDescriptor(
                    path=str(path),
                    rel_path=str(path.relative_to(input_dir)),
                    size_bytes=stat.st_size,
                    extension=path.suffix.lower().lstrip("."),
                )
            )

    return descriptors, errors
