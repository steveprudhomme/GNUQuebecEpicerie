"""Exécuter avec python -m gnuquebecepicerie.analysis.superc --date YYYY-MM-DD."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from gnuquebecepicerie.analysis.assets import capture_assets

CONFIG_URL = "https://circulaire.superc.ca/config/app.json"
API_URL = "https://metrodigital-apim.azure-api.net/api"
STORE_ID = "447"
STORE_NAME = "LAVAL DES LAURENTIDES"
USER_AGENT = "GNUQuebecEpicerie/0.1 (+https://github.com/steveprudhomme/GNUQuebecEpicerie)"


def product_entries(value: Any) -> list[dict[str, Any]]:
    """Inclut les blocs imbriqués; conserve les répétitions pour le diagnostic."""
    result = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "products" and isinstance(child, list):
                result.extend(item for item in child if isinstance(item, dict))
            else:
                result.extend(product_entries(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(product_entries(child))
    return result


def summarize_pages(pages: list) -> dict[str, Any]:
    products = product_entries(pages)
    return {
        "pages_count": len(pages),
        "product_entries_count": len(products),
        "distinct_skus_count": len({p["sku"] for p in products if p.get("sku")}),
        "member_price_entries_count": sum(p.get("memberPriceFr") is not None for p in products),
        "fields": sorted({key for product in products for key in product}),
        "missing_sale_price_count": sum(p.get("salePriceFr") is None for p in products),
    }


def audit(
    client: httpx.Client, day: date, output: Path, delay: float = 2,
    asset_client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Lit la configuration publique en mémoire; écrit uniquement sous output."""
    response = client.get(CONFIG_URL)
    response.raise_for_status()
    config = response.json()
    if config["api"].rstrip("/") != API_URL:
        raise ValueError("La source API a changé : analyser la nouvelle configuration.")
    headers = {
        "Ocp-Apim-Subscription-Key": config["apikey"],
        "Banner": config["banner_id"],
        "x-api-version": config["api_version"],
    }
    time.sleep(delay)
    response = client.get(
        f"{API_URL}/flyers/{STORE_ID}/bil", params={"date": day.isoformat()}, headers=headers
    )
    response.raise_for_status()
    metadata = response.json()
    flyers = metadata.get("flyers", [])
    if not flyers:
        raise ValueError("Aucune circulaire disponible : aucune archive créée.")
    if any(flyer.get("storeName") != STORE_NAME for flyer in flyers):
        raise ValueError("Magasin inattendu : arrêt du diagnostic.")
    # Le lecteur renvoie aussi des aperçus : ne collecter que la période demandée.
    flyers = [flyer for flyer in flyers
              if date.fromisoformat(flyer["startDate"][:10]) <= day
              <= date.fromisoformat(flyer["endDate"][:10])]
    if not flyers:
        raise ValueError("Aucune circulaire ne couvre la date demandée.")
    output.mkdir(parents=True, exist_ok=False)
    (output / "metadata.json").write_bytes(response.content)
    result = {
        "observed_at": datetime.now(UTC).isoformat(),
        "requested_date": day.isoformat(),
        "store_id": "superc-laval-des-laurentides-1000",
        "source_store_id": STORE_ID,
        "store_name": STORE_NAME,
        "flyers": [],
    }
    for flyer in flyers:
        flyer_id = str(flyer["title"])
        if not flyer_id.isascii() or not flyer_id.isdigit():
            raise ValueError("Identifiant de circulaire inattendu.")
        time.sleep(delay)
        url = f"{API_URL}/pages/{flyer_id}/{STORE_ID}/bil/"
        response = client.get(url, headers=headers)
        response.raise_for_status()
        pages = response.json()
        if not isinstance(pages, list):
            raise ValueError("Structure des pages inattendue.")
        (output / f"pages-{flyer_id}.json").write_bytes(response.content)
        asset_summary = None
        if asset_client is not None:
            asset_summary = capture_assets(
                asset_client, pages, flyer_id, output, delay=min(delay, 0.2)
            )
        result["flyers"].append({
            "assets": ({k: v for k, v in asset_summary.items() if k != "items"}
                       if asset_summary is not None else {"status": "not_requested"}),
            "flyer_id": flyer_id,
            "valid_from_source": flyer.get("startDate"),
            "valid_to_source": flyer.get("endDate"),
            "url": url,
            "sha256": hashlib.sha256(response.content).hexdigest(),
            **summarize_pages(pages),
        })
    (output / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, type=date.fromisoformat)
    parser.add_argument("--no-assets", action="store_true",
                        help="Diagnostic JSON seul, sans conservation des visuels")
    args = parser.parse_args()
    output = Path("local/source-analysis") / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    # Clients séparés : la clé publique du lecteur ne part jamais vers le CDN.
    with (httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT}) as client,
          httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT}) as asset_client):
        result = audit(client, args.date, output,
                       asset_client=None if args.no_assets else asset_client)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    print(f"Diagnostic local : {output}")
    if not args.no_assets and any(not f["assets"]["complete"] for f in result["flyers"]):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
