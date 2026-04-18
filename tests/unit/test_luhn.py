from pdn_scanner.validators.luhn import is_valid_luhn


def test_valid_luhn_number() -> None:
    assert is_valid_luhn("4111111111111111") is True


def test_invalid_luhn_number() -> None:
    assert is_valid_luhn("4111111111111112") is False
