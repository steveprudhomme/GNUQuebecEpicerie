import copy
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from gnuquebecepicerie.cli import app
from gnuquebecepicerie.normalizers.superc import NORMALIZER_VERSION, normalize_pages
from gnuquebecepicerie.normalizers.superc_snapshot import normalize_snapshot
from gnuquebecepicerie.storage.json_store import content_revision
from gnuquebecepicerie.validators.schema import validate_json

SCHEMAS = Path(__file__).resolve().parents[1] / "schema"
NOW = datetime(2026, 9, 20, 18, tzinfo=UTC)
META = {
    "title": "123", "storeName": "LAVAL DES LAURENTIDES", "language": "bil",
    "startDate": "2026-09-17T00:00:00Z", "endDate": "2026-09-23T23:59:00Z",
}


def record(**changes):
    return {
        "actionType": "Product", "sku": "000123", "upc": "001234567890",
        "productFr": "Produit fictif Québec", "bodyFr": "500 g", "salePriceFr": "4,99",
        "regularPrice": "6,99", "priceSign": "$", "pts": 0,
        "validFrom": "2026-09-17T04:00:00Z", "validTo": "2026-09-23T04:00:00Z",
        **changes,
    }


def normalize(*records, now=NOW):
    return normalize_pages(META, [{"blocks": [{"products": list(records)}]}], now)


def test_simple_price_keeps_original_text_and_date_without_timezone_shift():
    flyer, report = normalize(record())
    offer = flyer.offers[0]
    assert offer.promotion.sale_price == 4.99
    assert offer.promotion.regular_price == 6.99
    assert offer.promotion.points is None
    assert offer.product.quantity.value == 500
    assert offer.product.name == "Produit fictif Québec"
    assert offer.product.sku == "000123"
    assert json.loads(offer.source.source_text)["salePriceFr"] == "4,99"
    assert str(flyer.valid_from) == "2026-09-17"
    assert report["normalization_complete"]
    assert not report["ready_for_archive"]
    validate_json(flyer.model_dump(mode="json"), SCHEMAS / "flyer.v1.1.schema.json")


def test_member_and_public_prices_are_distinct_offers():
    flyer, _ = normalize(record(memberPriceFr="3.99", memberPricePrefixFr="prix membre"))
    assert len(flyer.offers) == 2
    assert len({offer.offer_id for offer in flyer.offers}) == 2
    member = next(o for o in flyer.offers if o.promotion.loyalty_required)
    assert member.promotion.sale_price == 3.99
    assert member.promotion.loyalty_program == "moi"
    public = next(o for o in flyer.offers if not o.promotion.loyalty_required)
    assert public.promotion.sale_price == 4.99


def test_multi_buy_does_not_invent_single_purchase_price():
    flyer, _ = normalize(record(salePriceFr="5.00", priceQuantity="2"))
    promo = flyer.offers[0].promotion
    assert promo.sale_price is None
    assert promo.multi_buy_quantity == 2
    assert promo.multi_buy_price == 5
    assert promo.regular_price is None


def test_weighted_price_conversion_uses_decimal_and_keeps_original_basis():
    flyer, _ = normalize(record(salePriceFr="1.94", promoUnitFr="/lb",
                                bodyFr="poids variable", regularPrice="3,79/lb - 8,36/kg"))
    promo = flyer.offers[0].promotion
    assert promo.sale_price == 1.94
    assert promo.price_basis == "lb"
    assert promo.unit_prices[0].value == 4.276968
    assert promo.unit_prices[0].basis == "kg"
    assert promo.regular_price is None
    assert flyer.offers[0].product.quantity is None


def test_reward_is_separate_from_public_price_and_requires_membership():
    flyer, _ = normalize(record(pts=20))
    assert len(flyer.offers) == 2
    reward = next(o for o in flyer.offers if o.promotion.points)
    assert reward.promotion.points == 20
    assert reward.promotion.sale_price is None
    assert reward.promotion.loyalty_required
    assert not next(o for o in flyer.offers if o.promotion.sale_price).promotion.loyalty_required


def test_limit_and_after_limit_price():
    flyer, _ = normalize(record(limitQty="4", afterLimitPrice="7.99"))
    assert flyer.offers[0].promotion.limit_quantity == 4
    assert flyer.offers[0].promotion.price_after_limit == 7.99


@pytest.mark.parametrize("changes,reason", [
    ({"coupon": True}, "coupon_requires_review"),
    ({"priceSign": "¢", "salePriceFr": "99"}, "ambiguous_currency_sign"),
    ({"salePriceFr": "de 2 à 4"}, "ambiguous_number"),
    ({"salePriceFr": "NaN"}, "ambiguous_number"),
    ({"salePriceFr": "0"}, "nonpositive_number"),
    ({"salePriceFr": None}, "missing_price_or_supported_reward"),
    ({"priceQuantity": "2.5"}, "noninteger_quantity"),
    ({"promoUnitFr": "prix variable"}, "ambiguous_price_basis"),
    ({"salePricePrefixFr": "rabais de"}, "discount_amount_requires_review"),
    ({"rowPrice": "3.00"}, "unsupported_rowPrice"),
    ({"validToROW": "2026-09-21T04:00:00Z"}, "offer_period_differs"),
    ({"validFrom": "not-a-date"}, "invalid_date"),
    ({"sku": 123}, "nonstring_product_identifier"),
    ({"priceQuantity": "2", "memberPriceFr": "2.99"}, "ambiguous_member_multi_buy"),
    ({"actionType": "NewUnknownType"}, "unknown_action_type"),
])
def test_uncertain_entries_are_rejected_with_original_record(changes, reason):
    raw = record(**changes)
    flyer, report = normalize(raw)
    assert not flyer.offers
    assert report["rejected_entries"] == 1
    assert report["rejected"][0]["reason"] == reason
    assert report["rejected"][0]["record"] == raw
    assert not report["normalization_complete"]


def test_variable_format_and_regular_price_range_remain_unknown():
    flyer, _ = normalize(record(bodyFr="300-500 g, choix variés", regularPrice="de 6,99 à 8,99"))
    assert flyer.offers[0].product.quantity is None
    assert flyer.offers[0].promotion.regular_price is None


def test_exact_duplicates_removed_but_same_sku_different_price_preserved():
    flyer, report = normalize(record(), record(), record(salePriceFr="3.99"))
    assert len(flyer.offers) == 2
    assert report["accepted_entries"] == 3
    assert report["duplicate_offers_removed"] == 1


def test_identity_is_stable_across_order_and_retrieval_time_without_mutation():
    records = [record(), record(sku="other", salePriceFr="2.99")]
    original = copy.deepcopy(records)
    first, _ = normalize(*records)
    later, _ = normalize(*reversed(records), now=NOW + timedelta(days=1))
    assert first.flyer_id == later.flyer_id
    assert records == original


def test_nonproduct_blocks_skipped_explicitly():
    flyer, report = normalize(record(), {"actionType": "URL"}, {"actionType": "Inblock"})
    assert len(flyer.offers) == 1
    assert report["skipped_entries"] == 2
    assert report["source_entries"] == 3


@pytest.mark.parametrize("change", [{"storeName": "STE-THERESE"}, {"language": "en"}])
def test_wrong_store_or_language_stops_entire_batch(change):
    with pytest.raises(ValueError):
        normalize_pages({**META, **change}, [{"products": [record()]}], NOW)


def test_malformed_products_container_stops_entire_batch():
    with pytest.raises(ValueError):
        normalize_pages(META, [{"products": [None]}], NOW)


def snapshot_fixture(tmp_path, monkeypatch, raw=None):
    monkeypatch.chdir(tmp_path)
    snapshot = tmp_path / "local/capture"
    snapshot.mkdir(parents=True)
    pages = json.dumps([{"products": [raw or record()]}]).encode()
    (snapshot / "pages-123.json").write_bytes(pages)
    (snapshot / "metadata.json").write_text(json.dumps({"flyers": [META]}), encoding="utf-8")
    summary = {
        "source_store_id": "447", "store_id": "superc-laval-des-laurentides-1000",
        "store_name": "LAVAL DES LAURENTIDES", "observed_at": NOW.isoformat(),
        "requested_date": "2026-09-20", "flyers": [{
            "flyer_id": "123", "sha256": hashlib.sha256(pages).hexdigest(),
            "valid_from_source": META["startDate"], "valid_to_source": META["endDate"],
        }],
    }
    (snapshot / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return snapshot


def test_snapshot_manifest_matches_source_and_repeat_is_deterministic(tmp_path, monkeypatch):
    snapshot = snapshot_fixture(tmp_path, monkeypatch)
    output, _ = normalize_snapshot(snapshot, "123", SCHEMAS)
    before = {path.name: path.read_bytes() for path in output.iterdir()}
    normalize_snapshot(snapshot, "123", SCHEMAS)
    assert before == {path.name: path.read_bytes() for path in output.iterdir()}
    flyer = json.loads(before["flyer.json"])
    manifest = json.loads(before["manifest.json"])
    expected_hash = "sha256:" + hashlib.sha256(before["source-input.bin"]).hexdigest()
    assert manifest["source_hash"] == expected_hash
    assert manifest["flyer_id"] == flyer["flyer_id"]
    assert manifest["source_urls"] == flyer["source_urls"]
    assert manifest["offers_count"] == len(flyer["offers"])
    assert not (tmp_path / "data").exists()


def test_tampered_snapshot_rejected_before_output(tmp_path, monkeypatch):
    snapshot = snapshot_fixture(tmp_path, monkeypatch)
    (snapshot / "pages-123.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="Empreinte"):
        normalize_snapshot(snapshot, "123", SCHEMAS)
    assert not (snapshot / "normalized").exists()


def test_cli_reports_partial_result_with_nonzero_status(tmp_path, monkeypatch):
    snapshot = snapshot_fixture(tmp_path, monkeypatch, record(coupon=True))
    result = CliRunner().invoke(app, ["normalize-superc", str(snapshot),
                                    "--publication", "123", "--schemas", str(SCHEMAS)])
    assert result.exit_code == 2
    assert "1 entrées à revoir" in result.output
    assert (snapshot / "normalized" / NORMALIZER_VERSION / "123/report.json").exists()


@pytest.mark.parametrize("price", ["0.99", "0,88"])
def test_cents_symbol_does_not_divide_dollar_value_by_one_hundred(price):
    flyer, report = normalize(record(salePriceFr=price, salePrice=price, priceSign="¢"))
    assert not report["rejected"]
    assert flyer.offers[0].promotion.sale_price == float(price.replace(",", "."))


def test_conflicting_french_and_generic_cents_values_rejected():
    _, report = normalize(record(salePriceFr="0.99", salePrice="99", priceSign="¢"))
    assert report["rejection_reasons"] == {"conflicting_currency_values": 1}


def test_member_price_with_coupon_flag_requires_explicit_member_label():
    flyer, report = normalize(record(coupon=True, memberPriceFr="0.99",
                                     memberPriceSign="¢", memberPricePrefixFr="prix membre"))
    assert not report["rejected"]
    assert len(flyer.offers) == 2
    member = next(o for o in flyer.offers if o.promotion.loyalty_required)
    assert member.promotion.sale_price == 0.99
    assert member.promotion.loyalty_program == "moi"
    assert json.loads(member.source.source_text)["coupon"] is True
    _, rejected = normalize(record(coupon=True, memberPriceFr="0.99"))
    assert rejected["rejection_reasons"] == {"coupon_requires_review": 1}


def test_member_discount_is_not_treated_as_final_price():
    _, report = normalize(record(memberPriceFr="3.99", memberSave="2$"))
    assert report["rejection_reasons"] == {"member_discount_amount_requires_review": 1}


@pytest.mark.parametrize("unit", ["environ 11 lb", "½ caisse"])
def test_package_descriptions_keep_format_without_inventing_unit_price(unit):
    flyer, report = normalize(record(promoUnitFr=unit, bodyFr="format annoncé"))
    assert not report["rejected"]
    offer = flyer.offers[0]
    assert offer.promotion.price_basis == "package"
    assert offer.product.quantity is None
    assert offer.promotion.unit_prices == []
    assert f"promoUnitFr: {unit}" in offer.promotion.conditions


def test_visual_review_quarantines_only_matching_publication_store_and_period():
    issue = {
        "publication": "123", "source_store_id": "447", "sku": "000123",
        "valid_from": "2026-09-17", "valid_to": "2026-09-23",
        "reason": "visual_period_conflicts_with_json",
    }
    pages = [{"products": [record()]}]
    flyer, report = normalize_pages(META, pages, NOW, [issue])
    assert not flyer.offers
    assert report["rejection_reasons"] == {"visual_period_conflicts_with_json": 1}
    assert report["rejected"][0]["source_review"] == issue
    for field, value in [("publication", "456"), ("source_store_id", "465"),
                         ("valid_from", "2026-09-24"), ("sku", "other")]:
        flyer, _ = normalize_pages(META, pages, NOW, [{**issue, field: value}])
        assert len(flyer.offers) == 1


def test_missing_review_registry_blocks_snapshot(tmp_path, monkeypatch):
    snapshot = snapshot_fixture(tmp_path, monkeypatch)
    schemas = tmp_path / "schema"
    schemas.mkdir()
    with pytest.raises(FileNotFoundError):
        normalize_snapshot(snapshot, "123", schemas)
    assert not (snapshot / "normalized").exists()


@pytest.mark.parametrize("changes,reason", [
    ({"salePriceFr": "3", "salePricePrefixFr": "prix réduit rabais de"},
     "discount_amount_requires_review"),
    ({"salePriceFr": None, "savingsPrefix": "rabais de", "savingsFr": "2$",
      "savingsSuffix": "à l’achat de 2 pains", "coupon": True},
     "discount_amount_requires_review"),
    ({"rabaisMM": "1.00"}, "member_discount_without_final_price"),
    ({"rabaisMM": "1.00", "memberPriceFr": "4.49"},
     "member_discount_conflicts_with_prices"),
    ({"rabaisMM": "1.00", "memberPriceFr": "3.99", "memberPriceUnit": "/lb"},
     "member_discount_basis_requires_review"),
    ({"rabaisMM": "1.00", "memberPriceFr": "3.99", "memberPriceQuantity": "2"},
     "member_discount_basis_requires_review"),
])
def test_discount_ambiguities_block_whole_entry(changes, reason):
    flyer, report = normalize(record(**changes))
    assert not flyer.offers
    assert report["rejection_reasons"] == {reason: 1}


def test_consistent_member_discount_preserves_both_explicit_prices():
    flyer, report = normalize(record(rabaisMM="1.00", memberPriceFr="3.99"))
    assert not report["rejected"]
    assert sorted(o.promotion.sale_price for o in flyer.offers) == [3.99, 4.99]
    assert all(json.loads(o.source.source_text)["rabaisMM"] == "1.00" for o in flyer.offers)


def test_savings_conditions_preserved_without_changing_final_price():
    flyer, _ = normalize(record(savingsPrefix="économie :", savingsFr="2$",
                                savingsSuffix="à l’achat de 2 produits"))
    offer = flyer.offers[0]
    assert offer.promotion.sale_price == 4.99
    assert "savingsSuffix: à l’achat de 2 produits" in offer.promotion.conditions
    assert json.loads(offer.source.source_text)["savingsPrefix"] == "économie :"


def test_review_list_preserves_conditions_and_warns_about_dates(tmp_path, monkeypatch):
    snapshot = snapshot_fixture(tmp_path, monkeypatch, record(
        savingsPrefix="rabais de", savingsFr="2$", savingsSuffix="à l’achat de 2 pains"
    ))
    output, report = normalize_snapshot(snapshot, "123", SCHEMAS)
    text = (output / "review.txt").read_text(encoding="utf-8")
    assert "à l’achat de 2 pains" in text
    assert "SKU 000123" in text
    assert "2026-09-23" in text
    assert "pas une validation visuelle" in text
    assert not report["ready_for_archive"]



def visual_review(raw, decision="accept_coupon_flag"):
    from gnuquebecepicerie.normalizers.superc_reviews import record_digest
    return {
        "publication": "123", "source_store_id": "447", "sku": raw["sku"],
        "valid_from": "2026-09-17", "valid_to": "2026-09-23",
        "observed_at": "2026-09-21", "decision": decision,
        "record_sha256": record_digest(raw), "evidence": "Observation fictive de test.",
        "source_url": "https://circulaire.superc.ca/flyer/123?storeId=447&language=fr",
    }


def test_reviewed_coupon_keeps_raw_flag_and_logs_decision():
    raw = record(coupon=True, pts=20)
    review = visual_review(raw)
    flyer, report = normalize_pages(META, [{"products": [raw]}], NOW,
                                    source_reviews=[review])
    assert len(flyer.offers) == 2
    assert json.loads(flyer.offers[0].source.source_text)["coupon"] is True
    assert report["applied_source_reviews"] == [{"index": 0, **review}]
    assert not report["ready_for_archive"]


@pytest.mark.parametrize("change", [
    {"salePriceFr": "9.99"}, {"sku": "other"}, {"pts": 300},
    {"validTo": "2026-09-18T04:00:00Z"}, {"newCondition": "nouvelle condition"},
])
def test_changed_source_invalidates_visual_permission(change):
    raw = record(coupon=True)
    flyer, report = normalize_pages(META, [{"products": [{**raw, **change}]}], NOW,
                                    source_reviews=[visual_review(raw)])
    assert not flyer.offers
    assert not report["applied_source_reviews"]


def test_review_cannot_transfer_to_another_publication_or_store():
    raw = record(coupon=True)
    for changes in (
        {"publication": "999", "source_url":
         "https://circulaire.superc.ca/flyer/999?storeId=447&language=fr"},
        {"source_store_id": "448", "source_url":
         "https://circulaire.superc.ca/flyer/123?storeId=448&language=fr"},
        {"valid_to": "2026-09-24"},
    ):
        flyer, report = normalize_pages(META, [{"products": [raw]}], NOW,
                                        source_reviews=[{**visual_review(raw), **changes}])
        assert not flyer.offers
        assert not report["applied_source_reviews"]


def test_reviewed_explicit_prices_do_not_rewrite_discount_or_bypass_coupon():
    raw = record(memberPriceFr="2.99", salePriceFr="3.49", regularPrice="3.99",
                 rabaisMM="1.00", memberPricePrefixFr="prix membre", coupon=True)
    flyer, _ = normalize_pages(META, [{"products": [raw]}], NOW,
                              source_reviews=[visual_review(raw, "accept_explicit_prices")])
    assert sorted(o.promotion.sale_price for o in flyer.offers) == [2.99, 3.49]
    assert json.loads(flyer.offers[0].source.source_text)["rabaisMM"] == "1.00"
    raw["memberPricePrefixFr"] = ""
    flyer, report = normalize_pages(META, [{"products": [raw]}], NOW,
                                    source_reviews=[visual_review(raw, "accept_explicit_prices")])
    assert not flyer.offers
    assert report["rejection_reasons"] == {"coupon_requires_review": 1}


def test_visual_coupon_permission_does_not_override_date_guard():
    raw = record(coupon=True, validTo="2026-09-18T04:00:00Z")
    flyer, report = normalize_pages(META, [{"products": [raw]}], NOW,
                                    source_reviews=[visual_review(raw)])
    assert not flyer.offers
    assert report["rejection_reasons"] == {"offer_period_differs": 1}


@pytest.mark.parametrize("change", [
    {"decision": "accept_everything"}, {"record_sha256": "bad"},
    {"evidence": " "}, {"observed_at": "yesterday"},
])
def test_invalid_visual_registry_stops_batch(change):
    raw = record(coupon=True)
    with pytest.raises(ValueError):
        normalize_pages(META, [{"products": [raw]}], NOW,
                        source_reviews=[{**visual_review(raw), **change}])


def test_duplicate_visual_decisions_stop_batch():
    raw = record(coupon=True)
    review = visual_review(raw)
    with pytest.raises(ValueError, match="double"):
        normalize_pages(META, [{"products": [raw]}], NOW, source_reviews=[review, review])



def test_v11_reviewed_period_overrides_only_known_period_issue():
    raw = record()
    review = {**visual_review(raw, "normalize_v11"),
              "validity": {"valid_from": "2026-09-17", "valid_to": "2026-09-18"}}
    issue = {key: review[key] for key in (
        "publication", "source_store_id", "sku", "valid_from", "valid_to")}
    issue["reason"] = "visual_period_conflicts_with_json"
    flyer, report = normalize_pages(META, [{"products": [raw]}], NOW, [issue], [review])
    assert flyer.schema_version == "1.1"
    assert str(flyer.offers[0].validity.valid_to) == "2026-09-18"
    assert json.loads(flyer.offers[0].source.source_text)["validTo"] == raw["validTo"]
    assert not report["rejected"]
    issue["reason"] = "another_issue"
    flyer, report = normalize_pages(META, [{"products": [raw]}], NOW, [issue], [review])
    assert not flyer.offers


def discount_review(raw):
    return {**visual_review(raw, "normalize_v11"), "promotions": [{
        "kind": "conditional_discount", "amount": 15, "scope": "basket",
        "application": "per_transaction", "reference_basis": "unspecified",
        "eligibility": {"qualifying_products": ["Caisses fictives"], "minimum_quantity": 2},
        "conditions": ["Conditions des astérisques à confirmer"],
        "conditions_complete": False,
    }]}


def test_incomplete_discount_is_not_price_or_complete_batch():
    raw = record(salePriceFr=None)
    flyer, report = normalize_pages(META, [{"products": [raw]}], NOW,
                                    source_reviews=[discount_review(raw)])
    promo = flyer.offers[0].promotion.model_dump()
    assert promo["amount"] == 15 and "sale_price" not in promo
    assert report["accepted_entries"] == 1
    assert report["rejected_entries"] == 0
    assert report["incomplete_entries"] == 1
    assert not report["normalization_complete"] and not report["ready_for_archive"]
    validate_json(flyer.model_dump(mode="json"), SCHEMAS / "flyer.v1.1.schema.json")
    altered = {**raw, "bodyFr": "Nouvelle condition"}
    flyer, report = normalize_pages(META, [{"products": [altered]}], NOW,
                                    source_reviews=[discount_review(raw)])
    assert not flyer.offers and report["rejected_entries"] == 1


def test_reviewed_prices_preserve_source_and_do_not_invent_rewards():
    raw = record(salePriceFr="10.99", memberPriceFr=None, rabaisMM="1.00", coupon=True)
    review = {**visual_review(raw, "normalize_v11"), "promotions": [
        {"sale_price": 11.99},
        {"sale_price": 10.99, "loyalty_required": True, "loyalty_program": "moi"},
    ]}
    flyer, report = normalize_pages(META, [{"products": [raw]}], NOW, source_reviews=[review])
    assert len(flyer.offers) == 2
    assert sorted(o.promotion.sale_price for o in flyer.offers) == [10.99, 11.99]
    assert all(json.loads(o.source.source_text)["salePriceFr"] == "10.99" for o in flyer.offers)
    assert all(o.promotion.points is None for o in flyer.offers)
    assert report["applied_source_reviews"][0]["promotions"]


def test_cli_incomplete_discount_alone_returns_nonzero(tmp_path, monkeypatch):
    import shutil
    raw = record(salePriceFr=None)
    snapshot = snapshot_fixture(tmp_path, monkeypatch, raw)
    shutil.copytree(SCHEMAS, tmp_path / "schema")
    registry = tmp_path / "config/source-reviews/superc.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"version": 1, "issues": [],
                                    "reviews": [discount_review(raw)]}), encoding="utf-8")
    result = CliRunner().invoke(app, ["normalize-superc", str(snapshot),
                                    "--publication", "123", "--schemas", str(tmp_path / "schema")])
    assert result.exit_code == 2
    assert "1 entrées aux conditions incomplètes" in result.output
    output = snapshot / "normalized" / NORMALIZER_VERSION / "123"
    flyer = json.loads((output / "flyer.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert flyer["schema_version"] == manifest["schema_version"] == "1.1"
    assert manifest["content_hash"] == "sha256:" + content_revision(flyer)
    assert "Conditions incomplètes" in (output / "review.txt").read_text(encoding="utf-8")
