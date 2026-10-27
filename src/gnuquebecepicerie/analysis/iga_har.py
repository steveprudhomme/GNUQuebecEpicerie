"""Inspection locale des requêtes de publications Flipp, sans rejouer le réseau."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from gnuquebecepicerie.storage.json_store import write_json_atomic


def inspect_har(document: dict) -> dict:
    entries = document.get("log", {}).get("entries")
    if not isinstance(entries, list):
        raise ValueError("Export HAR invalide : liste des requêtes absente.")
    candidates = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Entrée HAR invalide.")
        request, response = entry.get("request", {}), entry.get("response", {})
        if not isinstance(request, dict) or not isinstance(response, dict):
            raise ValueError("Structure de requête HAR invalide.")
        if not isinstance(request.get("url", ""), str):
            raise ValueError("URL HAR invalide.")
        try:
            url = urlsplit(request.get("url", ""))
        except ValueError:
            continue
        if (url.scheme != "https" or url.hostname != "dam.flippenterprise.net"
                or request.get("method") != "GET"
                or not re.fullmatch(r"/hosted/publications/[a-zA-Z0-9_-]{1,100}", url.path)):
            continue
        query = parse_qs(url.query)
        store_values = query.get("store_code", [])
        store_matches = store_values == ["8270"]
        content = response.get("content", {})
        if not isinstance(content, dict):
            raise ValueError("Contenu HAR invalide.")
        body = content.get("text")
        payload = None
        body_status = "missing"
        if isinstance(body, str):
            try:
                if content.get("encoding") == "base64":
                    body = base64.b64decode(body, validate=True).decode("utf-8")
                elif content.get("encoding") not in (None, ""):
                    raise ValueError("Encodage inconnu")
                payload = json.loads(body)
                body_status = "json" if isinstance(payload, (dict, list)) else "unexpected_json"
            except (ValueError, UnicodeError):
                body_status = "invalid_or_non_json"
        status = response.get("status")
        status = status if type(status) is int else None
        candidates.append({
            # Ne jamais recopier l'URL complète, les en-têtes, cookies ou contenus source.
            "endpoint": "https://dam.flippenterprise.net" + url.path,
            "store_matches_8270": store_matches,
            "http_status": status, "body_status": body_status,
            "top_level_type": type(payload).__name__ if body_status == "json" else None,
            "top_level_list_count": len(payload) if isinstance(payload, list) else None,
            "usable_for_source_analysis": store_matches and status == 200 and body_status == "json",
        })
    return {
        "version": 1, "source_store_id": "8270", "candidates": candidates,
        "candidate_count": len(candidates),
        "source_response_found": any(c["usable_for_source_analysis"] for c in candidates),
        "commercial_validation_complete": False, "ready_for_archive": False,
    }


def inspect_har_file(path: Path) -> tuple[Path, dict]:
    path = path.resolve()
    if not path.is_relative_to(Path("local").resolve()):
        raise ValueError("Conserver l'export HAR sous local/.")
    if path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError("Export trop volumineux; limiter la capture au lecteur de circulaires.")
    raw = path.read_bytes()
    document = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(document, dict) or not isinstance(document.get("log"), dict):
        raise ValueError("Export HAR invalide.")
    report = inspect_har(document)
    report["capture_sha256"] = hashlib.sha256(raw).hexdigest()
    output = path.with_name(path.name + ".diagnostic.json")
    write_json_atomic(output, report)
    return output, report
