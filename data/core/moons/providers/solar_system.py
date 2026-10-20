"""
Solar System Moon Provider
Provides high-precision physical and orbital parameters for all major and minor natural satellites
in the Solar System (Earth, Mars, Jupiter, Saturn, Uranus, Neptune, and Pluto systems).
"""

from typing import Any
import math
from astropy.coordinates import SkyCoord
from astropy.time import Time

from core.constants import DEG_TO_RAD, G_CONST
from core.space import MoonClass, AtmosphereType
from core.planets.models import OrbitRecord
from core.moons.models import MoonRecord, sanitize_moon_id
from core.moons.coords import keplerian_to_cartesian_moon
from core.moons.providers.base import BaseMoonProvider


class SolarSystemMoonProvider(BaseMoonProvider):
    """
    Decoupled Solar System provider containing precision IAU/NASA parameters
    for all major and notable minor moons of the Solar System.
    """

    @property
    def name(self) -> str:
        return "solar_system_moons"

    def query_by_host_planet(
        self,
        planet_name: str,
        host_id: str | None = None,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """
        Returns natural satellites orbiting a specified Solar System planet.
        If querying for the Sun, returns an empty list (the Sun is a star, not a planet).
        """
        clean_name = planet_name.strip().upper()
        if clean_name in ("SUN", "SOL", "THE SUN"):
            # The Sun is a star and does not host moons directly
            return []

        all_moons = self.get_all_moons(sim_time=kwargs.get("sim_time"))
        matching: list[MoonRecord] = []
        for m in all_moons:
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
        """
        Returns all moons within the Solar System when querying for the Sun/Sol.
        """
        clean_name = host_star_name.strip().upper()
        if clean_name in ("SUN", "SOL", "THE SUN"):
            include_dwarf = kwargs.get("include_dwarf_planet_moons", True)
            all_moons = self.get_all_moons(sim_time=kwargs.get("sim_time"))
            if not include_dwarf:
                all_moons = [m for m in all_moons if m.host_planet_name.upper() != "PLUTO"]
            return all_moons
        return []

    def get_known_moon(
        self,
        moon_name: str,
        **kwargs: Any
    ) -> MoonRecord | None:
        """Retrieves a specific Solar System moon by name or body_id."""
        target = moon_name.strip().upper()
        all_moons = self.get_all_moons(sim_time=kwargs.get("sim_time"))
        for m in all_moons:
            if m.name.upper() == target or m.body_id.upper() == target:
                return m
        return None

    def query_by_region(
        self,
        center_coord: SkyCoord,
        radius_deg: float,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """Returns Solar System moons if explicitly requested in region."""
        if kwargs.get("include_solar_system", False):
            return self.get_all_moons(sim_time=kwargs.get("sim_time"))
        return []

    def get_all_moons(self, sim_time: Time | None = None) -> list[MoonRecord]:
        """Builds and returns MoonRecords for all curated Solar System natural satellites."""
        specs = self._get_solar_system_moon_specs()
        records: list[MoonRecord] = []

        for spec in specs:
            a_km = spec["semi_major_axis_km"]
            e = spec["eccentricity"]
            inc_rad = spec["inclination_rad"]
            node_rad = spec["longitude_ascending_node_rad"]
            peri_rad = spec["argument_periapsis_rad"]
            m_rad = spec["mean_anomaly_rad"]
            period_days = spec["orbital_period_days"]

            # Compute accurate 3D position vector in meters relative to host planet center
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
                albedo=spec.get("albedo", 0.3),
                surface_temperature_k=spec.get("surface_temperature_k", 100.0),
                surface_pressure_pa=spec.get("surface_pressure_pa", 0.0),
                orbit=orbit,
                extra_metadata={"jpl_id": spec.get("jpl_id")},
            )
            records.append(rec)

        return records

    @staticmethod
    def _get_solar_system_moon_specs() -> list[dict[str, Any]]:
        return [
            # =================================================================
            # EARTH (Host: Earth / EARTH)
            # =================================================================
            {
                "name": "Moon", "body_id": "LUNA", "jpl_id": "301",
                "host_planet_name": "Earth", "host_planet_id": "EARTH",
                "moon_class": MoonClass.ROCKY,
                "radius_m": 1737400.0, "mass_kg": 7.342e22,
                "surface_temperature_k": 250.0,
                "atmosphere_type": AtmosphereType.NONE,
                "surface_pressure_pa": 1e-10,
                "is_tidally_locked": 1,
                "axial_tilt_rad": 0.0269 * DEG_TO_RAD,
                "rotation_period_days": 27.321661,
                "albedo": 0.12,
                "semi_major_axis_km": 384400.0,
                "eccentricity": 0.0549,
                "inclination_rad": 5.145 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 125.08 * DEG_TO_RAD,
                "argument_periapsis_rad": 318.15 * DEG_TO_RAD,
                "mean_anomaly_rad": 135.27 * DEG_TO_RAD,
                "orbital_period_days": 27.321661,
            },

            # =================================================================
            # MARS (Host: Mars / MARS)
            # =================================================================
            {
                "name": "Phobos", "body_id": "PHOBOS", "jpl_id": "401",
                "host_planet_name": "Mars", "host_planet_id": "MARS",
                "moon_class": MoonClass.CAPTURED,
                "radius_m": 11262.0, "mass_kg": 1.0659e16,
                "surface_temperature_k": 233.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 0.3189,
                "albedo": 0.071,
                "semi_major_axis_km": 9376.0,
                "eccentricity": 0.0151,
                "inclination_rad": 1.093 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 169.5 * DEG_TO_RAD,
                "argument_periapsis_rad": 150.1 * DEG_TO_RAD,
                "mean_anomaly_rad": 180.0 * DEG_TO_RAD,
                "orbital_period_days": 0.3189,
            },
            {
                "name": "Deimos", "body_id": "DEIMOS", "jpl_id": "402",
                "host_planet_name": "Mars", "host_planet_id": "MARS",
                "moon_class": MoonClass.CAPTURED,
                "radius_m": 6255.0, "mass_kg": 1.4762e15,
                "surface_temperature_k": 233.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 1.263,
                "albedo": 0.068,
                "semi_major_axis_km": 23463.0,
                "eccentricity": 0.00033,
                "inclination_rad": 0.93 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 54.3 * DEG_TO_RAD,
                "argument_periapsis_rad": 260.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 90.0 * DEG_TO_RAD,
                "orbital_period_days": 1.263,
            },

            # =================================================================
            # JUPITER (Host: Jupiter / JUPITER)
            # =================================================================
            {
                "name": "Amalthea", "body_id": "AMALTHEA", "jpl_id": "505",
                "host_planet_name": "Jupiter", "host_planet_id": "JUPITER",
                "moon_class": MoonClass.CAPTURED,
                "radius_m": 83500.0, "mass_kg": 2.08e18,
                "surface_temperature_k": 125.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 0.498,
                "albedo": 0.09,
                "semi_major_axis_km": 181366.0,
                "eccentricity": 0.0032,
                "inclination_rad": 0.374 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 10.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 20.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 45.0 * DEG_TO_RAD,
                "orbital_period_days": 0.498,
            },
            {
                "name": "Io", "body_id": "IO", "jpl_id": "501",
                "host_planet_name": "Jupiter", "host_planet_id": "JUPITER",
                "moon_class": MoonClass.VOLCANIC,
                "radius_m": 1821600.0, "mass_kg": 8.9319e22,
                "surface_temperature_k": 130.0,
                "atmosphere_type": AtmosphereType.THIN,
                "surface_pressure_pa": 1e-4,
                "is_tidally_locked": 1,
                "rotation_period_days": 1.769,
                "albedo": 0.63,
                "semi_major_axis_km": 421700.0,
                "eccentricity": 0.0041,
                "inclination_rad": 0.050 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 43.8 * DEG_TO_RAD,
                "argument_periapsis_rad": 84.1 * DEG_TO_RAD,
                "mean_anomaly_rad": 142.9 * DEG_TO_RAD,
                "orbital_period_days": 1.769,
            },
            {
                "name": "Europa", "body_id": "EUROPA", "jpl_id": "502",
                "host_planet_name": "Jupiter", "host_planet_id": "JUPITER",
                "moon_class": MoonClass.ICY,
                "radius_m": 1560800.0, "mass_kg": 4.7998e22,
                "surface_temperature_k": 102.0,
                "atmosphere_type": AtmosphereType.THIN,
                "surface_pressure_pa": 1e-7,
                "is_tidally_locked": 1,
                "rotation_period_days": 3.551,
                "albedo": 0.67,
                "semi_major_axis_km": 670900.0,
                "eccentricity": 0.009,
                "inclination_rad": 0.471 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 219.1 * DEG_TO_RAD,
                "argument_periapsis_rad": 66.3 * DEG_TO_RAD,
                "mean_anomaly_rad": 312.4 * DEG_TO_RAD,
                "orbital_period_days": 3.551,
            },
            {
                "name": "Ganymede", "body_id": "GANYMEDE", "jpl_id": "503",
                "host_planet_name": "Jupiter", "host_planet_id": "JUPITER",
                "moon_class": MoonClass.ICY,
                "radius_m": 2634100.0, "mass_kg": 1.4819e23,
                "surface_temperature_k": 110.0,
                "atmosphere_type": AtmosphereType.THIN,
                "surface_pressure_pa": 1e-6,
                "is_tidally_locked": 1,
                "rotation_period_days": 7.154,
                "albedo": 0.43,
                "semi_major_axis_km": 1070400.0,
                "eccentricity": 0.0013,
                "inclination_rad": 0.204 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 63.6 * DEG_TO_RAD,
                "argument_periapsis_rad": 192.4 * DEG_TO_RAD,
                "mean_anomaly_rad": 89.2 * DEG_TO_RAD,
                "orbital_period_days": 7.154,
            },
            {
                "name": "Callisto", "body_id": "CALLISTO", "jpl_id": "504",
                "host_planet_name": "Jupiter", "host_planet_id": "JUPITER",
                "moon_class": MoonClass.ICY,
                "radius_m": 2410300.0, "mass_kg": 1.0759e23,
                "surface_temperature_k": 134.0,
                "atmosphere_type": AtmosphereType.THIN,
                "surface_pressure_pa": 7.5e-7,
                "is_tidally_locked": 1,
                "rotation_period_days": 16.689,
                "albedo": 0.22,
                "semi_major_axis_km": 1882700.0,
                "eccentricity": 0.0074,
                "inclination_rad": 0.281 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 298.8 * DEG_TO_RAD,
                "argument_periapsis_rad": 52.6 * DEG_TO_RAD,
                "mean_anomaly_rad": 25.1 * DEG_TO_RAD,
                "orbital_period_days": 16.689,
            },
            {
                "name": "Himalia", "body_id": "HIMALIA", "jpl_id": "506",
                "host_planet_name": "Jupiter", "host_planet_id": "JUPITER",
                "moon_class": MoonClass.CAPTURED,
                "radius_m": 69800.0, "mass_kg": 4.2e18,
                "surface_temperature_k": 120.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 0,
                "rotation_period_days": 0.324,
                "albedo": 0.05,
                "semi_major_axis_km": 11460000.0,
                "eccentricity": 0.162,
                "inclination_rad": 27.5 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 120.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 305.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 15.0 * DEG_TO_RAD,
                "orbital_period_days": 250.56,
            },

            # =================================================================
            # SATURN (Host: Saturn / SATURN)
            # =================================================================
            {
                "name": "Mimas", "body_id": "MIMAS", "jpl_id": "601",
                "host_planet_name": "Saturn", "host_planet_id": "SATURN",
                "moon_class": MoonClass.ICY,
                "radius_m": 198200.0, "mass_kg": 3.75e19,
                "surface_temperature_k": 64.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 0.942,
                "albedo": 0.96,
                "semi_major_axis_km": 185520.0,
                "eccentricity": 0.0202,
                "inclination_rad": 1.574 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 153.2 * DEG_TO_RAD,
                "argument_periapsis_rad": 12.3 * DEG_TO_RAD,
                "mean_anomaly_rad": 210.0 * DEG_TO_RAD,
                "orbital_period_days": 0.942,
            },
            {
                "name": "Enceladus", "body_id": "ENCELADUS", "jpl_id": "602",
                "host_planet_name": "Saturn", "host_planet_id": "SATURN",
                "moon_class": MoonClass.ICY,
                "radius_m": 252100.0, "mass_kg": 1.08e20,
                "surface_temperature_k": 75.0,
                "atmosphere_type": AtmosphereType.THIN,
                "is_tidally_locked": 1,
                "rotation_period_days": 1.370,
                "albedo": 0.99,
                "semi_major_axis_km": 238020.0,
                "eccentricity": 0.0047,
                "inclination_rad": 0.009 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 94.3 * DEG_TO_RAD,
                "argument_periapsis_rad": 284.1 * DEG_TO_RAD,
                "mean_anomaly_rad": 45.8 * DEG_TO_RAD,
                "orbital_period_days": 1.370,
            },
            {
                "name": "Tethys", "body_id": "TETHYS", "jpl_id": "603",
                "host_planet_name": "Saturn", "host_planet_id": "SATURN",
                "moon_class": MoonClass.ICY,
                "radius_m": 531100.0, "mass_kg": 6.17e20,
                "surface_temperature_k": 86.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 1.888,
                "albedo": 0.8,
                "semi_major_axis_km": 294660.0,
                "eccentricity": 0.0001,
                "inclination_rad": 1.12 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 330.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 15.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 170.0 * DEG_TO_RAD,
                "orbital_period_days": 1.888,
            },
            {
                "name": "Dione", "body_id": "DIONE", "jpl_id": "604",
                "host_planet_name": "Saturn", "host_planet_id": "SATURN",
                "moon_class": MoonClass.ICY,
                "radius_m": 561400.0, "mass_kg": 1.095e21,
                "surface_temperature_k": 87.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 2.737,
                "albedo": 0.6,
                "semi_major_axis_km": 377400.0,
                "eccentricity": 0.0022,
                "inclination_rad": 0.019 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 168.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 182.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 290.0 * DEG_TO_RAD,
                "orbital_period_days": 2.737,
            },
            {
                "name": "Rhea", "body_id": "RHEA", "jpl_id": "605",
                "host_planet_name": "Saturn", "host_planet_id": "SATURN",
                "moon_class": MoonClass.ICY,
                "radius_m": 763800.0, "mass_kg": 2.306e21,
                "surface_temperature_k": 76.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 4.518,
                "albedo": 0.95,
                "semi_major_axis_km": 527040.0,
                "eccentricity": 0.00125,
                "inclination_rad": 0.345 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 310.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 240.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 330.0 * DEG_TO_RAD,
                "orbital_period_days": 4.518,
            },
            {
                "name": "Titan", "body_id": "TITAN", "jpl_id": "606",
                "host_planet_name": "Saturn", "host_planet_id": "SATURN",
                "moon_class": MoonClass.ROCKY,
                "radius_m": 2574700.0, "mass_kg": 1.3452e23,
                "surface_temperature_k": 94.0,
                "atmosphere_type": AtmosphereType.DENSE,
                "surface_pressure_pa": 146700.0,
                "is_tidally_locked": 1,
                "rotation_period_days": 15.945,
                "albedo": 0.22,
                "semi_major_axis_km": 1221870.0,
                "eccentricity": 0.0288,
                "inclination_rad": 0.3485 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 29.8 * DEG_TO_RAD,
                "argument_periapsis_rad": 178.6 * DEG_TO_RAD,
                "mean_anomaly_rad": 74.2 * DEG_TO_RAD,
                "orbital_period_days": 15.945,
            },
            {
                "name": "Hyperion", "body_id": "HYPERION", "jpl_id": "607",
                "host_planet_name": "Saturn", "host_planet_id": "SATURN",
                "moon_class": MoonClass.ICY,
                "radius_m": 135000.0, "mass_kg": 5.6e18,
                "surface_temperature_k": 93.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 0,
                "rotation_period_days": 13.0,
                "albedo": 0.3,
                "semi_major_axis_km": 1481100.0,
                "eccentricity": 0.123,
                "inclination_rad": 0.568 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 140.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 200.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 110.0 * DEG_TO_RAD,
                "orbital_period_days": 21.276,
            },
            {
                "name": "Iapetus", "body_id": "IAPETUS", "jpl_id": "608",
                "host_planet_name": "Saturn", "host_planet_id": "SATURN",
                "moon_class": MoonClass.ICY,
                "radius_m": 734500.0, "mass_kg": 1.805e21,
                "surface_temperature_k": 110.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 79.321,
                "albedo": 0.2,
                "semi_major_axis_km": 3561300.0,
                "eccentricity": 0.0286,
                "inclination_rad": 15.47 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 75.6 * DEG_TO_RAD,
                "argument_periapsis_rad": 275.4 * DEG_TO_RAD,
                "mean_anomaly_rad": 195.0 * DEG_TO_RAD,
                "orbital_period_days": 79.321,
            },
            {
                "name": "Phoebe", "body_id": "PHOEBE", "jpl_id": "609",
                "host_planet_name": "Saturn", "host_planet_id": "SATURN",
                "moon_class": MoonClass.CAPTURED,
                "radius_m": 106500.0, "mass_kg": 8.29e18,
                "surface_temperature_k": 75.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 0,
                "rotation_period_days": 0.387,
                "albedo": 0.08,
                "semi_major_axis_km": 12955759.0,
                "eccentricity": 0.156,
                "inclination_rad": 175.3 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 230.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 110.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 50.0 * DEG_TO_RAD,
                "orbital_period_days": 550.56,
            },

            # =================================================================
            # URANUS (Host: Uranus / URANUS)
            # =================================================================
            {
                "name": "Puck", "body_id": "PUCK", "jpl_id": "715",
                "host_planet_name": "Uranus", "host_planet_id": "URANUS",
                "moon_class": MoonClass.ICY,
                "radius_m": 81000.0, "mass_kg": 2.9e18,
                "surface_temperature_k": 64.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 0.762,
                "albedo": 0.11,
                "semi_major_axis_km": 86004.0,
                "eccentricity": 0.00012,
                "inclination_rad": 0.319 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 50.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 80.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 20.0 * DEG_TO_RAD,
                "orbital_period_days": 0.762,
            },
            {
                "name": "Miranda", "body_id": "MIRANDA", "jpl_id": "705",
                "host_planet_name": "Uranus", "host_planet_id": "URANUS",
                "moon_class": MoonClass.ICY,
                "radius_m": 235800.0, "mass_kg": 6.59e19,
                "surface_temperature_k": 60.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 1.413,
                "albedo": 0.32,
                "semi_major_axis_km": 129390.0,
                "eccentricity": 0.0013,
                "inclination_rad": 4.338 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 326.4 * DEG_TO_RAD,
                "argument_periapsis_rad": 68.3 * DEG_TO_RAD,
                "mean_anomaly_rad": 150.0 * DEG_TO_RAD,
                "orbital_period_days": 1.413,
            },
            {
                "name": "Ariel", "body_id": "ARIEL", "jpl_id": "701",
                "host_planet_name": "Uranus", "host_planet_id": "URANUS",
                "moon_class": MoonClass.ICY,
                "radius_m": 578900.0, "mass_kg": 1.25e21,
                "surface_temperature_k": 60.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 2.520,
                "albedo": 0.39,
                "semi_major_axis_km": 191020.0,
                "eccentricity": 0.0012,
                "inclination_rad": 0.041 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 22.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 114.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 40.0 * DEG_TO_RAD,
                "orbital_period_days": 2.520,
            },
            {
                "name": "Umbriel", "body_id": "UMBRIEL", "jpl_id": "702",
                "host_planet_name": "Uranus", "host_planet_id": "URANUS",
                "moon_class": MoonClass.ICY,
                "radius_m": 584700.0, "mass_kg": 1.27e21,
                "surface_temperature_k": 75.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 4.144,
                "albedo": 0.21,
                "semi_major_axis_km": 266300.0,
                "eccentricity": 0.0039,
                "inclination_rad": 0.128 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 33.5 * DEG_TO_RAD,
                "argument_periapsis_rad": 94.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 210.0 * DEG_TO_RAD,
                "orbital_period_days": 4.144,
            },
            {
                "name": "Titania", "body_id": "TITANIA", "jpl_id": "703",
                "host_planet_name": "Uranus", "host_planet_id": "URANUS",
                "moon_class": MoonClass.ICY,
                "radius_m": 788400.0, "mass_kg": 3.40e21,
                "surface_temperature_k": 70.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 8.706,
                "albedo": 0.27,
                "semi_major_axis_km": 435910.0,
                "eccentricity": 0.0011,
                "inclination_rad": 0.079 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 99.8 * DEG_TO_RAD,
                "argument_periapsis_rad": 280.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 85.0 * DEG_TO_RAD,
                "orbital_period_days": 8.706,
            },
            {
                "name": "Oberon", "body_id": "OBERON", "jpl_id": "704",
                "host_planet_name": "Uranus", "host_planet_id": "URANUS",
                "moon_class": MoonClass.ICY,
                "radius_m": 761400.0, "mass_kg": 3.01e21,
                "surface_temperature_k": 75.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 13.463,
                "albedo": 0.23,
                "semi_major_axis_km": 583520.0,
                "eccentricity": 0.0014,
                "inclination_rad": 0.068 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 279.8 * DEG_TO_RAD,
                "argument_periapsis_rad": 15.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 310.0 * DEG_TO_RAD,
                "orbital_period_days": 13.463,
            },

            # =================================================================
            # NEPTUNE (Host: Neptune / NEPTUNE)
            # =================================================================
            {
                "name": "Proteus", "body_id": "PROTEUS", "jpl_id": "808",
                "host_planet_name": "Neptune", "host_planet_id": "NEPTUNE",
                "moon_class": MoonClass.ICY,
                "radius_m": 210000.0, "mass_kg": 4.4e19,
                "surface_temperature_k": 51.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": 1.122,
                "albedo": 0.096,
                "semi_major_axis_km": 117647.0,
                "eccentricity": 0.00053,
                "inclination_rad": 0.075 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 90.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 180.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 60.0 * DEG_TO_RAD,
                "orbital_period_days": 1.122,
            },
            {
                "name": "Triton", "body_id": "TRITON", "jpl_id": "801",
                "host_planet_name": "Neptune", "host_planet_id": "NEPTUNE",
                "moon_class": MoonClass.ICY,
                "radius_m": 1353400.0, "mass_kg": 2.14e22,
                "surface_temperature_k": 38.0,
                "atmosphere_type": AtmosphereType.THIN,
                "surface_pressure_pa": 1.4,
                "is_tidally_locked": 1,
                "rotation_period_days": -5.877,
                "albedo": 0.76,
                "semi_major_axis_km": 354760.0,
                "eccentricity": 0.000016,
                "inclination_rad": 156.885 * DEG_TO_RAD,  # Retrograde orbit
                "longitude_ascending_node_rad": 167.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 35.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 240.0 * DEG_TO_RAD,
                "orbital_period_days": -5.877,
            },
            {
                "name": "Nereid", "body_id": "NEREID", "jpl_id": "802",
                "host_planet_name": "Neptune", "host_planet_id": "NEPTUNE",
                "moon_class": MoonClass.CAPTURED,
                "radius_m": 170000.0, "mass_kg": 3.1e19,
                "surface_temperature_k": 50.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 0,
                "rotation_period_days": 0.48,
                "albedo": 0.155,
                "semi_major_axis_km": 5513400.0,
                "eccentricity": 0.7512,  # Highly eccentric captured orbit
                "inclination_rad": 7.23 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 320.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 290.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 12.0 * DEG_TO_RAD,
                "orbital_period_days": 360.14,
            },

            # =================================================================
            # PLUTO (Host: Pluto / PLUTO)
            # =================================================================
            {
                "name": "Charon", "body_id": "CHARON", "jpl_id": "901",
                "host_planet_name": "Pluto", "host_planet_id": "PLUTO",
                "moon_class": MoonClass.ICY,
                "radius_m": 606000.0, "mass_kg": 1.586e21,
                "surface_temperature_k": 53.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 1,
                "rotation_period_days": -6.387,
                "albedo": 0.38,
                "semi_major_axis_km": 19591.0,
                "eccentricity": 0.00005,
                "inclination_rad": 0.001 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 223.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 0.0,
                "mean_anomaly_rad": 180.0 * DEG_TO_RAD,
                "orbital_period_days": -6.387,
            },
            {
                "name": "Nix", "body_id": "NIX", "jpl_id": "902",
                "host_planet_name": "Pluto", "host_planet_id": "PLUTO",
                "moon_class": MoonClass.ICY,
                "radius_m": 24900.0, "mass_kg": 5.0e16,
                "surface_temperature_k": 40.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 0,
                "rotation_period_days": 1.829,
                "albedo": 0.56,
                "semi_major_axis_km": 48694.0,
                "eccentricity": 0.002,
                "inclination_rad": 0.133 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 10.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 50.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 90.0 * DEG_TO_RAD,
                "orbital_period_days": 24.85,
            },
            {
                "name": "Hydra", "body_id": "HYDRA", "jpl_id": "903",
                "host_planet_name": "Pluto", "host_planet_id": "PLUTO",
                "moon_class": MoonClass.ICY,
                "radius_m": 27500.0, "mass_kg": 5.0e16,
                "surface_temperature_k": 40.0,
                "atmosphere_type": AtmosphereType.NONE,
                "is_tidally_locked": 0,
                "rotation_period_days": 0.429,
                "albedo": 0.55,
                "semi_major_axis_km": 64738.0,
                "eccentricity": 0.0058,
                "inclination_rad": 0.242 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 100.0 * DEG_TO_RAD,
                "argument_periapsis_rad": 120.0 * DEG_TO_RAD,
                "mean_anomaly_rad": 210.0 * DEG_TO_RAD,
                "orbital_period_days": 38.20,
            },
        ]
