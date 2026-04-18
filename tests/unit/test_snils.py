from pdn_scanner.validators.snils import is_valid_snils


def test_valid_snils() -> None:
    assert is_valid_snils("112-233-445 95") is True


def test_invalid_snils() -> None:
    assert is_valid_snils("112-233-445 96") is False
