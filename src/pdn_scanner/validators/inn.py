from __future__ import annotations

from pdn_scanner.validators.common import digits_only


def is_valid_inn(value: str) -> bool:
    digits = digits_only(value)
    if len(digits) == 10:
        return _is_valid_inn10(digits)
    if len(digits) == 12:
        return _is_valid_inn12(digits)
    return False


def _is_valid_inn10(value: str) -> bool:
    coefficients = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    checksum = sum(int(digit) * factor for digit, factor in zip(value[:9], coefficients, strict=True)) % 11 % 10
    return checksum == int(value[9])


def _is_valid_inn12(value: str) -> bool:
    coefficients_11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    checksum_11 = sum(
        int(digit) * factor for digit, factor in zip(value[:10], coefficients_11, strict=True)
    ) % 11 % 10
    if checksum_11 != int(value[10]):
        return False

    coefficients_12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    checksum_12 = sum(
        int(digit) * factor for digit, factor in zip(value[:11], coefficients_12, strict=True)
    ) % 11 % 10
    return checksum_12 == int(value[11])
