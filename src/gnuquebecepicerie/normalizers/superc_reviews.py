"""Décisions visuelles limitées à une entrée source immuable."""

import hashlib
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gnuquebecepicerie.models import Promotion
from gnuquebecepicerie.models_v11 import ConditionalDiscount, OfferValidity


class SourceReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    publication: str = Field(pattern=r"^[0-9]+$")
    source_store_id: str
    sku: str = Field(min_length=1)
    valid_from: str
    valid_to: str
    observed_at: str
    source_url: str
    record_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    decision: Literal[
        "accept_coupon_flag", "accept_explicit_prices", "keep_rejected", "normalize_v11"
    ]
    promotions: list[Promotion | ConditionalDiscount] | None = None
    validity: OfferValidity | None = None
    evidence: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scope(self):
        if date.fromisoformat(self.valid_from) > date.fromisoformat(self.valid_to):
            raise ValueError("Période de révision inversée")
        date.fromisoformat(self.observed_at)
        expected = (f"https://circulaire.superc.ca/flyer/{self.publication}"
                    f"?storeId={self.source_store_id}&language=fr")
        if self.source_url != expected or not self.evidence.strip():
            raise ValueError("Source ou preuve de révision invalide")
        if self.decision == "normalize_v11":
            if not self.promotions and self.validity is None:
                raise ValueError("Une révision V1.1 exige des promotions ou une période.")
            if self.promotions == []:
                raise ValueError("Promotions révisées vides.")
            if self.validity and not (date.fromisoformat(self.valid_from)
                    <= self.validity.valid_from <= self.validity.valid_to
                    <= date.fromisoformat(self.valid_to)):
                raise ValueError("Période révisée hors circulaire.")
        elif self.promotions is not None or self.validity is not None:
            raise ValueError("Correction structurée sans décision V1.1.")
        return self


def record_digest(record: dict) -> str:
    raw = json.dumps(record, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_reviews(reviews: list) -> list[SourceReview]:
    if not isinstance(reviews, list):
        raise ValueError("Liste de révisions invalide")
    result = [SourceReview.model_validate(review) for review in reviews]
    identities = [(r.publication, r.source_store_id, r.sku, r.valid_from,
                   r.valid_to, r.record_sha256) for r in result]
    if len(set(identities)) != len(identities):
        raise ValueError("Décisions de révision en double")
    return result


def matching_review(reviews, metadata, record, store):
    for review in reviews:
        if (review.publication == str(metadata["title"])
                and review.source_store_id == store and review.sku == record.get("sku")
                and review.valid_from == metadata["startDate"][:10]
                and review.valid_to == metadata["endDate"][:10]
                and review.record_sha256 == record_digest(record)):
            return review.model_dump(mode="json", exclude_none=True)
    return None
