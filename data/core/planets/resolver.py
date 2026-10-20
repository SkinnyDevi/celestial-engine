"""
Planet Resolver
Coordinates planetary data providers (NASA Exoplanet Archive, Solar System, Rogue Planets)
under a low-coupled, extensible facade.
"""

from typing import Any
from astropy.coordinates import SkyCoord
from astropy.time import Time

from core.planets.models import PlanetRecord
from core.planets.providers import (
    BasePlanetProvider,
    NasaExoplanetProvider,
    RoguePlanetProvider,
    SolarSystemPlanetProvider,
)

class PlanetResolver:
    """
    Decoupled orchestrator for resolving all classes of celestial planets
    (terrestrial, gas giant, ice giant, dwarf, rogue) from respective providers.
    """

    def __init__(
        self,
        nasa_provider: BasePlanetProvider | None = None,
        solar_provider: BasePlanetProvider | None = None,
        rogue_provider: BasePlanetProvider | None = None,
    ) -> None:
        self.nasa_provider: BasePlanetProvider = (
            nasa_provider if nasa_provider is not None else NasaExoplanetProvider()
        )
        self.solar_provider: BasePlanetProvider = (
            solar_provider if solar_provider is not None else SolarSystemPlanetProvider()
        )
        self.rogue_provider: BasePlanetProvider = (
            rogue_provider if rogue_provider is not None else RoguePlanetProvider()
        )

    def resolve_planets_for_star(
        self,
        host_name: str,
        host_id: str | None = None,
        **kwargs: Any
    ) -> list[PlanetRecord]:
        """
        Resolves all planets orbiting a specified host star.
        Routes to Solar System provider for Sun/Sol, or NASA Exoplanet Archive for exoplanet hosts.
        """
        clean_name = host_name.strip()
        if clean_name.upper() in ("SUN", "SOL", "THE SUN"):
            return self.solar_provider.query_by_host_star(clean_name, host_id=host_id, **kwargs)

        return self.nasa_provider.query_by_host_star(clean_name, host_id=host_id, **kwargs)

    def resolve_planets_in_region(
        self,
        center_coord: SkyCoord,
        radius_deg: float,
        include_exoplanets: bool = True,
        include_rogue: bool = True,
        **kwargs: Any
    ) -> list[PlanetRecord]:
        """
        Discovers all planets within a cone of radius_deg around center_coord,
        including exoplanets around stars and free-floating rogue planets.
        """
        results: list[PlanetRecord] = []

        if include_exoplanets:
            exo = self.nasa_provider.query_by_region(center_coord, radius_deg, **kwargs)
            results.extend(exo)

        if include_rogue:
            rogues = self.rogue_provider.query_by_region(center_coord, radius_deg, **kwargs)
            results.extend(rogues)

        return results

    def resolve_exoplanets_by_distance(self, max_distance_pc: float, **kwargs: Any) -> list[PlanetRecord]:
        """Queries exoplanets within max_distance_pc of the Solar System (Sun)."""
        if hasattr(self.nasa_provider, "query_by_distance"):
            return self.nasa_provider.query_by_distance(max_distance_pc, **kwargs)
        return []

    def resolve_solar_system_planets(
        self,
        include_dwarf_planets: bool = True,
        sim_time: Time | None = None,
        **kwargs: Any
    ) -> list[PlanetRecord]:
        """Returns the Solar System planetary bodies (Mercury through Neptune + Pluto/Ceres)."""
        if isinstance(self.solar_provider, SolarSystemPlanetProvider):
            return self.solar_provider.get_all_planets(
                include_dwarf=include_dwarf_planets,
                sim_time=sim_time
            )
        return self.solar_provider.query_by_host_star("Sun", include_dwarf_planets=include_dwarf_planets, **kwargs)

    def resolve_rogue_planets(
        self,
        center_coord: SkyCoord | None = None,
        radius_deg: float | None = None,
        **kwargs: Any
    ) -> list[PlanetRecord]:
        """Returns rogue planets either across the sky or filtered by region."""
        if center_coord is not None and radius_deg is not None:
            return self.rogue_provider.query_by_region(center_coord, radius_deg, **kwargs)

        if isinstance(self.rogue_provider, RoguePlanetProvider):
            return self.rogue_provider.get_all_rogue_planets()

        return []

    def get_known_planet(self, planet_name: str, **kwargs: Any) -> PlanetRecord | None:
        """Finds a specific planet by name across all providers."""
        for provider in (self.solar_provider, self.rogue_provider, self.nasa_provider):
            p = provider.get_known_planet(planet_name, **kwargs)
            if p is not None:
                return p
        return None
