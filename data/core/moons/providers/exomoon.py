"""
Exomoon Provider
Provides known candidate and extrasolar natural satellites orbiting confirmed exoplanets
across the universe (e.g., Kepler-1625b I, Kepler-1708b I).
"""

from typing import Any
import math
from astropy.coordinates import SkyCoord
from astropy.time import Time

from core.constants import DEG_TO_RAD, EARTH_MASS_KG, EARTH_RADIUS_M, G_CONST
from core.space import MoonClass, AtmosphereType
from core.planets.models import OrbitRecord
from core.moons.models import MoonRecord, sanitize_moon_id
from core.moons.coords import keplerian_to_cartesian_moon
from core.moons.providers.base import BaseMoonProvider


class ExomoonProvider(BaseMoonProvider):
    """
    Decoupled provider for extrasolar moons (exomoons) and natural satellites
    orbiting extrasolar planets in confirmed stellar systems.
    """

    @property
    def name(self) -> str:
        return "exomoons"

    def query_by_host_planet(
        self,
        planet_name: str,
        host_id: str | None = None,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """Returns exomoons orbiting a specified host exoplanet."""
        clean_name = planet_name.strip().upper()
        all_exomoons = self.get_all_moons(sim_time=kwargs.get("sim_time"))
        matching: list[MoonRecord] = []
        for m in all_exomoons:
            if m.host_planet_name.upper() == clean_name:
                matching.append(m)
            elif m.host_planet_id and m.host_planet_id.upper() == clean_name:
                matching.append(m)
            elif host_id and m.host_planet_id and m.host_planet_id.upper() == host_id.strip().upper():
                matching.append(m)
        return matching

    def query_by_system(
        self,
        host_star_name: str,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """Returns all exomoons belonging to planets orbiting a specific host star."""
        clean_name = host_star_name.strip().upper()
        if clean_name in ("SUN", "SOL", "THE SUN"):
            return []  # Sun has no exomoons

        all_exomoons = self.get_all_moons(sim_time=kwargs.get("sim_time"))
        matching: list[MoonRecord] = []
        for m in all_exomoons:
            star_ref = m.extra_metadata.get("host_star_name", "").upper()
            if star_ref == clean_name or clean_name in star_ref or star_ref in clean_name:
                matching.append(m)
        return matching

    def get_known_moon(
        self,
        moon_name: str,
        **kwargs: Any
    ) -> MoonRecord | None:
        """Finds an exomoon by name or body ID."""
        target = moon_name.strip().upper()
        all_exomoons = self.get_all_moons(sim_time=kwargs.get("sim_time"))
        for m in all_exomoons:
            if m.name.upper() == target or m.body_id.upper() == target:
                return m
        return None

    def query_by_region(
        self,
        center_coord: SkyCoord,
        radius_deg: float,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """Returns exomoons located within radius_deg of center_coord."""
        all_exomoons = self.get_all_moons(sim_time=kwargs.get("sim_time"))
        matching: list[MoonRecord] = []
        for m in all_exomoons:
            ra_deg = m.extra_metadata.get("ra_deg")
            dec_deg = m.extra_metadata.get("dec_deg")
            if ra_deg is not None and dec_deg is not None:
                coord = SkyCoord(ra=ra_deg, dec=dec_deg, unit="deg")
                sep_deg = float(center_coord.separation(coord).deg)
                if sep_deg <= radius_deg:
                    matching.append(m)
        return matching

    def get_all_moons(self, sim_time: Time | None = None) -> list[MoonRecord]:
        """Builds and returns MoonRecords for known extrasolar natural satellites."""
        specs = self._get_exomoon_specs()
        records: list[MoonRecord] = []

        for spec in specs:
            a_km = spec["semi_major_axis_km"]
            e = spec["eccentricity"]
            inc_rad = spec["inclination_rad"]
            node_rad = spec["longitude_ascending_node_rad"]
            peri_rad = spec["argument_periapsis_rad"]
            m_rad = spec["mean_anomaly_rad"]
            period_days = spec["orbital_period_days"]

            pos, _, nu = keplerian_to_cartesian_moon(
                semimajor_axis_km=a_km,
                eccentricity=e,
                inclination_rad=inc_rad,
                longitude_ascending_node_rad=node_rad,
                argument_periapsis_rad=peri_rad,
                mean_anomaly_rad=m_rad,
            )

            a_m = a_km * 1000.0
            orbit = OrbitRecord(
                semimajor_axis=a_m,
                eccentricity=e,
                inclination=inc_rad,
                longitude_of_ascending_node=node_rad,
                argument_of_periapsis=peri_rad,
                mean_anomaly_at_epoch=m_rad,
                orbital_period_days=period_days,
                mean_anomaly=m_rad,
                true_anomaly=nu,
                center_position={"x": 0.0, "y": 0.0, "z": 0.0},
            )

            mass = spec["mass_kg"]
            radius = spec["radius_m"]
            gravity = spec.get("surface_gravity_m_s2", (G_CONST * mass) / (radius ** 2) if radius > 0 else 0.0)

            rec = MoonRecord(
                name=spec["name"],
                body_id=spec["body_id"],
                host_planet_name=spec["host_planet_name"],
                host_planet_id=spec["host_planet_id"],
                moon_class=spec["moon_class"],
                atmosphere_type=spec.get("atmosphere_type", AtmosphereType.NONE),
                position=pos,
                semi_major_axis_km=a_km,
                eccentricity=e,
                inclination_rad=inc_rad,
                longitude_ascending_node_rad=node_rad,
                argument_periapsis_rad=peri_rad,
                mean_anomaly_rad=m_rad,
                orbital_period_days=period_days,
                mass_kg=mass,
                radius_m=radius,
                surface_gravity_m_s2=gravity,
                is_tidally_locked=spec.get("is_tidally_locked", 1),
                axial_tilt_rad=spec.get("axial_tilt_rad", 0.0),
                rotation_period_days=spec.get("rotation_period_days", period_days),
                albedo=spec.get("albedo", 0.35),
                surface_temperature_k=spec.get("surface_temperature_k", 250.0),
                surface_pressure_pa=spec.get("surface_pressure_pa", 1000.0),
                orbit=orbit,
                extra_metadata={
                    "host_star_name": spec.get("host_star_name"),
                    "host_star_id": spec.get("host_star_id"),
                    "ra_deg": spec.get("ra_deg"),
                    "dec_deg": spec.get("dec_deg"),
                    "distance_pc": spec.get("distance_pc"),
                },
            )
            records.append(rec)

        return records

    @staticmethod
    def _get_exomoon_specs() -> list[dict[str, Any]]:
        return [
            # 1. Kepler-1625b I (First candidate exomoon, Neptune-sized companion)
            {
                "name": "Kepler-1625b I", "body_id": "KEPLER_1625B_I",
                "host_planet_name": "Kepler-1625 b", "host_planet_id": "KEPLER_1625_B",
                "host_star_name": "Kepler-1625", "host_star_id": "KEPLER_1625",
                "moon_class": MoonClass.ICY,
                "radius_m": 3.0 * EARTH_RADIUS_M,  # Neptune-sized satellite (~19,100 km)
                "mass_kg": 19.0 * EARTH_MASS_KG,
                "surface_temperature_k": 253.0,
                "atmosphere_type": AtmosphereType.THICK_ENVELOPE,
                "surface_pressure_pa": 500000.0,
                "is_tidally_locked": 1,
                "rotation_period_days": 28.7,
                "albedo": 0.35,
                "semi_major_axis_km": 3000000.0,  # ~3 million km orbit (~40 planetary radii)
                "eccentricity": 0.05,
                "inclination_rad": 1.2 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 45.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 110.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 60.0 * DEG_TO_RAD,
                "orbital_period_days": 28.7,
                "ra_deg": 290.3705,
                "dec_deg": 39.9575,
                "distance_pc": 2465.0,
            },
            # 2. Kepler-1708b I (Candidate super-Earth/mini-Neptune exomoon)
            {
                "name": "Kepler-1708b I", "body_id": "KEPLER_1708B_I",
                "host_planet_name": "Kepler-1708 b", "host_planet_id": "KEPLER_1708_B",
                "host_star_name": "Kepler-1708", "host_star_id": "KEPLER_1708",
                "moon_class": MoonClass.ICY,
                "radius_m": 2.61 * EARTH_RADIUS_M,  # Mini-Neptune exomoon (~16,600 km)
                "mass_kg": 37.0 * EARTH_MASS_KG,
                "surface_temperature_k": 200.0,
                "atmosphere_type": AtmosphereType.THICK_ENVELOPE,
                "surface_pressure_pa": 300000.0,
                "is_tidally_locked": 1,
                "rotation_period_days": 4.6,
                "albedo": 0.3,
                "semi_major_axis_km": 740000.0,  # ~740,000 km orbit (~12 planetary radii)
                "eccentricity": 0.01,
                "inclination_rad": 0.5 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 30.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 45.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 120.0 * DEG_TO_RAD,
                "orbital_period_days": 4.6,
                "ra_deg": 298.1345,
                "dec_deg": 42.4764,
                "distance_pc": 1668.0,
            },
            # 3. DH Tauri b I (Massive satellite companion)
            {
                "name": "DH Tauri b I", "body_id": "DH_TAURI_B_I",
                "host_planet_name": "DH Tauri b", "host_planet_id": "DH_TAURI_B",
                "host_star_name": "DH Tauri", "host_star_id": "DH_TAURI",
                "moon_class": MoonClass.ROCKY,
                "radius_m": 1.2 * EARTH_RADIUS_M,
                "mass_kg": 2.0 * EARTH_MASS_KG,
                "surface_temperature_k": 180.0,
                "atmosphere_type": AtmosphereType.THIN,
                "surface_pressure_pa": 10000.0,
                "is_tidally_locked": 1,
                "rotation_period_days": 10.5,
                "albedo": 0.25,
                "semi_major_axis_km": 1500000.0,
                "eccentricity": 0.08,
                "inclination_rad": 2.0 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 80.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 30.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 200.0 * DEG_TO_RAD,
                "orbital_period_days": 10.5,
                "ra_deg": 65.4196,
                "dec_deg": 27.7289,
                "distance_pc": 133.0,
            },
        ]
