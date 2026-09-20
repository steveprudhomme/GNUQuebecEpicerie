from __future__ import annotations

from gnuquebecepicerie.collectors.base import Collector
from gnuquebecepicerie.models import Flyer


class SuperCCollector(Collector):
    retailer_id = "superc"
    public_flyer_url = "https://www.superc.ca/circulaire"

    def collect(self, store_id: str) -> Flyer:
        raise NotImplementedError(
            "Le collecteur Super C sera implémenté à la phase 1 "
            "après validation de la source structurée."
        )
