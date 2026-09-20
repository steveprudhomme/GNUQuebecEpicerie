from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Quantity(StrictModel):
    value: float = Field(gt=0)
    unit: str = Field(min_length=1)


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
    regular_price: float | None = Field(default=None, gt=0)
    currency: Literal["CAD"] = "CAD"
    multi_buy_quantity: int | None = Field(default=None, ge=2)
    multi_buy_price: float | None = Field(default=None, gt=0)
    loyalty_required: bool = False
    loyalty_program: str | None = None
    points: int | None = Field(default=None, ge=0)
    limit_quantity: int | None = Field(default=None, ge=1)
    price_after_limit: float | None = Field(default=None, gt=0)
    unit_prices: list[UnitPrice] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def promotion_has_value(self) -> Promotion:
        if self.sale_price is None and self.multi_buy_price is None and self.points is None:
            raise ValueError("Une promotion doit contenir un prix, un multi-achat ou des points.")
        return self


class Source(StrictModel):
    url: HttpUrl
    source_text: str | None = None
    retrieved_at: datetime


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
    published_at: datetime | None = None
    valid_from: date
    valid_to: date
    retrieved_at: datetime
    source_urls: list[HttpUrl] = Field(min_length=1)
    offers: list[Offer] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_date_range(self) -> Flyer:
        if self.valid_to < self.valid_from:
            raise ValueError("valid_to doit être postérieur ou égal à valid_from.")
        return self
