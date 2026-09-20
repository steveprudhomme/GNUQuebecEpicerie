from gnuquebecepicerie.normalizers.text import normalize_text, parse_price_fr


def test_normalize_text() -> None:
    assert normalize_text("  Beurre   Lactantia \n 454 g ") == "Beurre Lactantia 454 g"


def test_parse_price_fr() -> None:
    assert parse_price_fr("4,99 $") == 4.99
