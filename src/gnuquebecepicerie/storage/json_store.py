from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any


def content_revision(document: dict[str, Any]) -> str:
    """Empreinte V1 du contenu métier, indépendante de l'heure de collecte."""
    content = {key: deepcopy(document[key]) for key in (
        "schema_version", "retailer_id", "store_id", "valid_from", "valid_to", "offers"
    )}
    for offer in content["offers"]:
        offer["source"].pop("retrieved_at", None)
    content["offers"].sort(key=lambda offer: offer["offer_id"])
    payload = json.dumps(
        content, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def archive_directory(
    data_root: Path, retailer_id: str, store_id: str, valid_from: str, revision: str
) -> Path:
    if retailer_id not in {"superc", "iga"}:
        raise ValueError("Enseigne inconnue.")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", store_id):
        raise ValueError("Identifiant de magasin invalide.")
    if not re.fullmatch(r"[0-9a-f]{64}", revision):
        raise ValueError("La révision doit être une empreinte SHA-256 hexadécimale.")
    if date.fromisoformat(valid_from).isoformat() != valid_from:
        raise ValueError("Date non canonique.")
    year = valid_from[:4]
    return data_root / year / retailer_id / store_id / valid_from / revision


def write_json_atomic(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)
