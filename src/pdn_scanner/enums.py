from enum import StrEnum


class FileFormat(StrEnum):
    TXT = "txt"
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    RTF = "rtf"
    XLS = "xls"
    HTML = "html"
    IMAGE = "image"
    VIDEO = "mp4"
    UNKNOWN = "unknown"


class ContentStatus(StrEnum):
    OK = "ok"
    EMPTY = "empty"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


class ValidationStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UZLevel(StrEnum):
    UZ1 = "UZ-1"
    UZ2 = "UZ-2"
    UZ3 = "UZ-3"
    UZ4 = "UZ-4"
    NO_PDN = "NO_PDN"


class StorageClass(StrEnum):
    TARGET_LEAK = "TARGET_LEAK"
    PD_BUT_JUSTIFIED_STORAGE = "PD_BUT_JUSTIFIED_STORAGE"
    NON_TARGET = "NON_TARGET"
