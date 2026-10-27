"""Diagnostic hors ligne du contexte visible IGA; aucune extraction commerciale."""

from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path

from gnuquebecepicerie.storage.json_store import write_json_atomic

STORE_NAME = "IGA Extra des-Rapides"
MONTHS = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août",
          "sept.", "oct.", "nov.", "déc.")


def inspect_context(text: str, publication: str, valid_from: date, valid_to: date) -> dict:
    """Vérifie une capture AX complète, avec période attendue fournie explicitement.

    Les onglets n'affichent pas l'année : celle fournie n'est jamais certifiée ici.
    """
    if not re.fullmatch(r"[0-9]+", publication) or valid_from > valid_to:
        raise ValueError("Publication ou période attendue invalide.")
    if (valid_to - valid_from).days > 31:
        raise ValueError("Période attendue trop longue pour ce diagnostic.")
    reasons = []
    page = text.splitlines()[0] if text.splitlines() else ""
    if not re.search(r"https://www\.iga\.ca/fr/circulaire\?"
                     r'set_preferred_store_number=8270(?:["\s]|$)', page):
        reasons.append("unexpected_page_or_store_parameter")
    # Le titre de la fiche ou un résultat voisin ne remplace pas l'en-tête sélectionné.
    header = re.search(r"pop up button[^\n]*Description: "
                       + re.escape(STORE_NAME) + r" Ouvert aujourd'hui", text)
    if not header:
        reasons.append("displayed_store_not_confirmed")
    selected = re.findall(r"^.*tab \(selected,[^\n]*ID: filmstrip-([0-9]+)[^\n]*$",
                          text, flags=re.MULTILINE)
    if selected != [publication]:
        reasons.append("selected_publication_mismatch")
    label = (f"Valide du {valid_from.day:02d} {MONTHS[valid_from.month - 1]} "
             f"au {valid_to.day:02d} {MONTHS[valid_to.month - 1]}")
    selected_lines = [line for line in text.splitlines()
                      if "tab (selected," in line and "ID: filmstrip-" in line]
    if len(selected_lines) != 1 or label not in selected_lines[0]:
        reasons.append("displayed_period_mismatch")
    return {
        "version": 1, "capture_kind": "browser_accessibility",
        "store_id": "iga-laval-cartier-ouest-307", "source_store_id": "8270",
        "expected_publication": publication,
        "expected_valid_from": valid_from.isoformat(),
        "expected_valid_to": valid_to.isoformat(),
        "context_checks_passed": not reasons,
        "context_issues": reasons,
        "year_verified": False,
        "complete_source_capture": False, "ready_for_archive": False,
        "limitations": ["Année attendue fournie par l'opérateur, non attestée par l'onglet.",
                        "Le contexte visible ne certifie ni les prix ni la portée du flux.",
                        "Capture structurée complète et validation commerciale requises."],
    }


def inspect_capture(path: Path, publication: str, valid_from: date, valid_to: date) -> Path:
    path = path.resolve()
    if not path.is_relative_to(Path("local").resolve()):
        raise ValueError("La capture doit rester sous local/.")
    raw = path.read_bytes()
    report = inspect_context(raw.decode("utf-8"), publication, valid_from, valid_to)
    report["capture_sha256"] = hashlib.sha256(raw).hexdigest()
    output = path.with_name(path.stem + "-context.json")
    write_json_atomic(output, report)
    return output
