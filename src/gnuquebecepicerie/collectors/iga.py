from __future__ import annotations

from gnuquebecepicerie.collectors.base import Collector
from gnuquebecepicerie.models import Flyer


class IGACollector(Collector):
    retailer_id = "iga"
    public_flyer_url = "https://www.iga.net/fr/circulaire"

    def collect(self, store_id: str) -> Flyer:
        raise NotImplementedError(
            "Le collecteur IGA sera implémenté à la phase 1 "
            "après validation de la source structurée."
        )
