"""Normalisation prudente des réponses du lecteur Super C vers le contrat V1."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from bs4 import BeautifulSoup

from gnuquebecepicerie.models import Flyer, Offer, Product, Promotion, Quantity, Source, UnitPrice
from gnuquebecepicerie.normalizers.superc_reviews import matching_review, validate_reviews
from gnuquebecepicerie.storage.json_store import content_revision

NORMALIZER_VERSION = "superc-0.4.0"
INTERNAL_STORE = "superc-laval-des-laurentides-1000"
SOURCE_STORE = "447"
SOURCE_NAME = "LAVAL DES LAURENTIDES"
RAW_FIELDS = (
    "sku", "upc", "productFr", "bodyFr", "productBrands", "brandDescriptionFr",
    "salePriceFr", "salePrice", "regularPriceFr", "regularPrice", "priceQuantity",
    "priceSign", "salePricePrefixFr", "promoUnitFr", "alternatePriceFr", "contents",
    "memberPriceFr", "memberPriceEn", "memberPriceQuantity", "memberPriceUnit",
    "memberPriceSign", "memberPricePrefixFr", "memberPriceSuffixFr", "memberSave",
    "memberSavePrefix", "memberSaveSuffixFr", "pts", "coupon",
    "loyalty", "loyaltyPrefix", "loyaltySuffixFr", "savingsFr", "savingsPrefix",
    "savingsSuffix", "rabaisMM", "limitQty",
    "afterLimitPrice", "rowPrice", "rowPriceQty", "rowPriceUnit", "tx",
    "validFrom", "validTo", "validFromROW", "validToROW", "attr1", "attr2", "attr3",
)


class ReviewRequired(ValueError):
    """Entrée conservée localement pour révision, sans conversion hasardeuse."""


def clean(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ReviewRequired("text_not_string")
    return " ".join(BeautifulSoup(value, "html.parser").get_text(" ").split())


def number(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    text = str(value).strip().replace(",", ".")
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        raise ReviewRequired("ambiguous_number")
    result = Decimal(text)
    if not result.is_finite() or result <= 0:
        raise ReviewRequired("nonpositive_number")
    return result


def integer(value: Any) -> int | None:
    parsed = number(value)
    if parsed is None:
        return None
    if parsed != parsed.to_integral_value():
        raise ReviewRequired("noninteger_quantity")
    return int(parsed)


def first(record: dict, primary: str, fallback: str) -> Any:
    value = record.get(primary)
    return record.get(fallback) if value is None or value == "" else value


def basis(value: Any) -> str:
    unit = clean(value).lower().replace(" ", "")
    # Description d'un format approximatif, et non tarif à la livre.
    if re.fullmatch(r"environ\d+(?:[.,]\d+)?lb", unit):
        return "package"
    units = {"": "package", "caisse": "package", "àcaisse": "package",
             "½caisse": "package",
             "/lb": "lb", "/kg": "kg", "/100g": "100g", "/l": "l",
             "/100ml": "100ml", "/un.": "unit", "/un": "unit"}
    if unit not in units:
        raise ReviewRequired("ambiguous_price_basis")
    return units[unit]


def business_date(value: Any) -> date:
    # Ces champs codent les journées commerciales; ne pas décaler minuit UTC à Laval.
    if not isinstance(value, str):
        raise ReviewRequired("invalid_date")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise ReviewRequired("invalid_date") from exc


def entries(value: Any) -> list[dict]:
    result = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "products":
                if not isinstance(child, list) or any(not isinstance(p, dict) for p in child):
                    raise ValueError("Tableau products invalide : arrêt de la normalisation.")
                result.extend(child)
            else:
                result.extend(entries(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(entries(child))
    return result


def product(record: dict) -> Product:
    raw_name = record.get("productFr")
    name = clean(raw_name)
    if not name:
        raise ReviewRequired("missing_product_name")
    body = clean(record.get("bodyFr"))
    # Un format exact isolé seulement : aucune inférence sur assortiment ou intervalle.
    match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(g|kg|ml|l)", body, re.IGNORECASE)
    quantity = None
    if match:
        quantity = Quantity(value=float(number(match[1])), unit=match[2].lower())
    for key in ("sku", "upc"):
        if record.get(key) is not None and not isinstance(record[key], str):
            raise ReviewRequired("nonstring_product_identifier")
    return Product(
        raw_name=raw_name, name=name, variant=body or None, quantity=quantity,
        sku=record.get("sku") or None, upc=record.get("upc") or None,
        # Une liste de marques peut désigner un assortiment; ne pas en choisir une.
        brand=clean(record.get("brandDescriptionFr")) or None,
        category=clean(record.get("mainCategoryFr")) or None,
    )


def promotion(record: dict, member: bool, conditions: list[str]) -> Promotion:
    prefix = "member" if member else "sale"
    sign = clean(record.get("memberPriceSign" if member else "priceSign"))
    if sign not in {"", "$", "¢"}:
        raise ReviewRequired("ambiguous_currency_sign")
    unit_field = record.get("memberPriceUnit") if member else record.get("promoUnitFr")
    if member and not unit_field:
        unit_field = record.get("promoUnitFr")
    unit = basis(unit_field)
    quantity = integer(record.get("memberPriceQuantity" if member else "priceQuantity"))
    if member and quantity is None and record.get("priceQuantity") not in (None, "", "1", 1):
        raise ReviewRequired("ambiguous_member_multi_buy")
    if quantity == 1:
        quantity = None
    price = number(first(record, prefix + "PriceFr", "memberPriceEn" if member else "salePrice"))
    if price is None:
        raise ReviewRequired("missing_price")
    # Le lecteur formate 0.99 en 0,99 $ même quand priceSign vaut ¢.
    # Une future convention encodant 99 plutôt que 0.99 doit être revue.
    if sign == "¢":
        if price >= 1:
            raise ReviewRequired("ambiguous_currency_sign")
        other = record.get("memberPriceEn" if member else "salePrice")
        if other not in (None, "") and number(other) != price:
            raise ReviewRequired("conflicting_currency_values")
    if quantity and unit not in {"package", "unit"}:
        raise ReviewRequired("weighted_multi_buy")
    regular = None
    # Un prix normal libre ou au poids reste dans le texte source, sans l'extraire partiellement.
    if not quantity and unit in {"package", "unit"}:
        try:
            regular = number(first(record, "regularPriceFr", "regularPrice"))
        except ReviewRequired:
            pass
    unit_prices = []
    if unit == "lb":
        per_kg = (price / Decimal("0.45359237")).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
        unit_prices.append(UnitPrice(value=float(per_kg), basis="kg"))
    elif unit in {"kg", "100g", "l", "100ml", "unit"}:
        unit_prices.append(UnitPrice(value=float(price), basis=unit))
    return Promotion(
        sale_price=None if quantity else float(price), price_basis=unit,
        regular_price=float(regular) if regular is not None else None,
        multi_buy_quantity=quantity, multi_buy_price=float(price) if quantity else None,
        loyalty_required=member, loyalty_program="moi" if member else None,
        limit_quantity=integer(record.get("limitQty")),
        price_after_limit=(float(number(record["afterLimitPrice"]))
                           if record.get("afterLimitPrice") not in (None, "") else None),
        unit_prices=unit_prices, conditions=conditions,
    )


def normalize_record(
    record: dict, metadata: dict, retrieved_at: datetime, reviewed_decision: str | None = None
) -> list[Offer]:
    # Un montant de rabais ne devient jamais un prix final par soustraction implicite.
    if any("rabais de" in clean(record.get(key)).lower() for key in (
        "salePricePrefixFr", "memberPricePrefixFr", "savingsPrefix"
    )):
        raise ReviewRequired("discount_amount_requires_review")
    if record.get("rabaisMM") not in (None, "", 0, "0", "0.00"):
        public = number(first(record, "salePriceFr", "salePrice"))
        member = number(first(record, "memberPriceFr", "memberPriceEn"))
        discount = number(record["rabaisMM"])
        if public is None or member is None:
            raise ReviewRequired("member_discount_without_final_price")
        public_unit = basis(record.get("promoUnitFr"))
        member_unit = basis(record.get("memberPriceUnit") or record.get("promoUnitFr"))
        public_qty = integer(record.get("priceQuantity")) or 1
        member_qty = integer(record.get("memberPriceQuantity")) or 1
        if public_unit != member_unit or public_qty != member_qty:
            raise ReviewRequired("member_discount_basis_requires_review")
        if public - member != discount and reviewed_decision != "accept_explicit_prices":
            raise ReviewRequired("member_discount_conflicts_with_prices")
    if (record.get("coupon") not in (None, False)
            and reviewed_decision != "accept_coupon_flag"):
        if (record.get("coupon") is not True
                or clean(record.get("memberPricePrefixFr")).lower() != "prix membre"
                or first(record, "memberPriceFr", "memberPriceEn") in (None, "")):
            raise ReviewRequired("coupon_requires_review")
    if record.get("memberSave") not in (None, ""):
        raise ReviewRequired("member_discount_amount_requires_review")
    for key in ("rowPrice", "rowPriceQty", "rowPriceUnit", "loyalty"):
        if record.get(key) not in (None, ""):
            raise ReviewRequired("unsupported_" + key)
    if clean(record.get("salePricePrefixFr")).lower() not in {
        "", "prix réduit", "bas prix tous les jours"
    }:
        raise ReviewRequired("ambiguous_price_prefix")
    if clean(record.get("memberPricePrefixFr")).lower() not in {"", "prix membre"}:
        raise ReviewRequired("ambiguous_member_prefix")
    for suffix in ("validFrom", "validFromROW"):
        if (record.get(suffix)
                and business_date(record[suffix]) != business_date(metadata["startDate"])):
            raise ReviewRequired("offer_period_differs")
    for suffix in ("validTo", "validToROW"):
        if (record.get(suffix)
                and business_date(record[suffix]) != business_date(metadata["endDate"])):
            raise ReviewRequired("offer_period_differs")
    title = str(metadata["title"])
    url = f"https://circulaire.superc.ca/flyer/{title}?storeId={SOURCE_STORE}&language=fr"
    raw = {key: record[key] for key in RAW_FIELDS if key in record}
    source = Source(url=url, retrieved_at=retrieved_at,
                    source_text=json.dumps(raw, ensure_ascii=False, sort_keys=True))
    conditions = [f"{key}: {clean(record[key])}" for key in (
        "bodyFr", "alternatePriceFr", "savingsFr", "savingsPrefix", "savingsSuffix",
        "salePricePrefixFr", "memberPricePrefixFr",
        "memberPriceSuffixFr", "memberPriceUnit", "promoUnitFr", "loyaltyPrefix",
        "loyaltySuffixFr", "attr1", "attr2", "attr3", "tx"
    ) if record.get(key)]
    item = product(record)
    promotions = []
    if first(record, "salePriceFr", "salePrice") not in (None, ""):
        promotions.append(promotion(record, False, conditions))
    if first(record, "memberPriceFr", "memberPriceEn") not in (None, ""):
        promotions.append(promotion(record, True, conditions))
    if record.get("pts") not in (None, "", 0, "0"):
        # Les points sont une offre membre séparée, jamais une réduction du prix public.
        points = integer(record["pts"])
        promotions.append(Promotion(
            points=points, loyalty_required=True, loyalty_program="moi", conditions=conditions
        ))
    if not promotions:
        raise ReviewRequired("missing_price_or_supported_reward")
    offers = []
    for promo in promotions:
        offer = Offer(offer_id="pending", product=item, promotion=promo, source=source)
        content = offer.model_dump(mode="json")
        del content["offer_id"]
        del content["source"]["retrieved_at"]
        canonical = json.dumps(content, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), allow_nan=False)
        offer.offer_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        offers.append(offer)
    return offers


def normalize_pages(
    metadata: dict, pages: list, retrieved_at: datetime, known_issues: tuple | list = (),
    source_reviews: list | None = None,
) -> tuple[Flyer, dict]:
    if metadata.get("storeName") != SOURCE_NAME:
        raise ValueError("Magasin inattendu : aucune normalisation.")
    if metadata.get("language") != "bil":
        raise ValueError("Langue de source inattendue.")
    title = str(metadata.get("title", ""))
    if not title.isascii() or not title.isdigit():
        raise ValueError("Identifiant de circulaire invalide.")
    if not isinstance(pages, list) or not pages:
        raise ValueError("Pages absentes ou invalides.")
    reviews = validate_reviews(source_reviews if source_reviews is not None else [])
    applied_reviews = []
    records = entries(pages)
    offers: dict[str, Offer] = {}
    rejected, skipped = [], []
    accepted = duplicates = 0
    for index, record in enumerate(records):
        action = record.get("actionType")
        if action in {"URL", "Inblock"}:
            skipped.append({"index": index, "action": action})
            continue
        source_review = matching_review(reviews, metadata, record, SOURCE_STORE)
        if source_review:
            applied_reviews.append({"index": index, **source_review})
        try:
            if action != "Product":
                raise ReviewRequired("unknown_action_type")
            for issue in known_issues:
                if (issue["publication"] == title and issue["source_store_id"] == SOURCE_STORE
                        and issue["sku"] == record.get("sku")
                        and issue["valid_from"] == metadata["startDate"][:10]
                        and issue["valid_to"] == metadata["endDate"][:10]):
                    source_review = issue
                    raise ReviewRequired(issue["reason"])
            decision = source_review["decision"] if source_review else None
            normalized = normalize_record(record, metadata, retrieved_at, decision)
            accepted += 1
            for offer in normalized:
                if offer.offer_id in offers:
                    duplicates += 1
                offers[offer.offer_id] = offer
        except (ReviewRequired, ValueError) as exc:
            rejection = {"index": index, "reason": str(exc), "record": record}
            if source_review is not None:
                rejection["source_review"] = source_review
            rejected.append(rejection)
    flyer = Flyer(
        flyer_id="pending", retailer_id="superc", store_id=INTERNAL_STORE,
        valid_from=business_date(metadata["startDate"]),
        valid_to=business_date(metadata["endDate"]), retrieved_at=retrieved_at,
        source_urls=[f"https://circulaire.superc.ca/flyer/{title}?storeId=447&language=fr"],
        offers=sorted(offers.values(), key=lambda offer: offer.offer_id),
    )
    revision = content_revision(flyer.model_dump(mode="json"))
    flyer.flyer_id = f"{INTERNAL_STORE}:{flyer.valid_from}:{revision}"
    report = {
        "normalizer_version": NORMALIZER_VERSION, "source_entries": len(records),
        "accepted_entries": accepted, "skipped_entries": len(skipped),
        "rejected_entries": len(rejected), "offers_count": len(offers),
        "duplicate_offers_removed": duplicates,
        "normalization_complete": bool(offers) and not rejected,
        "ready_for_archive": False,
        "applied_source_reviews": applied_reviews,
        "warnings": ["Les dates structurées ne garantissent pas la validité commerciale affichée. "
                     "Une vérification visuelle est nécessaire avant archivage."],
        "rejection_reasons": dict(Counter(item["reason"] for item in rejected)),
        "skipped": skipped, "rejected": rejected,
    }
    return flyer, report
