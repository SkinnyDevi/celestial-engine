"""
Moon Resolver
Coordinates natural satellite data providers (Solar System moons, Exomoons, JPL Horizons)
under a low-coupled, extensible facade.
"""

from typing import Any
from astropy.coordinates import SkyCoord
from astropy.time import Time

from core.moons.models import MoonRecord
from core.moons.providers import (
    BaseMoonProvider,
    SolarSystemMoonProvider,
    ExomoonProvider,
    JPLHorizonsMoonProvider,
)


class MoonResolver:
    """
    Decoupled orchestrator for resolving natural satellites and moons across the universe
    from their respective providers (Solar System, Extrasolar, and Ephemerides).
    """

    def __init__(
        self,
        solar_provider: BaseMoonProvider | None = None,
        exomoon_provider: BaseMoonProvider | None = None,
        jpl_provider: BaseMoonProvider | None = None,
    ) -> None:
        self.solar_provider: BaseMoonProvider = (
            solar_provider if solar_provider is not None else SolarSystemMoonProvider()
        )
        self.exomoon_provider: BaseMoonProvider = (
            exomoon_provider if exomoon_provider is not None else ExomoonProvider()
        )
        self.jpl_provider: BaseMoonProvider = (
            jpl_provider if jpl_provider is not None else JPLHorizonsMoonProvider()
        )

    def resolve_moons_for_planet(
        self,
        planet_name: str,
        host_id: str | None = None,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """
        Resolves natural satellites orbiting a specified host planet.
        Gracefully handles the case where the Sun is passed as a planet (the Sun is a star,
        so it directly hosts zero moons).
        """
        clean_name = planet_name.strip().upper()
        if clean_name in ("SUN", "SOL", "THE SUN"):
            print("Notice: 'Sun' is a central star, not a planet. Moons orbit planets. No direct moons exist for the Sun.")
            return []

        # 1. Check Solar System moons
        solar_moons = self.solar_provider.query_by_host_planet(planet_name, host_id=host_id, **kwargs)
        if solar_moons:
            return solar_moons

        # 2. Check Exomoons
        exo_moons = self.exomoon_provider.query_by_host_planet(planet_name, host_id=host_id, **kwargs)
        if exo_moons:
            return exo_moons

        return []

    def resolve_moons_for_star(
        self,
        star_name: str,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """
        Resolves all moons in the planetary system of a specified host star.
        For the Sun/Sol, returns all Solar System moons mapped to their host planets.
        For exoplanet host stars, returns the corresponding exomoons.
        """
        clean_name = star_name.strip().upper()
        if clean_name in ("SUN", "SOL", "THE SUN"):
            return self.solar_provider.query_by_system("Sun", **kwargs)

        return self.exomoon_provider.query_by_system(star_name, **kwargs)

    def resolve_moons_for_system(self, system_name: str, **kwargs: Any) -> list[MoonRecord]:
        """Alias for resolve_moons_for_star."""
        return self.resolve_moons_for_star(system_name, **kwargs)

    def resolve_all_universe_moons(self, **kwargs: Any) -> list[MoonRecord]:
        """
        Returns all known universe moons across both the Solar System and extrasolar planetary systems.
        """
        all_moons: list[MoonRecord] = []
        all_moons.extend(self.solar_provider.get_all_moons(**kwargs))
        all_moons.extend(self.exomoon_provider.get_all_moons(**kwargs))
        return all_moons

    def get_known_moon(self, moon_name: str, **kwargs: Any) -> MoonRecord | None:
        """
        Finds a specific natural satellite by name across all providers.
        Throws a clear ValueError if the Sun is queried as a moon.
        """
        clean_name = moon_name.strip().upper()
        if clean_name in ("SUN", "SOL", "THE SUN"):
            raise ValueError("The Sun is a star, not a natural satellite or moon.")

        for provider in (self.solar_provider, self.exomoon_provider, self.jpl_provider):
            m = provider.get_known_moon(moon_name, **kwargs)
            if m is not None:
                return m
        return None

    def resolve_moons_in_region(
        self,
        center: str | SkyCoord,
        radius_deg: float,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """
        Discovers natural satellites in a celestial region.
        Properly handles exceptions when querying the Sun as target:
        When center is 'Sun' or 'Sol', avoids catalog coordinate lookups and returns Solar System moons.
        """
        if isinstance(center, str) and center.strip().upper() in ("SUN", "SOL", "THE SUN"):
            # Target is the Sun: return all Solar System moons
            return self.resolve_moons_for_star("Sun", **kwargs)

        if isinstance(center, str):
            from core.catalogs import resolve_center_coord
            center_coord = resolve_center_coord(center)
        else:
            center_coord = center

        results: list[MoonRecord] = []

        # Check exomoons in region
        exo = self.exomoon_provider.query_by_region(center_coord, radius_deg, **kwargs)
        results.extend(exo)

        # Include Solar System moons if requested
        if kwargs.get("include_solar_system", False):
            results.extend(self.solar_provider.get_all_moons(**kwargs))

        return results
