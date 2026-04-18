from __future__ import annotations

from pdn_scanner.validators.common import digits_only


def is_valid_snils(value: str) -> bool:
    digits = digits_only(value)
    if len(digits) != 11 or digits == "00000000000":
        return False

    number = digits[:9]
    checksum = int(digits[9:])
    total = sum(int(digit) * weight for digit, weight in zip(number, range(9, 0, -1), strict=True))

    if total < 100:
        expected = total
    elif total in (100, 101):
        expected = 0
    else:
        expected = total % 101
        if expected == 100:
            expected = 0

    return checksum == expected
