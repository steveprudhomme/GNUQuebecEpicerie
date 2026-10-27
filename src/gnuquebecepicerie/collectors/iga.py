from __future__ import annotations

from gnuquebecepicerie.collectors.base import Collector
from gnuquebecepicerie.models import Flyer


class IGACollector(Collector):
    retailer_id = "iga"
    public_flyer_url = "https://www.iga.ca/fr/circulaire"

    def collect(self, store_id: str) -> Flyer:
        raise NotImplementedError(
            "Le magasin IGA 8270 est identifié; le collecteur sera implémenté "
            "après validation de la source structurée."
        )
