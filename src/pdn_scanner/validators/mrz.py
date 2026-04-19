from __future__ import annotations

import re

MRZ_TOKEN_RE = re.compile(r"^[A-Z0-9<]{30,44}$")


def validate_mrz(value: str) -> bool:
    token = value.strip().replace(" ", "")
    if not MRZ_TOKEN_RE.fullmatch(token):
        return False
    return token.startswith(("P<", "I<", "ID", "PN")) and "<" in token
