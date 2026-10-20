"""
Base provider interface for natural satellites and moons.
"""

from abc import ABC, abstractmethod
from typing import Any
from astropy.coordinates import SkyCoord

from core.moons.models import MoonRecord


class BaseMoonProvider(ABC):
    """Abstract base class defining the contract for moon providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier."""
        pass

    @abstractmethod
    def query_by_host_planet(
        self,
        planet_name: str,
        host_id: str | None = None,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """Returns moons orbiting a specific host planet."""
        pass

    @abstractmethod
    def query_by_system(
        self,
        host_star_name: str,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """Returns all moons within a planetary system orbiting a given host star."""
        pass

    @abstractmethod
    def get_known_moon(
        self,
        moon_name: str,
        **kwargs: Any
    ) -> MoonRecord | None:
        """Retrieves a specific moon by name or body_id."""
        pass

    @abstractmethod
    def get_all_moons(
        self,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """Returns all known natural satellites provided by this source."""
        pass

    @abstractmethod
    def query_by_region(
        self,
        center_coord: SkyCoord,
        radius_deg: float,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """Discovers moons located within a cone around center_coord."""
        pass
