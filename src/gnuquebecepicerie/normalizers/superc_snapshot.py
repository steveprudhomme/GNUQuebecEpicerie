"""Conversion hors ligne d'un diagnostic vérifié en brouillon local V1.1."""

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
    review_path = schemas.resolve().parent / "config/source-reviews/superc.json"
    reviews = json.loads(review_path.read_text(encoding="utf-8"))
    if reviews.get("version") != 1 or not isinstance(reviews.get("issues"), list):
        raise ValueError("Registre de révision Super C invalide.")
    flyer, report = normalize_pages(
        metadata, json.loads(pages_bytes), datetime.fromisoformat(summary["observed_at"]),
        known_issues=reviews["issues"], source_reviews=reviews.get("reviews", []),
    )
    report["review_registry_sha256"] = hashlib.sha256(review_path.read_bytes()).hexdigest()
    document = flyer.model_dump(mode="json")
    revision = content_revision(document)
    # Ordre lexical des URL : /flyers/... puis /pages/..., encadrement V1 des octets bruts.
    framed = b"".join(len(raw).to_bytes(8, "big") + raw for raw in (metadata_bytes, pages_bytes))
    manifest = {
        "schema_version": "1.1", "flyer_id": flyer.flyer_id, "retailer_id": "superc",
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
    validate_json(document, schemas / "flyer.v1.1.schema.json")
    validate_json(manifest, schemas / "manifest.v1.1.schema.json")
    # Même sans rejet, les seuils historiques et la validation manuelle restent à réaliser.
    report["ready_for_archive"] = False
    report["status"] = "local_draft_requires_review"
    output = snapshot / "normalized" / NORMALIZER_VERSION / publication
    write_json_atomic(output / "flyer.json", document)
    write_json_atomic(output / "manifest.json", manifest)
    write_json_atomic(output / "report.json", report)
    (output / "source-input.bin").write_bytes(framed)
    (output / "review.txt").write_text(review_text(report, publication), encoding="utf-8")
    return output, report


REVIEW_REASONS = {
    "discount_amount_requires_review": "Rabais annoncé : prix final non établi.",
    "member_discount_without_final_price": "Rabais membre : prix final membre absent.",
    "member_discount_conflicts_with_prices": "Rabais membre incompatible avec les deux prix.",
    "member_discount_basis_requires_review": "Bases ou quantités des prix non comparables.",
    "coupon_requires_review": "Conditions du coupon à vérifier.",
    "missing_price_or_supported_reward": "Prix promotionnel ou récompense absent.",
    "visual_period_conflicts_with_json": "Dates de l'image incompatibles avec le JSON.",
    "offer_period_differs": "Période du produit différente de celle de la circulaire.",
}


def review_text(report: dict, publication: str) -> str:
    """Liste locale de vérification; aucune décision de validation n'est déduite."""
    lines = [
        f"Révision Super C — publication {publication}",
        f"{report['rejected_entries']} entrées bloquées; "
        f"{report['offers_count']} offres en brouillon.",
        "Les dates affichées dans le JSON ne sont pas une validation visuelle.",
        "Les offres acceptées doivent également être vérifiées avant archivage.",
        "Modifier cette liste ne débloque aucune offre.",
        f"Source : https://circulaire.superc.ca/flyer/{publication}?storeId=447&language=fr",
        "",
    ]
    fields = (
        "productFr", "bodyFr", "salePricePrefixFr", "salePriceFr", "priceQuantity",
        "promoUnitFr", "memberPricePrefixFr", "memberPriceFr", "memberPriceQuantity",
        "memberPriceUnit", "rabaisMM", "savingsPrefix", "savingsFr", "savingsSuffix",
        "coupon", "pts", "validFrom", "validTo", "validFromROW", "validToROW",
    )
    for entry in report["rejected"]:
        record = entry["record"]
        lines.append(f"[ ] Entrée {entry['index']} — SKU {record.get('sku', '?')}")
        reason = entry["reason"]
        lines.append(f"    Motif : {REVIEW_REASONS.get(reason, reason)} ({reason})")
        if entry.get("source_review"):
            evidence = json.dumps(entry["source_review"], ensure_ascii=False, sort_keys=True)
            lines.append(f"    Observation enregistrée : {evidence}")
        for field in fields:
            value = record.get(field)
            if value is not None and value != "":
                # JSON sur une ligne conserve les données et neutralise les sauts de ligne source.
                lines.append(f"    {field} : {json.dumps(value, ensure_ascii=False)}")
        lines.append("")
    for entry in report.get("incomplete", []):
        lines.append(f"[ ] Conditions incomplètes — entrée {entry['index']}, SKU {entry['sku']}")
        lines.append(json.dumps(entry["source_review"], ensure_ascii=False, sort_keys=True))
    return "\n".join(lines) + "\n"
