import copy
import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from gnuquebecepicerie.models import Flyer
from gnuquebecepicerie.models_v11 import FlyerV11, parse_flyer
from gnuquebecepicerie.storage.json_store import content_revision
from gnuquebecepicerie.validators.schema import validate_json

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema/flyer.v1.1.schema.json"


def example():
    return json.loads((ROOT / "examples/flyer.v1.1.json").read_text(encoding="utf-8"))


def test_legacy_and_new_versions_validate_without_implicit_migration():
    old = json.loads((ROOT / "examples/flyer.v1.json").read_text(encoding="utf-8"))
    original = copy.deepcopy(old)
    validate_json(old, ROOT / "schema/flyer.schema.json")
    assert type(parse_flyer(old)) is Flyer
    assert old == original
    new = example()
    validate_json(new, SCHEMA)
    parsed = parse_flyer(new)
    assert type(parsed) is FlyerV11
    validate_json(parsed.model_dump(mode="json"), SCHEMA)
    for offer in parsed.offers:
        validate_json(offer.model_dump(mode="json"), ROOT / "schema/offer.v1.1.schema.json")
    with pytest.raises(ValueError):
        validate_json(new, ROOT / "schema/flyer.schema.json")
    with pytest.raises(ValueError):
        validate_json(old, SCHEMA)
    with pytest.raises(ValueError):
        parse_flyer({**old, "schema_version": "9.0"})


@pytest.mark.parametrize("changes", [
    {"amount": None}, {"percent": 20}, {"amount": 0}, {"amount": -2},
    {"amount": None, "percent": 101}, {"sale_price": 15},
    {"points": 100}, {"scope": "basket"}, {"conditions": []},
    {"conditions": [" "]}, {"loyalty_required": True},
    {"eligibility": {"qualifying_products": ["Pain"]}},
    {"eligibility": {"qualifying_products": [""], "minimum_quantity": 2}},
    {"eligibility": {"qualifying_products": ["Pain"], "minimum_quantity": 2,
                     "minimum_spend": 20}},
    {"eligibility": {"qualifying_products": ["Pain"], "minimum_quantity": 2,
                     "minimum_spend_scope": "basket"}},
])
def test_ambiguous_discounts_rejected_by_schema_and_model(changes):
    doc = example()
    offer = next(o for o in doc["offers"] if o["offer_id"] == "rabais-groupe")
    offer["promotion"].update(changes)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(doc))
    with pytest.raises(ValueError):
        FlyerV11.model_validate(doc)


@pytest.mark.parametrize("period", [
    {"valid_from": "2026-01-02", "valid_to": "2026-01-01"},
    {"valid_from": "2025-01-01", "valid_to": "2025-01-02"},
    {"valid_from": "2030-01-01", "valid_to": "2030-01-02"},
    {"valid_from": "2026-09-17"},
])
def test_invalid_offer_periods_rejected(period):
    doc = example()
    doc["offers"][0]["validity"] = period
    with pytest.raises(ValueError):
        validate_json(doc, SCHEMA)


def test_duplicate_ids_remain_forbidden():
    doc = example()
    doc["offers"].append(copy.deepcopy(doc["offers"][0]))
    with pytest.raises(ValueError):
        validate_json(doc, SCHEMA)


def test_discount_is_not_a_price_and_incomplete_conditions_stay_explicit():
    doc = parse_flyer(example()).model_dump(mode="json")
    basket = next(o for o in doc["offers"] if o["offer_id"] == "rabais-panier")
    assert basket["promotion"]["amount"] == 15
    assert "sale_price" not in basket["promotion"]
    assert basket["promotion"]["conditions_complete"] is False
    assert basket["validity"] is None


def test_revision_accounts_for_offer_period_and_conditions():
    doc = parse_flyer(example()).model_dump(mode="json")
    initial = content_revision(doc)
    changed = copy.deepcopy(doc)
    changed["offers"][0]["validity"] = {
        "valid_from": doc["valid_from"], "valid_to": doc["valid_from"]}
    assert content_revision(changed) != initial
    changed = copy.deepcopy(doc)
    changed["offers"][-2]["promotion"]["conditions_complete"] = False
    assert content_revision(changed) != initial
    changed = copy.deepcopy(doc)
    changed["retrieved_at"] = "2030-01-01T00:00:00Z"
    for offer in changed["offers"]:
        offer["source"]["retrieved_at"] = changed["retrieved_at"]
    assert content_revision(changed) == initial


def test_generated_schemas_are_current_and_valid():
    spec = importlib.util.spec_from_file_location(
        "generate_v11", ROOT / "scripts/generate_v11_schemas.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, schema in module.schemas().items():
        Draft202012Validator.check_schema(schema)
        assert schema == json.loads((ROOT / "schema" / name).read_text(encoding="utf-8"))
