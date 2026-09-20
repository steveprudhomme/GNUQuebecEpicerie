import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from gnuquebecepicerie.config import load_yaml
from gnuquebecepicerie.models import Flyer, Promotion
from gnuquebecepicerie.storage.json_store import archive_directory, content_revision
from gnuquebecepicerie.validators.schema import validate_json

ROOT = Path(__file__).resolve().parents[1]


def example():
    return json.loads((ROOT / "examples/flyer.v1.json").read_text(encoding="utf-8"))


def test_all_schemas_are_valid():
    for path in (ROOT / "schema").glob("*.json"):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_seven_promotion_examples_and_model_roundtrip():
    document = example()
    assert len(document["offers"]) == 7
    validate_json(document, ROOT / "schema/flyer.schema.json")
    validate_json(Flyer.model_validate(document).model_dump(mode="json"),
                  ROOT / "schema/flyer.schema.json")


@pytest.mark.parametrize("promotion", [
    {}, {"regular_price": 8}, {"sale_price": 0}, {"points": 0},
    {"multi_buy_price": 5}, {"multi_buy_quantity": 2, "sale_price": 5},
    {"sale_price": 3, "loyalty_required": True},
    {"sale_price": 3, "price_after_limit": 5},
    {"discount_percent": 101}, {"sale_price": 3, "unexpected": True},
])
def test_incomplete_promotions_rejected_by_schema_and_model(promotion):
    offer = example()["offers"][0]
    offer["promotion"] = {"currency": "CAD", "price_basis": "package", **promotion}
    with pytest.raises(ValueError):
        validate_json(offer, ROOT / "schema/offer.schema.json")
    with pytest.raises(ValidationError):
        Promotion.model_validate(offer["promotion"])


@pytest.mark.parametrize("case", ["date", "naive_time", "inverted", "duplicate", "unit"])
def test_invalid_flyers_rejected(case):
    document = example()
    if case == "date":
        document["valid_from"] = "2026-02-30"
    elif case == "naive_time":
        document["offers"][0]["source"]["retrieved_at"] = "2026-09-20T18:00:00"
    elif case == "inverted":
        document["valid_to"] = "2026-09-01"
    elif case == "duplicate":
        document["offers"].append(copy.deepcopy(document["offers"][0]))
    else:
        document["offers"][0]["product"]["quantity"] = {"value": 1, "unit": "unknown"}
    with pytest.raises(ValueError):
        validate_json(document, ROOT / "schema/flyer.schema.json")


@pytest.mark.parametrize("name", ["stores.yaml", "stores.example.yaml"])
def test_store_registry(name):
    registry = load_yaml(ROOT / "config" / name)
    validate_json(registry, ROOT / "schema/stores.schema.json")
    assert {s["store_id"] for s in registry["stores"]} == {
        "superc-laval-des-laurentides-1000", "iga-laval-cartier-ouest-307"
    }


@pytest.mark.parametrize("case", ["duplicate", "unverified", "retailer"])
def test_invalid_store_registry(case):
    registry = load_yaml(ROOT / "config/stores.yaml")
    if case == "duplicate":
        registry["stores"].append(copy.deepcopy(registry["stores"][0]))
    elif case == "unverified":
        registry["stores"][0]["enabled"] = True
        registry["stores"][0]["source_store_id"] = None
    else:
        registry["stores"][0]["retailer_id"] = "iga"
    with pytest.raises(ValueError):
        validate_json(registry, ROOT / "schema/stores.schema.json")


def test_archive_paths_separate_stores_and_revisions(tmp_path):
    first = archive_directory(tmp_path, "superc", "superc-one", "2026-09-24", "a" * 64)
    other = archive_directory(tmp_path, "superc", "superc-two", "2026-09-24", "a" * 64)
    revised = archive_directory(tmp_path, "superc", "superc-one", "2026-09-24", "b" * 64)
    assert len({first, other, revised}) == 3
    assert first == tmp_path / "2026/superc/superc-one/2026-09-24" / ("a" * 64)


def test_archive_path_rejects_traversal(tmp_path):
    with pytest.raises(ValueError):
        archive_directory(tmp_path, "superc", "../outside", "2026-09-24", "a" * 64)


def test_revision_ignores_poll_time_and_offer_order_but_detects_price_changes():
    document = example()
    original = copy.deepcopy(document)
    revision = content_revision(document)
    assert document["flyer_id"] == f"{document['store_id']}:{document['valid_from']}:{revision}"
    assert document == original
    document["retrieved_at"] = "2026-09-21T18:00:00-04:00"
    for offer in document["offers"]:
        offer["source"]["retrieved_at"] = document["retrieved_at"]
    document["offers"].reverse()
    assert content_revision(document) == revision
    document["offers"][0]["promotion"]["sale_price"] = 9.99
    assert content_revision(document) != revision
