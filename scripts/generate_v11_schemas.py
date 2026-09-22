"""Régénère uniquement les schémas 1.1; ne modifie jamais les schémas V1."""

import json
from pathlib import Path

from gnuquebecepicerie.models_v11 import FlyerV11, OfferV11

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://github.com/steveprudhomme/GNUQuebecEpicerie/raw/main/schema/"


def present(key, kind="number"):
    return {"required": [key], "properties": {key: {"type": kind}}}


def schemas():
    legacy = json.loads((ROOT / "schema/offer.schema.json").read_text(encoding="utf-8"))
    result = {}
    for name, model in (("offer.v1.1.schema.json", OfferV11),
                        ("flyer.v1.1.schema.json", FlyerV11)):
        schema = model.model_json_schema()
        schema.update({"$schema": "https://json-schema.org/draft/2020-12/schema",
                       "$id": BASE + name})
        # Conserver exactement les contraintes structurelles des promotions V1.
        schema["$defs"]["Promotion"] = legacy["properties"]["promotion"]
        discount = schema["$defs"]["ConditionalDiscount"]
        discount["oneOf"] = [
            {**present("amount"), "not": present("percent")},
            {**present("percent"), "not": present("amount")},
        ]
        discount["allOf"] = [
            {"if": {"properties": {"loyalty_required": {"const": True}},
                    "required": ["loyalty_required"]},
             "then": {"required": ["loyalty_program"],
                      "properties": {"loyalty_program": {"type": "string", "pattern": r"\S"}}}},
            {"if": {"properties": {"scope": {"const": "basket"}}},
             "then": {"properties": {
                 "application": {"const": "per_transaction"},
                 "reference_basis": {"enum": ["basket_subtotal", "unspecified"]}}},
             "else": {"properties": {
                 "application": {"enum": ["per_item", "per_qualifying_group"]},
                 "reference_basis": {"enum": ["regular_price", "current_price", "unspecified"]}}}},
            {"if": {"properties": {"application": {"const": "per_qualifying_group"}}},
             "then": {"properties": {"eligibility": present("minimum_quantity", "integer")}}},
        ]
        discount["properties"]["conditions"]["items"]["pattern"] = r"\S"
        eligibility = schema["$defs"]["Eligibility"]
        eligibility["properties"]["qualifying_products"]["items"]["pattern"] = r"\S"
        eligibility["allOf"] = [
            {"if": present("minimum_spend"),
             "then": present("minimum_spend_scope", "string")},
            {"if": present("minimum_spend_scope", "string"),
             "then": present("minimum_spend")},
        ]
        if model is FlyerV11:
            schema["properties"]["store_id"]["pattern"] = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
            schema["required"] = list(
                dict.fromkeys(schema["required"] + ["schema_version", "offers"])
            )
        result[name] = schema
    manifest = json.loads((ROOT / "schema/manifest.schema.json").read_text(encoding="utf-8"))
    manifest["$id"] = BASE + "manifest.v1.1.schema.json"
    manifest["properties"]["schema_version"]["const"] = "1.1"
    result["manifest.v1.1.schema.json"] = manifest
    return result


if __name__ == "__main__":
    for name, schema in schemas().items():
        (ROOT / "schema" / name).write_text(
            json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
