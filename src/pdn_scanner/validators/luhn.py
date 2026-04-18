from __future__ import annotations

from pdn_scanner.validators.common import digits_only


def is_valid_luhn(value: str) -> bool:
    digits = digits_only(value)
    if len(digits) < 13 or len(digits) > 19:
        return False

    checksum = 0
    parity = len(digits) % 2

    for index, char in enumerate(digits):
        digit = int(char)
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit

    return checksum % 10 == 0
