from pdn_scanner.validators.inn import is_valid_inn


def test_valid_inn_10() -> None:
    assert is_valid_inn("7707083893") is True


def test_invalid_inn_10() -> None:
    assert is_valid_inn("7707083894") is False


def test_valid_inn_12() -> None:
    assert is_valid_inn("500100732259") is True


def test_invalid_inn_12() -> None:
    assert is_valid_inn("500100732258") is False
