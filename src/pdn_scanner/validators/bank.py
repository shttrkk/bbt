from __future__ import annotations


def validate_bik(value: str) -> bool:
    digits = "".join(char for char in value if char.isdigit())
    return len(digits) == 9 and digits != "000000000"


def validate_account_with_bik(account: str, bik: str) -> bool:
    account_digits = "".join(char for char in account if char.isdigit())
    bik_digits = "".join(char for char in bik if char.isdigit())
    return validate_bik(bik_digits) and len(account_digits) == 20 and account_digits != "0" * 20
