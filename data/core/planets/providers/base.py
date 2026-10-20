"""
Abstract Base Class for planetary data providers.
"""

from abc import ABC, abstractmethod
from typing import Any
from astropy.coordinates import SkyCoord

from core.planets.models import PlanetRecord

class BasePlanetProvider(ABC):
    """
    Abstract interface for decoupled planet data providers.
    Supports querying by host star name, sky region, or known planet designation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the provider."""
        pass

    @abstractmethod
    def query_by_host_star(self, host_name: str, host_id: str | None = None, **kwargs: Any) -> list[PlanetRecord]:
        """Queries planets orbiting a specific host star."""
        pass

    @abstractmethod
    def query_by_region(self, center_coord: SkyCoord, radius_deg: float, **kwargs: Any) -> list[PlanetRecord]:
        """Queries planets within a cone / sky region."""
        pass

    @abstractmethod
    def get_known_planet(self, planet_name: str, **kwargs: Any) -> PlanetRecord | None:
        """Retrieves a specific known planet by its primary name or designation."""
        pass
