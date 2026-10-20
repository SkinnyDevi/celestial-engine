"""
Domain models, physical estimations, and classifications for moons and natural satellites.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
import re
from typing import Any

from core.constants import G_CONST
from core.space import MoonClass, AtmosphereType
from core.planets.models import OrbitRecord


def sanitize_moon_id(raw_name: str, fallback_prefix: str = "MOON") -> tuple[str, str]:
    """Generates a clean human-readable name and an engine-compliant body ID (max 31 chars)."""
    clean_name = re.sub(r'[*]+', '', raw_name).strip()
    if not clean_name:
        clean_name = fallback_prefix
    body_id = re.sub(r'[^A-Za-z0-9_]', '_', clean_name).strip('_')[:31].upper()
    if not body_id:
        body_id = fallback_prefix
    return clean_name, body_id


def estimate_moon_gravity(mass_kg: float, radius_m: float) -> float:
    """Computes Newtonian surface gravity in m/s^2."""
    if radius_m <= 0:
        return 0.0
    return (G_CONST * mass_kg) / (radius_m ** 2)


def classify_moon_type(
    raw_type_str: str | None = None,
    is_captured: bool = False,
    is_volcanic: bool = False,
    is_icy: bool = False,
    is_rocky: bool = False,
    density_kg_m3: float | None = None,
) -> MoonClass:
    """
    Scientifically classifies any natural satellite into MoonClass:
    - VOLCANIC: Active volcanism / tidal heating (e.g. Io)
    - CAPTURED: Captured asteroids / irregular satellites (e.g. Phobos, Deimos, Phoebe, Himalia)
    - ICY: Subsurface oceans / ice crust (e.g. Europa, Ganymede, Enceladus, Triton, Charon)
    - ROCKY: Silicate / rocky composition (e.g. Earth's Moon)
    """
    if is_volcanic:
        return MoonClass.VOLCANIC
    if is_captured:
        return MoonClass.CAPTURED
    if is_icy:
        return MoonClass.ICY
    if is_rocky:
        return MoonClass.ROCKY

    if raw_type_str:
        s = raw_type_str.lower()
        if "volcan" in s or "active" in s:
            return MoonClass.VOLCANIC
        if "captur" in s or "irregular" in s or "asteroid" in s:
            return MoonClass.CAPTURED
        if "ice" in s or "icy" in s or "ocean" in s or "water" in s:
            return MoonClass.ICY
        if "rock" in s or "silicate" in s or "terrestrial" in s:
            return MoonClass.ROCKY

    if density_kg_m3 is not None:
        if density_kg_m3 > 3000.0:
            return MoonClass.ROCKY
        elif density_kg_m3 < 2000.0:
            return MoonClass.ICY

    return MoonClass.ROCKY


@dataclass
class MoonRecord:
    """Decoupled record representing a natural satellite / moon."""
    name: str
    body_id: str
    host_planet_name: str
    host_planet_id: str | None = None
    host_planet_index: int = -1
    orbit_index: int = -1

    moon_class: MoonClass = MoonClass.ROCKY
    atmosphere_type: AtmosphereType = AtmosphereType.NONE

    # 3D position vector in meters RELATIVE to host planet center
    position: dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    rotation: dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0})

    semi_major_axis_km: float = 0.0
    eccentricity: float = 0.0
    inclination_rad: float = 0.0
    longitude_ascending_node_rad: float = 0.0
    argument_periapsis_rad: float = 0.0
    mean_anomaly_rad: float = 0.0
    orbital_period_days: float = 1.0

    mass_kg: float = 1.0e20
    radius_m: float = 1.0e5
    surface_gravity_m_s2: float = 0.0

    is_tidally_locked: int = 1
    axial_tilt_rad: float = 0.0
    rotation_period_days: float = 1.0
    albedo: float = 0.3
    surface_temperature_k: float = 100.0
    surface_pressure_pa: float = 0.0

    orbit: OrbitRecord | None = None
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.surface_gravity_m_s2 <= 0.0 and self.radius_m > 0 and self.mass_kg > 0:
            self.surface_gravity_m_s2 = estimate_moon_gravity(self.mass_kg, self.radius_m)

    def to_engine_dict(self) -> dict[str, Any]:
        """Converts to JSON dictionary matching schema.json for moon."""
        return {
            "name": self.name,
            "body_id": self.body_id,
            "host_planet_index": int(self.host_planet_index),
            "orbit_index": int(self.orbit_index),
            "moon_class": self.moon_class.value if isinstance(self.moon_class, Enum) else int(self.moon_class),
            "position": {
                "x": round(float(self.position.get("x", 0.0)), 4),
                "y": round(float(self.position.get("y", 0.0)), 4),
                "z": round(float(self.position.get("z", 0.0)), 4),
            },
            "rotation": {
                "x": round(float(self.rotation.get("x", 0.0)), 6),
                "y": round(float(self.rotation.get("y", 0.0)), 6),
                "z": round(float(self.rotation.get("z", 0.0)), 6),
                "w": round(float(self.rotation.get("w", 1.0)), 6),
            },
            "semi_major_axis_km": round(float(self.semi_major_axis_km), 4),
            "eccentricity": round(float(self.eccentricity), 6),
            "inclination_rad": round(float(self.inclination_rad), 6),
            "longitude_ascending_node_rad": round(float(self.longitude_ascending_node_rad), 6),
            "argument_periapsis_rad": round(float(self.argument_periapsis_rad), 6),
            "mean_anomaly_rad": round(float(self.mean_anomaly_rad), 6),
            "orbital_period_days": round(float(self.orbital_period_days), 6),
            "mass_kg": float(self.mass_kg),
            "radius_m": round(float(self.radius_m), 2),
            "surface_gravity_m_s2": round(float(self.surface_gravity_m_s2), 4),
            "is_tidally_locked": int(self.is_tidally_locked),
            "axial_tilt_rad": round(float(self.axial_tilt_rad), 6),
            "rotation_period_days": round(float(self.rotation_period_days), 6),
            "albedo": round(float(self.albedo), 4),
            "surface_temperature_k": round(float(self.surface_temperature_k), 2),
            "atmosphere_type": self.atmosphere_type.value if isinstance(self.atmosphere_type, Enum) else int(self.atmosphere_type),
            "surface_pressure_pa": round(float(self.surface_pressure_pa), 2),
        }
