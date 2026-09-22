"""Contrat 1.1 distinct : aucune réinterprétation des documents 1.0."""

from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from gnuquebecepicerie.models import Flyer, Offer, Promotion, StrictModel


class OfferValidity(StrictModel):
    valid_from: date
    valid_to: date

    @model_validator(mode="after")
    def ordered(self):
        if self.valid_to < self.valid_from:
            raise ValueError("Période de l'offre inversée.")
        return self


class Eligibility(StrictModel):
    qualifying_products: list[str] = Field(min_length=1)
    minimum_quantity: int | None = Field(default=None, ge=1)
    minimum_spend: float | None = Field(default=None, gt=0)
    minimum_spend_scope: Literal["qualifying_products", "basket"] | None = None

    @model_validator(mode="after")
    def explicit_scope(self):
        if any(not name.strip() for name in self.qualifying_products):
            raise ValueError("Les produits admissibles doivent être décrits.")
        if (self.minimum_spend is None) != (self.minimum_spend_scope is None):
            raise ValueError("Un seuil monétaire exige sa portée, et réciproquement.")
        return self


class ConditionalDiscount(StrictModel):
    kind: Literal["conditional_discount"]
    amount: float | None = Field(default=None, gt=0)
    percent: float | None = Field(default=None, gt=0, le=100)
    currency: Literal["CAD"] = "CAD"
    scope: Literal["product", "basket"]
    application: Literal["per_item", "per_qualifying_group", "per_transaction"]
    reference_basis: Literal["regular_price", "current_price", "basket_subtotal", "unspecified"]
    eligibility: Eligibility
    loyalty_required: bool = False
    loyalty_program: str | None = None
    conditions: list[str] = Field(min_length=1)
    conditions_complete: bool = False

    @model_validator(mode="after")
    def discount_is_explicit(self):
        if (self.amount is None) == (self.percent is None):
            raise ValueError("Préciser un montant OU un pourcentage de rabais.")
        if self.loyalty_required and not (self.loyalty_program or "").strip():
            raise ValueError("Le programme membre est requis.")
        if any(not text.strip() for text in self.conditions):
            raise ValueError("Les conditions doivent contenir du texte.")
        if self.scope == "basket":
            if self.application != "per_transaction":
                raise ValueError("Un rabais panier s'applique à la transaction.")
            if self.reference_basis not in {"basket_subtotal", "unspecified"}:
                raise ValueError("Base incompatible avec un rabais panier.")
        elif self.application == "per_transaction" or self.reference_basis == "basket_subtotal":
            raise ValueError("Portée produit incompatible avec une base panier.")
        if self.application == "per_qualifying_group" and self.eligibility.minimum_quantity is None:
            raise ValueError("Un rabais par groupe exige sa quantité minimale.")
        return self


class OfferV11(Offer):
    promotion: Promotion | ConditionalDiscount
    validity: OfferValidity | None = None


class FlyerV11(Flyer):
    schema_version: Literal["1.1"] = "1.1"
    offers: list[OfferV11] = Field(default_factory=list)

    @model_validator(mode="after")
    def offer_periods_within_flyer(self):
        for offer in self.offers:
            if offer.validity and not (
                self.valid_from <= offer.validity.valid_from
                <= offer.validity.valid_to <= self.valid_to
            ):
                raise ValueError("La période de l'offre doit être incluse dans la circulaire.")
        return self


def parse_flyer(document: dict) -> Flyer | FlyerV11:
    """Sélection explicite de version, sans conversion automatique."""
    version = document.get("schema_version")
    if version == "1.0":
        return Flyer.model_validate(document)
    if version == "1.1":
        return FlyerV11.model_validate(document)
    raise ValueError(f"Version de circulaire non prise en charge : {version}")
