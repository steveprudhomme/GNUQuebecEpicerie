from __future__ import annotations

import re

_SPACES = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """Nettoie les espaces sans modifier le contenu sémantique."""
    return _SPACES.sub(" ", value).strip()


def parse_price_fr(value: str) -> float:
    """Convertit un prix québécois simple (ex. '4,99 $') en nombre."""
    cleaned = value.replace("$", "").replace(" ", " ").strip().replace(" ", "")
    cleaned = cleaned.replace(",", ".")
    return float(cleaned)
