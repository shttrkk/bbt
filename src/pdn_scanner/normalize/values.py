from __future__ import annotations

import re


def normalize_phone(value: str) -> str:
    """Return digits-only phone value with Russian leading 8 normalized to 7."""
    digits = re.sub(r"\D+", "", value)
    if len(digits) == 11 and digits.startswith("8"):
        return "7" + digits[1:]
    return digits


def normalize_numeric_id(value: str) -> str:
    """Keep only digits for numeric identifiers such as SNILS/INN/card."""
    return re.sub(r"\D+", "", value)
