"""
Rogue Planet Provider
Provides known free-floating / interstellar rogue planetary-mass objects (FFPs)
unbound to any host star.
"""

from typing import Any
import math
from astropy.coordinates import SkyCoord
import astropy.units as astrounits

from core.constants import (
    DEG_TO_RAD,
    G_CONST,
    JUPITER_MASS_KG,
    JUPITER_RADIUS_M,
    PC_TO_METERS,
)
from core.space import PlanetClass, AtmosphereType
from core.planets.models import PlanetRecord, sanitize_planet_id
from core.planets.providers.base import BasePlanetProvider

class RoguePlanetProvider(BasePlanetProvider):
    """
    Decoupled provider for rogue / free-floating planets.
    Calculates 3D celestial coordinates from RA, Dec, and parallax distance.
    """

    @property
    def name(self) -> str:
        return "rogue_planets"

    def query_by_host_star(self, host_name: str, host_id: str | None = None, **kwargs: Any) -> list[PlanetRecord]:
        """Rogue planets have no host star; returns empty list for host queries."""
        return []

    def query_by_region(self, center_coord: SkyCoord, radius_deg: float, **kwargs: Any) -> list[PlanetRecord]:
        """Queries known rogue planets within a cone of radius_deg around center_coord."""
        all_rogues = self.get_all_rogue_planets()
        matches: list[PlanetRecord] = []

        for p in all_rogues:
            p_coord = SkyCoord(
                ra=p.right_ascension_rad * astrounits.rad,
                dec=p.declination_rad * astrounits.rad,
                distance=p.distance_pc * astrounits.pc
            )
            sep_deg = center_coord.separation(p_coord).deg
            if sep_deg <= radius_deg:
                matches.append(p)

        return matches

    def get_known_planet(self, planet_name: str, **kwargs: Any) -> PlanetRecord | None:
        """Retrieves a known rogue planet by designation."""
        target = planet_name.strip().upper()
        for p in self.get_all_rogue_planets():
            if p.name.upper() == target or p.body_id.upper() == target or target in p.name.upper():
                return p
        return None

    def get_all_rogue_planets(self) -> list[PlanetRecord]:
        """Returns catalog of known confirmed free-floating rogue planets."""
        specs = self._get_rogue_specs()
        records: list[PlanetRecord] = []

        for spec in specs:
            name, body_id = sanitize_planet_id(spec["name"], fallback_prefix="ROGUE")
            ra_deg = spec["ra_deg"]
            dec_deg = spec["dec_deg"]
            dist_pc = spec["distance_pc"]

            ra_rad = ra_deg * DEG_TO_RAD
            dec_rad = dec_deg * DEG_TO_RAD
            dist_m = dist_pc * PC_TO_METERS

            # 3D spatial position in interstellar coordinates
            x = dist_m * math.cos(dec_rad) * math.cos(ra_rad)
            y = dist_m * math.cos(dec_rad) * math.sin(ra_rad)
            z = dist_m * math.sin(dec_rad)

            mass = spec["mass_kg"]
            radius = spec["radius_m"]
            gravity = spec.get("surface_gravity_m_s2", (G_CONST * mass) / (radius ** 2))
            vol = (4.0 / 3.0) * math.pi * (radius ** 3)
            density = spec.get("density_kg_m3", mass / vol)

            p = PlanetRecord(
                name=name,
                body_id=body_id,
                host_star_name=None,
                host_star_id=None,
                host_star_index=-1,
                orbit_index=-1,
                planet_class=PlanetClass.ROGUE,
                atmosphere_type=spec.get("atmosphere_type", AtmosphereType.THICK_ENVELOPE),
                position={"x": x, "y": y, "z": z},
                right_ascension_rad=ra_rad,
                declination_rad=dec_rad,
                distance_pc=dist_pc,
                semi_major_axis_au=0.0,
                eccentricity=0.0,
                inclination_rad=0.0,
                longitude_ascending_node_rad=0.0,
                argument_periapsis_rad=0.0,
                mean_anomaly_rad=0.0,
                orbital_period_days=0.0,
                mass_kg=mass,
                radius_m=radius,
                density_kg_m3=density,
                surface_gravity_m_s2=gravity,
                albedo=spec.get("albedo", 0.1),
                surface_temperature_k=spec["surface_temperature_k"],
                axial_tilt_rad=spec.get("axial_tilt_rad", 0.0),
                rotation_period_days=spec.get("rotation_period_days", 0.3),
                magnetic_field_gauss=spec.get("magnetic_field_gauss", 10.0),
                surface_pressure_pa=spec.get("surface_pressure_pa", 1e7),
                has_rings=spec.get("has_rings", 0),
                ring_inner_radius_m=spec.get("ring_inner_radius_m", 0.0),
                ring_outer_radius_m=spec.get("ring_outer_radius_m", 0.0),
                orbit=None,
                extra_metadata={"type": "rogue_planet", "spectral_type": spec.get("spectral_type")}
            )
            records.append(p)

        return records

    @staticmethod
    def _get_rogue_specs() -> list[dict[str, Any]]:
        return [
            # 1. PSO J318.5-22 (beta Pictoris moving group free-floating planet)
            {
                "name": "PSO J318.5-22",
                "ra_deg": 318.5133,
                "dec_deg": -22.8608,
                "distance_pc": 24.6,
                "mass_kg": 6.5 * JUPITER_MASS_KG,
                "radius_m": 1.53 * JUPITER_RADIUS_M,
                "surface_temperature_k": 1160.0,
                "atmosphere_type": AtmosphereType.THICK_ENVELOPE,
                "rotation_period_days": 0.29,  # ~7 hours
                "magnetic_field_gauss": 20.0,
                "albedo": 0.08,
                "spectral_type": "L7"
            },
            # 2. SIMP J013656.5+093347 (Giant magnetic aurora rogue planet)
            {
                "name": "SIMP J013656.5+093347",
                "ra_deg": 24.2333,
                "dec_deg": 9.5578,
                "distance_pc": 6.13,
                "mass_kg": 12.7 * JUPITER_MASS_KG,
                "radius_m": 1.22 * JUPITER_RADIUS_M,
                "surface_temperature_k": 1098.0,
                "atmosphere_type": AtmosphereType.THICK_ENVELOPE,
                "rotation_period_days": 0.10,  # ~2.4 hours
                "magnetic_field_gauss": 16000.0,  # Highly magnetized ~1.6 Tesla
                "albedo": 0.05,
                "spectral_type": "T2.5"
            },
            # 3. OTS 44 (Chamaeleon I cloud rogue gas planet)
            {
                "name": "OTS 44",
                "ra_deg": 167.3308,
                "dec_deg": -77.8631,
                "distance_pc": 160.0,
                "mass_kg": 11.5 * JUPITER_MASS_KG,
                "radius_m": 1.40 * JUPITER_RADIUS_M,
                "surface_temperature_k": 2000.0,
                "atmosphere_type": AtmosphereType.THICK_ENVELOPE,
                "rotation_period_days": 0.40,
                "magnetic_field_gauss": 50.0,
                "albedo": 0.05,
                "spectral_type": "M9.5"
            },
            # 4. CFBDSIR 2149-0403 (AB Doradus moving group isolated exoplanet candidate)
            {
                "name": "CFBDSIR 2149-0403",
                "ra_deg": 327.3104,
                "dec_deg": -4.0494,
                "distance_pc": 40.0,
                "mass_kg": 5.5 * JUPITER_MASS_KG,
                "radius_m": 1.30 * JUPITER_RADIUS_M,
                "surface_temperature_k": 670.0,
                "atmosphere_type": AtmosphereType.THICK_ENVELOPE,
                "rotation_period_days": 0.35,
                "magnetic_field_gauss": 15.0,
                "albedo": 0.10,
                "spectral_type": "T7"
            },
            # 5. Cha 110913-773444 (Young rogue planet with circumstellar dust disc)
            {
                "name": "Cha 110913-773444",
                "ra_deg": 167.3075,
                "dec_deg": -77.5794,
                "distance_pc": 163.0,
                "mass_kg": 8.0 * JUPITER_MASS_KG,
                "radius_m": 1.80 * JUPITER_RADIUS_M,
                "surface_temperature_k": 1350.0,
                "atmosphere_type": AtmosphereType.THICK_ENVELOPE,
                "has_rings": 1,
                "ring_inner_radius_m": 3.0 * JUPITER_RADIUS_M,
                "ring_outer_radius_m": 15.0 * JUPITER_RADIUS_M,
                "rotation_period_days": 0.30,
                "magnetic_field_gauss": 30.0,
                "albedo": 0.07,
                "spectral_type": "L0"
            }
        ]
