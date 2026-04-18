from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pdn_scanner.models import ProcessingError


class ErrorCode(StrEnum):
    CONFIG_ERROR = "config_error"
    WALKER_ERROR = "walker_error"
    FORMAT_DETECTION_ERROR = "format_detection_error"
    EXTRACTION_ERROR = "extraction_error"
    DETECTION_ERROR = "detection_error"
    CLASSIFICATION_ERROR = "classification_error"
    REPORTING_ERROR = "reporting_error"
    RUNTIME_ERROR = "runtime_error"


@dataclass(slots=True)
class PdnScannerError(Exception):
    code: ErrorCode
    stage: str
    message: str
    path: str | None = None
    recoverable: bool = True
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def to_processing_error(error: Exception, stage: str, path: str | None = None) -> ProcessingError:
    if isinstance(error, PdnScannerError):
        return ProcessingError(
            code=error.code.value,
            stage=error.stage,
            message=error.message,
            path=error.path or path,
            recoverable=error.recoverable,
            details=error.details,
        )

    return ProcessingError(
        code=ErrorCode.RUNTIME_ERROR.value,
        stage=stage,
        message=str(error),
        path=path,
        recoverable=True,
        details={},
    )
