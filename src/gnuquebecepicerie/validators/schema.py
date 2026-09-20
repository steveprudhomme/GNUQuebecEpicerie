from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from gnuquebecepicerie.models import Flyer, Offer


def validate_json(document: dict[str, Any], schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    registry = Registry()
    for path in schema_path.parent.glob("*.schema.json"):
        local_schema = json.loads(path.read_text(encoding="utf-8"))
        resource = Resource.from_contents(local_schema)
        uri = local_schema.get("$id", path.resolve().as_uri())
        registry = registry.with_resource(uri, resource)
        registry = registry.with_resource(path.resolve().as_uri(), resource)
    validator = Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda error: str(list(error.path)))
    if errors:
        details = "\n".join(f"- {list(e.path)}: {e.message}" for e in errors)
        raise ValueError(f"JSON invalide selon {schema_path.name}:\n{details}")
    if schema_path.name == "flyer.schema.json":
        Flyer.model_validate(document)
    elif schema_path.name == "offer.schema.json":
        Offer.model_validate(document)
    elif schema_path.name == "stores.schema.json":
        stores = document["stores"]
        if len({store["store_id"] for store in stores}) != len(stores):
            raise ValueError("Les store_id doivent être uniques dans le registre.")
        for store in stores:
            if not store["store_id"].startswith(store["retailer_id"] + "-"):
                raise ValueError("Le store_id doit commencer par l'identifiant de l'enseigne.")
            if store["enabled"] and not store["source_store_id"]:
                raise ValueError("Un magasin actif exige un identifiant source vérifié.")
