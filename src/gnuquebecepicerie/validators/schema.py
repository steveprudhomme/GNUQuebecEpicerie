from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver


def validate_json(document: dict[str, Any], schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    resolver = RefResolver(base_uri=schema_path.parent.resolve().as_uri() + "/", referrer=schema)
    validator = Draft202012Validator(schema, resolver=resolver)
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if errors:
        details = "\n".join(f"- {list(e.path)}: {e.message}" for e in errors)
        raise ValueError(f"JSON invalide selon {schema_path.name}:\n{details}")
