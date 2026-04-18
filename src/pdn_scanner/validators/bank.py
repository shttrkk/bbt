from __future__ import annotations


def validate_bik(value: str) -> bool:
    digits = "".join(char for char in value if char.isdigit())
    return len(digits) == 9


def validate_account_with_bik(account: str, bik: str) -> bool:
    """Placeholder for account/BIK checksum pair validation."""
    return validate_bik(bik) and len("".join(char for char in account if char.isdigit())) == 20
