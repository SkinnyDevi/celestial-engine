"""
Solar System Planet Provider
Provides high-precision physical and orbital specifications for all Solar System planets
(Terrestrial, Gas Giants, Ice Giants, and Dwarf Planets).
"""

from typing import Any
import math
from astropy.coordinates import SkyCoord
from astropy.time import Time

from core.constants import (
    AU_TO_METERS,
    DEG_TO_RAD,
    EARTH_MASS_KG,
    EARTH_RADIUS_M,
    G_CONST,
)
from core.space import PlanetClass, AtmosphereType
from core.planets.coords import keplerian_to_cartesian
from core.planets.models import OrbitRecord, PlanetRecord
from core.planets.providers.base import BasePlanetProvider

class SolarSystemPlanetProvider(BasePlanetProvider):
    """
    Decoupled Solar System provider containing precision IAU/NASA parameters
    for terrestrial planets, gas giants, ice giants, and dwarf planets.
    """

    @property
    def name(self) -> str:
        return "solar_system"

    def query_by_host_star(self, host_name: str, host_id: str | None = None, **kwargs: Any) -> list[PlanetRecord]:
        """Returns Solar System planets if querying for the Sun."""
        name_clean = host_name.strip().upper()
        if name_clean in ("SUN", "SOL", "THE SUN"):
            include_dwarf = kwargs.get("include_dwarf_planets", True)
            return self.get_all_planets(include_dwarf=include_dwarf, sim_time=kwargs.get("sim_time"))
        return []

    def query_by_region(self, center_coord: SkyCoord, radius_deg: float, **kwargs: Any) -> list[PlanetRecord]:
        """Returns Solar System planets if center is near the Sun or explicitly requested."""
        if kwargs.get("include_solar_system", False):
            return self.get_all_planets(
                include_dwarf=kwargs.get("include_dwarf_planets", True),
                sim_time=kwargs.get("sim_time")
            )
        return []

    def get_known_planet(self, planet_name: str, **kwargs: Any) -> PlanetRecord | None:
        """Retrieves a specific Solar System planet by name."""
        all_planets = self.get_all_planets(include_dwarf=True, sim_time=kwargs.get("sim_time"))
        target = planet_name.strip().upper()
        for p in all_planets:
            if p.name.upper() == target or p.body_id.upper() == target:
                return p
        return None

    def get_all_planets(self, include_dwarf: bool = True, sim_time: Time | None = None) -> list[PlanetRecord]:
        """Returns records for all major and dwarf planets in the Solar System."""
        specs = self._get_solar_system_specs()
        records: list[PlanetRecord] = []

        for spec in specs:
            if not include_dwarf and spec["planet_class"] == PlanetClass.DWARF:
                continue

            a_au = spec["semi_major_axis_au"]
            a_m = a_au * AU_TO_METERS
            e = spec["eccentricity"]
            inc_rad = spec["inclination_rad"]
            node_rad = spec["longitude_ascending_node_rad"]
            peri_rad = spec["argument_periapsis_rad"]
            m_rad = spec["mean_anomaly_rad"]
            period_days = spec["orbital_period_days"]

            # Calculate 3D Cartesian position relative to Sun at epoch
            pos, _, nu = keplerian_to_cartesian(
                semimajor_axis_m=a_m,
                eccentricity=e,
                inclination_rad=inc_rad,
                longitude_ascending_node_rad=node_rad,
                argument_periapsis_rad=peri_rad,
                mean_anomaly_rad=m_rad
            )

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
                center_position={"x": 0.0, "y": 0.0, "z": 0.0}
            )

            mass = spec["mass_kg"]
            radius = spec["radius_m"]
            gravity = spec.get("surface_gravity_m_s2", (G_CONST * mass) / (radius ** 2))
            vol = (4.0 / 3.0) * math.pi * (radius ** 3)
            density = spec.get("density_kg_m3", mass / vol)

            p = PlanetRecord(
                name=spec["name"],
                body_id=spec["body_id"],
                host_star_name="Sun",
                host_star_id="SUN",
                planet_class=spec["planet_class"],
                atmosphere_type=spec["atmosphere_type"],
                position=pos,
                semi_major_axis_au=a_au,
                eccentricity=e,
                inclination_rad=inc_rad,
                longitude_ascending_node_rad=node_rad,
                argument_periapsis_rad=peri_rad,
                mean_anomaly_rad=m_rad,
                orbital_period_days=period_days,
                mass_kg=mass,
                radius_m=radius,
                density_kg_m3=density,
                surface_gravity_m_s2=gravity,
                albedo=spec["albedo"],
                surface_temperature_k=spec["surface_temperature_k"],
                axial_tilt_rad=spec["axial_tilt_rad"],
                rotation_period_days=spec["rotation_period_days"],
                magnetic_field_gauss=spec.get("magnetic_field_gauss", 0.0),
                surface_pressure_pa=spec.get("surface_pressure_pa", 0.0),
                has_rings=spec.get("has_rings", 0),
                ring_inner_radius_m=spec.get("ring_inner_radius_m", 0.0),
                ring_outer_radius_m=spec.get("ring_outer_radius_m", 0.0),
                orbit=orbit,
                extra_metadata={"jpl_id": spec.get("jpl_id")}
            )
            records.append(p)

        return records

    @staticmethod
    def _get_solar_system_specs() -> list[dict[str, Any]]:
        return [
            # 1. Mercury (Terrestrial)
            {
                "name": "Mercury", "body_id": "MERCURY", "jpl_id": "199",
                "planet_class": PlanetClass.TERRESTRIAL,
                "radius_m": 2439700.0, "mass_kg": 3.3011e23,
                "surface_temperature_k": 440.0,
                "atmosphere_type": AtmosphereType.THIN,
                "surface_pressure_pa": 1e-9,
                "albedo": 0.106,
                "axial_tilt_rad": 0.034 * DEG_TO_RAD,
                "rotation_period_days": 58.646,
                "magnetic_field_gauss": 0.003,
                "has_rings": 0,
                "semi_major_axis_au": 0.387098,
                "eccentricity": 0.205630,
                "inclination_rad": 7.005 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 48.331 * DEG_TO_RAD,
                "argument_periapsis_rad": 29.124 * DEG_TO_RAD,
                "mean_anomaly_rad": 174.796 * DEG_TO_RAD,
                "orbital_period_days": 87.969
            },
            # 2. Venus (Terrestrial)
            {
                "name": "Venus", "body_id": "VENUS", "jpl_id": "299",
                "planet_class": PlanetClass.TERRESTRIAL,
                "radius_m": 6051800.0, "mass_kg": 4.8675e24,
                "surface_temperature_k": 737.0,
                "atmosphere_type": AtmosphereType.DENSE,
                "surface_pressure_pa": 9.3e6,
                "albedo": 0.77,
                "axial_tilt_rad": 177.36 * DEG_TO_RAD,
                "rotation_period_days": -243.02,
                "magnetic_field_gauss": 0.0,
                "has_rings": 0,
                "semi_major_axis_au": 0.723332,
                "eccentricity": 0.006772,
                "inclination_rad": 3.39458 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 76.680 * DEG_TO_RAD,
                "argument_periapsis_rad": 54.884 * DEG_TO_RAD,
                "mean_anomaly_rad": 50.115 * DEG_TO_RAD,
                "orbital_period_days": 224.701
            },
            # 3. Earth (Terrestrial)
            {
                "name": "Earth", "body_id": "EARTH", "jpl_id": "399",
                "planet_class": PlanetClass.TERRESTRIAL,
                "radius_m": EARTH_RADIUS_M, "mass_kg": EARTH_MASS_KG,
                "surface_temperature_k": 288.0,
                "atmosphere_type": AtmosphereType.STANDARD,
                "surface_pressure_pa": 101325.0,
                "albedo": 0.306,
                "axial_tilt_rad": 23.44 * DEG_TO_RAD,
                "rotation_period_days": 0.99726968,
                "magnetic_field_gauss": 0.5,
                "has_rings": 0,
                "semi_major_axis_au": 1.00000011,
                "eccentricity": 0.01671022,
                "inclination_rad": 0.00005 * DEG_TO_RAD,
                "longitude_ascending_node_rad": -11.26064 * DEG_TO_RAD,
                "argument_periapsis_rad": 102.94719 * DEG_TO_RAD,
                "mean_anomaly_rad": 358.617 * DEG_TO_RAD,
                "orbital_period_days": 365.256363
            },
            # 4. Mars (Terrestrial)
            {
                "name": "Mars", "body_id": "MARS", "jpl_id": "499",
                "planet_class": PlanetClass.TERRESTRIAL,
                "radius_m": 3389500.0, "mass_kg": 6.4171e23,
                "surface_temperature_k": 210.0,
                "atmosphere_type": AtmosphereType.THIN,
                "surface_pressure_pa": 610.0,
                "albedo": 0.17,
                "axial_tilt_rad": 25.19 * DEG_TO_RAD,
                "rotation_period_days": 1.025957,
                "magnetic_field_gauss": 0.0,
                "has_rings": 0,
                "semi_major_axis_au": 1.523679,
                "eccentricity": 0.0934,
                "inclination_rad": 1.850 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 49.57854 * DEG_TO_RAD,
                "argument_periapsis_rad": 286.502 * DEG_TO_RAD,
                "mean_anomaly_rad": 19.373 * DEG_TO_RAD,
                "orbital_period_days": 686.980
            },
            # 5. Jupiter (Gas Giant)
            {
                "name": "Jupiter", "body_id": "JUPITER", "jpl_id": "599",
                "planet_class": PlanetClass.GAS_GIANT,
                "radius_m": 69911000.0, "mass_kg": 1.8982e27,
                "surface_temperature_k": 165.0,
                "atmosphere_type": AtmosphereType.THICK_ENVELOPE,
                "surface_pressure_pa": 2.0e7,
                "albedo": 0.538,
                "axial_tilt_rad": 3.13 * DEG_TO_RAD,
                "rotation_period_days": 0.41354,
                "magnetic_field_gauss": 4.28,
                "has_rings": 1,
                "ring_inner_radius_m": 92000000.0, "ring_outer_radius_m": 226000000.0,
                "semi_major_axis_au": 5.204267,
                "eccentricity": 0.048498,
                "inclination_rad": 1.303 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 100.464 * DEG_TO_RAD,
                "argument_periapsis_rad": 273.867 * DEG_TO_RAD,
                "mean_anomaly_rad": 20.020 * DEG_TO_RAD,
                "orbital_period_days": 4332.589
            },
            # 6. Saturn (Gas Giant)
            {
                "name": "Saturn", "body_id": "SATURN", "jpl_id": "699",
                "planet_class": PlanetClass.GAS_GIANT,
                "radius_m": 58232000.0, "mass_kg": 5.6834e26,
                "surface_temperature_k": 134.0,
                "atmosphere_type": AtmosphereType.THICK_ENVELOPE,
                "surface_pressure_pa": 1.4e7,
                "albedo": 0.499,
                "axial_tilt_rad": 26.73 * DEG_TO_RAD,
                "rotation_period_days": 0.444,
                "magnetic_field_gauss": 0.22,
                "has_rings": 1,
                "ring_inner_radius_m": 74500000.0, "ring_outer_radius_m": 140220000.0,
                "semi_major_axis_au": 9.537070,
                "eccentricity": 0.054151,
                "inclination_rad": 2.485 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 113.665 * DEG_TO_RAD,
                "argument_periapsis_rad": 339.392 * DEG_TO_RAD,
                "mean_anomaly_rad": 317.020 * DEG_TO_RAD,
                "orbital_period_days": 10759.22
            },
            # 7. Uranus (Ice Giant)
            {
                "name": "Uranus", "body_id": "URANUS", "jpl_id": "799",
                "planet_class": PlanetClass.ICE_GIANT,
                "radius_m": 25362000.0, "mass_kg": 8.681e25,
                "surface_temperature_k": 76.0,
                "atmosphere_type": AtmosphereType.THICK_ENVELOPE,
                "surface_pressure_pa": 5.0e6,
                "albedo": 0.517,
                "axial_tilt_rad": 97.77 * DEG_TO_RAD,
                "rotation_period_days": -0.71833,
                "magnetic_field_gauss": 0.23,
                "has_rings": 1,
                "ring_inner_radius_m": 38000000.0, "ring_outer_radius_m": 51149000.0,
                "semi_major_axis_au": 19.19126,
                "eccentricity": 0.047168,
                "inclination_rad": 0.773 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 74.006 * DEG_TO_RAD,
                "argument_periapsis_rad": 96.999 * DEG_TO_RAD,
                "mean_anomaly_rad": 142.238 * DEG_TO_RAD,
                "orbital_period_days": 30685.4
            },
            # 8. Neptune (Ice Giant)
            {
                "name": "Neptune", "body_id": "NEPTUNE", "jpl_id": "899",
                "planet_class": PlanetClass.ICE_GIANT,
                "radius_m": 24622000.0, "mass_kg": 1.024e26,
                "surface_temperature_k": 72.0,
                "atmosphere_type": AtmosphereType.THICK_ENVELOPE,
                "surface_pressure_pa": 5.0e6,
                "albedo": 0.442,
                "axial_tilt_rad": 28.32 * DEG_TO_RAD,
                "rotation_period_days": 0.6713,
                "magnetic_field_gauss": 0.14,
                "has_rings": 1,
                "ring_inner_radius_m": 41900000.0, "ring_outer_radius_m": 62933000.0,
                "semi_major_axis_au": 30.06896,
                "eccentricity": 0.008586,
                "inclination_rad": 1.769 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 131.784 * DEG_TO_RAD,
                "argument_periapsis_rad": 273.187 * DEG_TO_RAD,
                "mean_anomaly_rad": 256.228 * DEG_TO_RAD,
                "orbital_period_days": 60189.0
            },
            # 9. Pluto (Dwarf Planet)
            {
                "name": "Pluto", "body_id": "PLUTO", "jpl_id": "999",
                "planet_class": PlanetClass.DWARF,
                "radius_m": 1188300.0, "mass_kg": 1.303e22,
                "surface_temperature_k": 44.0,
                "atmosphere_type": AtmosphereType.THIN,
                "surface_pressure_pa": 1.0,
                "albedo": 0.52,
                "axial_tilt_rad": 122.53 * DEG_TO_RAD,
                "rotation_period_days": -6.387,
                "magnetic_field_gauss": 0.0,
                "has_rings": 0,
                "semi_major_axis_au": 39.482,
                "eccentricity": 0.2488,
                "inclination_rad": 17.16 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 110.299 * DEG_TO_RAD,
                "argument_periapsis_rad": 113.834 * DEG_TO_RAD,
                "mean_anomaly_rad": 14.86 * DEG_TO_RAD,
                "orbital_period_days": 90560.0
            },
            # 10. Ceres (Dwarf Planet in Asteroid Belt)
            {
                "name": "Ceres", "body_id": "CERES", "jpl_id": "2000001",
                "planet_class": PlanetClass.DWARF,
                "radius_m": 469730.0, "mass_kg": 9.3835e20,
                "surface_temperature_k": 168.0,
                "atmosphere_type": AtmosphereType.THIN,
                "surface_pressure_pa": 1e-10,
                "albedo": 0.09,
                "axial_tilt_rad": 4.0 * DEG_TO_RAD,
                "rotation_period_days": 0.3781,
                "magnetic_field_gauss": 0.0,
                "has_rings": 0,
                "semi_major_axis_au": 2.7675,
                "eccentricity": 0.0758,
                "inclination_rad": 10.593 * DEG_TO_RAD,
                "longitude_ascending_node_rad": 80.327 * DEG_TO_RAD,
                "argument_periapsis_rad": 73.597 * DEG_TO_RAD,
                "mean_anomaly_rad": 95.989 * DEG_TO_RAD,
                "orbital_period_days": 1681.63
            }
        ]
