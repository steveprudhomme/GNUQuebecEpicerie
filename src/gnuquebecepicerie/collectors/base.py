from __future__ import annotations

from abc import ABC, abstractmethod

from gnuquebecepicerie.models import Flyer


class Collector(ABC):
    retailer_id: str

    @abstractmethod
    def collect(self, store_id: str) -> Flyer:
        """Collecte et normalise la circulaire courante du magasin."""
        raise NotImplementedError
