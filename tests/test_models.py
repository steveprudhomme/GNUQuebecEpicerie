from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from gnuquebecepicerie.models import Flyer, Offer, Product, Promotion, Source


def test_flyer_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError):
        Flyer(
            flyer_id="test",
            retailer_id="superc",
            store_id="store-1",
            valid_from=date(2026, 9, 24),
            valid_to=date(2026, 9, 23),
            retrieved_at=datetime.now(UTC),
            source_urls=["https://example.com/flyer"],
            offers=[],
        )


def test_offer_accepts_simple_price() -> None:
    offer = Offer(
        offer_id="offer-1",
        product=Product(raw_name="Beurre 454 g", name="Beurre"),
        promotion=Promotion(sale_price=4.99),
        source=Source(
            url="https://example.com/product",
            retrieved_at=datetime.now(UTC),
        ),
    )
    assert offer.promotion.currency == "CAD"
