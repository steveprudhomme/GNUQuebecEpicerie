"""Conversion hors ligne d'un diagnostic vérifié en brouillon local V1."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from gnuquebecepicerie.normalizers.superc import (
    INTERNAL_STORE,
    NORMALIZER_VERSION,
    SOURCE_NAME,
    SOURCE_STORE,
    normalize_pages,
)
from gnuquebecepicerie.storage.json_store import content_revision, write_json_atomic
from gnuquebecepicerie.validators.schema import validate_json


def normalize_snapshot(snapshot: Path, publication: str, schemas: Path) -> tuple[Path, dict]:
    snapshot = snapshot.resolve()
    if not snapshot.is_relative_to(Path("local").resolve()):
        raise ValueError("Utiliser une capture sous local/ pour garder les données hors Git.")
    if not publication.isascii() or not publication.isdigit():
        raise ValueError("Identifiant de publication invalide.")
    summary = json.loads((snapshot / "summary.json").read_text(encoding="utf-8"))
    if (summary.get("source_store_id") != SOURCE_STORE
            or summary.get("store_id") != INTERNAL_STORE
            or summary.get("store_name") != SOURCE_NAME):
        raise ValueError("Capture issue d'un autre magasin.")
    expected = [f for f in summary["flyers"] if f["flyer_id"] == publication]
    if len(expected) != 1:
        raise ValueError("Publication absente ou ambiguë dans le résumé.")
    metadata_bytes = (snapshot / "metadata.json").read_bytes()
    metadata_all = json.loads(metadata_bytes)
    matches = [f for f in metadata_all["flyers"] if str(f["title"]) == publication]
    if len(matches) != 1:
        raise ValueError("Publication absente ou ambiguë dans les métadonnées.")
    metadata = matches[0]
    if (metadata.get("startDate") != expected[0]["valid_from_source"]
            or metadata.get("endDate") != expected[0]["valid_to_source"]):
        raise ValueError("Période différente du diagnostic.")
    pages_bytes = (snapshot / f"pages-{publication}.json").read_bytes()
    if hashlib.sha256(pages_bytes).hexdigest() != expected[0]["sha256"]:
        raise ValueError("Empreinte des pages différente du diagnostic.")
    flyer, report = normalize_pages(
        metadata, json.loads(pages_bytes), datetime.fromisoformat(summary["observed_at"])
    )
    document = flyer.model_dump(mode="json")
    revision = content_revision(document)
    # Ordre lexical des URL : /flyers/... puis /pages/..., encadrement V1 des octets bruts.
    framed = b"".join(len(raw).to_bytes(8, "big") + raw for raw in (metadata_bytes, pages_bytes))
    manifest = {
        "schema_version": "1.0", "flyer_id": flyer.flyer_id, "retailer_id": "superc",
        "store_id": INTERNAL_STORE, "valid_from": flyer.valid_from.isoformat(),
        "valid_to": flyer.valid_to.isoformat(), "retrieved_at": flyer.retrieved_at.isoformat(),
        "offers_count": len(flyer.offers),
        "source_hash": "sha256:" + hashlib.sha256(framed).hexdigest(),
        "content_hash": "sha256:" + revision, "collector_version": NORMALIZER_VERSION,
        "source_urls": [
            f"https://metrodigital-apim.azure-api.net/api/flyers/447/bil"
            f"?date={summary['requested_date']}",
            f"https://metrodigital-apim.azure-api.net/api/pages/{publication}/447/bil/",
        ],
    }
    document["source_urls"] = manifest["source_urls"]
    validate_json(document, schemas / "flyer.schema.json")
    validate_json(manifest, schemas / "manifest.schema.json")
    # Même sans rejet, les seuils historiques et la validation manuelle restent à réaliser.
    report["ready_for_archive"] = False
    report["status"] = "local_draft_requires_review"
    output = snapshot / "normalized" / NORMALIZER_VERSION / publication
    write_json_atomic(output / "flyer.json", document)
    write_json_atomic(output / "manifest.json", manifest)
    write_json_atomic(output / "report.json", report)
    (output / "source-input.bin").write_bytes(framed)
    return output, report
