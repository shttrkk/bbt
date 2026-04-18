from __future__ import annotations

import re


def digits_only(value: str) -> str:
    return re.sub(r"\D+", "", value)
