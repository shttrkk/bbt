from __future__ import annotations

import re
import unicodedata


def normalize_unicode(value: str) -> str:
    """Normalize Unicode to a canonical form suitable for rule-based matching."""
    return unicodedata.normalize("NFKC", value)


def normalize_whitespace(value: str) -> str:
    """Collapse repeated whitespace and strip edge spaces."""
    return re.sub(r"\s+", " ", value).strip()


def normalize_text(value: str) -> str:
    return normalize_whitespace(normalize_unicode(value))
