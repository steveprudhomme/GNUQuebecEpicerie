from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Quantity(StrictModel):
    value: float = Field(gt=0)
    unit: Literal["g", "kg", "ml", "l", "unit"]


class UnitPrice(StrictModel):
    value: float = Field(gt=0)
    basis: Literal["100g", "kg", "100ml", "l", "unit"]


class Product(StrictModel):
    raw_name: str = Field(min_length=1)
    name: str = Field(min_length=1)
    brand: str | None = None
    variant: str | None = None
    sku: str | None = None
    upc: str | None = None
    category: str | None = None
    quantity: Quantity | None = None


class Promotion(StrictModel):
    sale_price: float | None = Field(default=None, gt=0)
    price_basis: Literal["package", "unit", "kg", "lb", "100g", "l", "100ml"] = "package"
    discount_percent: float | None = Field(default=None, gt=0, le=100)
    regular_price: float | None = Field(default=None, gt=0)
    currency: Literal["CAD"] = "CAD"
    multi_buy_quantity: int | None = Field(default=None, ge=2)
    multi_buy_price: float | None = Field(default=None, gt=0)
    loyalty_required: bool = False
    loyalty_program: str | None = None
    points: int | None = Field(default=None, gt=0)
    limit_quantity: int | None = Field(default=None, ge=1)
    price_after_limit: float | None = Field(default=None, gt=0)
    unit_prices: list[UnitPrice] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def promotion_has_value(self) -> Promotion:
        if all(value is None for value in (
            self.sale_price, self.multi_buy_price, self.points, self.discount_percent
        )):
            raise ValueError("Une promotion doit contenir un prix, un rabais ou des points.")
        if (self.multi_buy_quantity is None) != (self.multi_buy_price is None):
            raise ValueError("Un multi-achat exige une quantité et un prix total.")
        if self.loyalty_required and not self.loyalty_program:
            raise ValueError("Le programme de fidélité est requis pour un prix membre.")
        if self.price_after_limit is not None and self.limit_quantity is None:
            raise ValueError("Le prix après limite exige une limite de quantité.")
        return self


class Source(StrictModel):
    url: HttpUrl
    source_text: str | None = None
    retrieved_at: AwareDatetime


class Offer(StrictModel):
    offer_id: str = Field(min_length=1)
    product: Product
    promotion: Promotion
    source: Source


class Flyer(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    flyer_id: str = Field(min_length=1)
    retailer_id: Literal["superc", "iga"]
    store_id: str = Field(min_length=1)
    published_at: AwareDatetime | None = None
    valid_from: date
    valid_to: date
    retrieved_at: AwareDatetime
    source_urls: list[HttpUrl] = Field(min_length=1)
    offers: list[Offer] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_date_range(self) -> Flyer:
        if self.valid_to < self.valid_from:
            raise ValueError("valid_to doit être postérieur ou égal à valid_from.")
        if len({offer.offer_id for offer in self.offers}) != len(self.offers):
            raise ValueError("Les offer_id doivent être uniques dans une circulaire.")
        return self
