import copy
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from gnuquebecepicerie.cli import app
from gnuquebecepicerie.normalizers.superc import normalize_pages
from gnuquebecepicerie.normalizers.superc_snapshot import normalize_snapshot
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
    validate_json(flyer.model_dump(mode="json"), SCHEMAS / "flyer.schema.json")


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
    ({"priceSign": "¢"}, "ambiguous_currency_sign"),
    ({"salePriceFr": "de 2 à 4"}, "ambiguous_number"),
    ({"salePriceFr": "NaN"}, "ambiguous_number"),
    ({"salePriceFr": "0"}, "nonpositive_number"),
    ({"salePriceFr": None}, "missing_price_or_supported_reward"),
    ({"priceQuantity": "2.5"}, "noninteger_quantity"),
    ({"promoUnitFr": "environ 11 lb"}, "ambiguous_price_basis"),
    ({"salePricePrefixFr": "rabais de"}, "ambiguous_price_prefix"),
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
    assert (snapshot / "normalized/superc-0.1.0/123/report.json").exists()
