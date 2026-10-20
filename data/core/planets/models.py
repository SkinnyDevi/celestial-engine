"""
Domain models, physical estimations, and classifications for planets and planetary systems.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
import re
from typing import Any

from core.constants import (
    AU_TO_METERS,
    DEG_TO_RAD,
    EARTH_MASS_KG,
    EARTH_RADIUS_M,
    G_CONST,
    JUPITER_MASS_KG,
    JUPITER_RADIUS_M,
    SOLAR_MASS_KG,
    SOLAR_RADIUS_M,
)
from core.space import PlanetClass, AtmosphereType
from core.planets.coords import (
    estimate_period_from_semimajor_axis,
    estimate_semimajor_axis_from_period,
    keplerian_to_cartesian,
)

def sanitize_planet_id(raw_name: str, fallback_prefix: str = "PLANET") -> tuple[str, str]:
    """Generates a clean human-readable name and an engine-compliant body ID (max 31 chars)."""
    clean_name = re.sub(r'[*]+', '', raw_name).strip()
    if not clean_name:
        clean_name = fallback_prefix
    body_id = re.sub(r'[^A-Za-z0-9_]', '_', clean_name).strip('_')[:31].upper()
    if not body_id:
        body_id = fallback_prefix
    return clean_name, body_id

@dataclass
class OrbitRecord:
    """Decoupled record representing a Keplerian planetary orbit."""
    semimajor_axis: float  # In meters
    eccentricity: float = 0.0
    inclination: float = 0.0  # In radians
    longitude_of_ascending_node: float = 0.0  # In radians
    argument_of_periapsis: float = 0.0  # In radians
    mean_anomaly_at_epoch: float = 0.0  # In radians
    orbital_period_days: float = 365.25
    mean_anomaly: float = 0.0
    true_anomaly: float = 0.0
    center_position: dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})

    def to_engine_dict(self) -> dict[str, Any]:
        """Converts to JSON dictionary matching schema.json for orbit."""
        return {
            "semimajor_axis": round(float(self.semimajor_axis), 4),
            "eccentricity": round(float(self.eccentricity), 6),
            "inclination": round(float(self.inclination), 6),
            "longitude_of_ascending_node": round(float(self.longitude_of_ascending_node), 6),
            "argument_of_periapsis": round(float(self.argument_of_periapsis), 6),
            "mean_anomaly_at_epoch": round(float(self.mean_anomaly_at_epoch), 6),
            "orbital_period_days": round(float(self.orbital_period_days), 6),
            "mean_anomaly": round(float(self.mean_anomaly), 6),
            "true_anomaly": round(float(self.true_anomaly), 6),
            "center_position": {
                "x": round(float(self.center_position.get("x", 0.0)), 4),
                "y": round(float(self.center_position.get("y", 0.0)), 4),
                "z": round(float(self.center_position.get("z", 0.0)), 4),
            }
        }

@dataclass
class PlanetRecord:
    """Decoupled record representing a celestial planet (terrestrial, gas giant, ice giant, dwarf, rogue)."""
    name: str
    body_id: str
    host_star_name: str | None = None
    host_star_id: str | None = None
    host_star_index: int = -1
    orbit_index: int = -1

    planet_class: PlanetClass = PlanetClass.TERRESTRIAL
    atmosphere_type: AtmosphereType = AtmosphereType.NONE

    position: dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    rotation: dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0})

    right_ascension_rad: float = 0.0
    declination_rad: float = 0.0
    distance_pc: float = 0.0

    semi_major_axis_au: float = 1.0
    eccentricity: float = 0.0
    inclination_rad: float = 0.0
    longitude_ascending_node_rad: float = 0.0
    argument_periapsis_rad: float = 0.0
    mean_anomaly_rad: float = 0.0
    orbital_period_days: float = 365.25

    mass_kg: float = EARTH_MASS_KG
    radius_m: float = EARTH_RADIUS_M
    density_kg_m3: float = 5515.0
    surface_gravity_m_s2: float = 9.81

    albedo: float = 0.3
    surface_temperature_k: float = 288.0
    axial_tilt_rad: float = 0.0
    rotation_period_days: float = 1.0
    magnetic_field_gauss: float = 0.5

    surface_pressure_pa: float = 101325.0
    has_rings: int = 0
    ring_inner_radius_m: float = 0.0
    ring_outer_radius_m: float = 0.0

    orbit: OrbitRecord | None = None
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    def to_engine_dict(self) -> dict[str, Any]:
        """Converts to JSON dictionary matching schema.json for planet."""
        d: dict[str, Any] = {
            "name": self.name,
            "body_id": self.body_id,
            "host_star_index": int(self.host_star_index),
            "orbit_index": int(self.orbit_index),
            "planet_class": self.planet_class.value if isinstance(self.planet_class, Enum) else int(self.planet_class),
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
            "right_ascension_rad": round(float(self.right_ascension_rad), 6),
            "declination_rad": round(float(self.declination_rad), 6),
            "distance_pc": round(float(self.distance_pc), 4),
            "semi_major_axis_au": round(float(self.semi_major_axis_au), 8),
            "eccentricity": round(float(self.eccentricity), 6),
            "inclination_rad": round(float(self.inclination_rad), 6),
            "longitude_ascending_node_rad": round(float(self.longitude_ascending_node_rad), 6),
            "argument_periapsis_rad": round(float(self.argument_periapsis_rad), 6),
            "mean_anomaly_rad": round(float(self.mean_anomaly_rad), 6),
            "orbital_period_days": round(float(self.orbital_period_days), 6),
            "mass_kg": float(self.mass_kg),
            "radius_m": round(float(self.radius_m), 2),
            "density_kg_m3": round(float(self.density_kg_m3), 2),
            "surface_gravity_m_s2": round(float(self.surface_gravity_m_s2), 4),
            "albedo": round(float(self.albedo), 4),
            "surface_temperature_k": round(float(self.surface_temperature_k), 2),
            "axial_tilt_rad": round(float(self.axial_tilt_rad), 6),
            "rotation_period_days": round(float(self.rotation_period_days), 6),
            "magnetic_field_gauss": round(float(self.magnetic_field_gauss), 4),
            "atmosphere_type": self.atmosphere_type.value if isinstance(self.atmosphere_type, Enum) else int(self.atmosphere_type),
            "surface_pressure_pa": round(float(self.surface_pressure_pa), 2),
            "has_rings": int(self.has_rings),
            "ring_inner_radius_m": round(float(self.ring_inner_radius_m), 2),
            "ring_outer_radius_m": round(float(self.ring_outer_radius_m), 2),
        }
        return d

# -----------------------------------------------------------------------------
# Classification Logic
# -----------------------------------------------------------------------------

def classify_planet_type(
    mass_kg: float | None = None,
    radius_m: float | None = None,
    density_kg_m3: float | None = None,
    has_host: bool = True,
    is_dwarf: bool = False,
    raw_type_str: str | None = None
) -> PlanetClass:
    """
    Scientifically classifies any planet into PlanetClass:
    - ROGUE: Free-floating planet without a host star
    - DWARF: Sub-planetary dwarf objects (e.g. Pluto, Ceres)
    - GAS_GIANT: Jupiter/Saturn analogues, Hot Jupiters (R >= 6 R_earth, M >= 50 M_earth, or low density)
    - ICE_GIANT: Uranus/Neptune analogues, Mini-Neptunes (1.75 <= R/R_earth < 6, 10 <= M/M_earth < 50)
    - TERRESTRIAL: Rocky, Earth/Mars/Venus/Mercury analogues, Super-Earths
    """
    if not has_host:
        return PlanetClass.ROGUE

    if raw_type_str:
        s = raw_type_str.lower()
        if "rogue" in s or "free-floating" in s or "isolated" in s:
            return PlanetClass.ROGUE
        if "dwarf" in s:
            return PlanetClass.DWARF
        if "gas" in s or "jupiter" in s or "jovian" in s or "saturn" in s:
            return PlanetClass.GAS_GIANT
        if "ice" in s or "neptun" in s or "sub-neptune" in s or "mini-neptune" in s:
            return PlanetClass.ICE_GIANT
        if "terrestrial" in s or "rocky" in s or "earth" in s or "super-earth" in s:
            return PlanetClass.TERRESTRIAL

    if is_dwarf:
        return PlanetClass.DWARF

    # Check radius in Earth units
    r_earth = (radius_m / EARTH_RADIUS_M) if radius_m and radius_m > 0 else None
    # Check mass in Earth units
    m_earth = (mass_kg / EARTH_MASS_KG) if mass_kg and mass_kg > 0 else None

    # Dwarf planet check: very small radius and mass
    if (r_earth is not None and r_earth < 0.35) or (m_earth is not None and m_earth < 0.02):
        return PlanetClass.DWARF

    # Gas giant check: large radius or large mass
    if (r_earth is not None and r_earth >= 6.0) or (m_earth is not None and m_earth >= 50.0):
        return PlanetClass.GAS_GIANT

    if density_kg_m3 is not None and density_kg_m3 < 1800.0 and m_earth is not None and m_earth >= 20.0:
        return PlanetClass.GAS_GIANT

    # Ice giant check: intermediate size/mass
    if (r_earth is not None and 1.75 <= r_earth < 6.0) or (m_earth is not None and 10.0 <= m_earth < 50.0):
        return PlanetClass.ICE_GIANT

    # Default to Terrestrial (Rocky / Super-Earth)
    return PlanetClass.TERRESTRIAL

def classify_atmosphere_type(
    planet_class: PlanetClass,
    surface_temperature_k: float | None = None,
    surface_gravity_m_s2: float | None = None,
    mass_kg: float | None = None
) -> AtmosphereType:
    """Estimates the atmosphere type based on planet class, temperature, and surface gravity."""
    if planet_class in (PlanetClass.GAS_GIANT, PlanetClass.ICE_GIANT):
        return AtmosphereType.THICK_ENVELOPE

    if planet_class == PlanetClass.DWARF:
        return AtmosphereType.THIN if (surface_temperature_k and surface_temperature_k < 60) else AtmosphereType.NONE

    if planet_class == PlanetClass.ROGUE:
        if mass_kg and mass_kg > 20.0 * EARTH_MASS_KG:
            return AtmosphereType.THICK_ENVELOPE
        return AtmosphereType.THIN

    # Terrestrial planet
    temp = surface_temperature_k if surface_temperature_k is not None else 288.0
    grav = surface_gravity_m_s2 if surface_gravity_m_s2 is not None else 9.81

    if grav < 2.0 or temp < 100.0 or temp > 1500.0:
        # Extremely low gravity or extreme heat strips atmosphere
        return AtmosphereType.NONE if grav < 1.0 else AtmosphereType.THIN
    elif temp > 450.0:
        # Hot rocky planet (Venus-like greenhouse or heavy atmosphere)
        return AtmosphereType.DENSE
    elif 200.0 <= temp <= 350.0 and grav >= 6.0:
        # Habitable zone / Earth-like
        return AtmosphereType.STANDARD
    else:
        return AtmosphereType.THIN

# -----------------------------------------------------------------------------
# Physical Estimations
# -----------------------------------------------------------------------------

def estimate_mass_from_radius(radius_m: float) -> float:
    """
    Estimates planet mass from radius using empirical exoplanet Mass-Radius relations (Chen & Kipping 2017).
    """
    r_earth = max(0.1, radius_m / EARTH_RADIUS_M)
    if r_earth < 1.23:
        # Terran / rocky regime: M ~ R^3.7
        m_earth = r_earth ** 3.7
    elif r_earth < 3.0:
        # Sub-Neptunian / volatile regime: M ~ 2.7 * R^1.3
        m_earth = 2.7 * (r_earth ** 1.3)
    elif r_earth < 6.0:
        # Neptunian regime: M ~ 1.5 * R^2.1
        m_earth = 1.5 * (r_earth ** 2.1)
    else:
        # Jovian regime: saturation of radius due to electron degeneracy
        m_jup = max(0.1, min(15.0, (r_earth / (JUPITER_RADIUS_M / EARTH_RADIUS_M)) ** 2.5))
        return m_jup * JUPITER_MASS_KG

    return m_earth * EARTH_MASS_KG

def estimate_radius_from_mass(mass_kg: float) -> float:
    """Estimates planet radius from mass using inverse empirical Mass-Radius relations."""
    m_earth = max(0.001, mass_kg / EARTH_MASS_KG)
    if m_earth < 2.0:
        r_earth = m_earth ** (1.0 / 3.7)
    elif m_earth < 10.0:
        r_earth = (m_earth / 2.7) ** (1.0 / 1.3)
    elif m_earth < 50.0:
        r_earth = (m_earth / 1.5) ** (1.0 / 2.1)
    else:
        # Jovian plateau: radius ~ 1.0 - 1.4 R_jup
        m_jup = mass_kg / JUPITER_MASS_KG
        r_jup = 1.0 + 0.1 * math.log10(max(0.1, m_jup))
        return r_jup * JUPITER_RADIUS_M

    return r_earth * EARTH_RADIUS_M

def estimate_surface_gravity(mass_kg: float, radius_m: float) -> float:
    """Calculates surface gravitational acceleration g = G * M / R^2."""
    if radius_m <= 0:
        return 9.81
    return (G_CONST * mass_kg) / (radius_m ** 2)

def estimate_density(mass_kg: float, radius_m: float) -> float:
    """Calculates bulk density rho = M / (4/3 * pi * R^3) in kg/m^3."""
    if radius_m <= 0:
        return 5515.0
    vol = (4.0 / 3.0) * math.pi * (radius_m ** 3)
    return mass_kg / vol

def estimate_equilibrium_temperature(
    semi_major_axis_au: float,
    host_teff_k: float = 5778.0,
    host_radius_m: float = SOLAR_RADIUS_M,
    albedo: float = 0.3
) -> float:
    """Calculates planetary equilibrium temperature Teq = T_star * sqrt(R_star / (2 * a)) * (1 - A)^0.25."""
    if semi_major_axis_au <= 0:
        return 288.0
    a_m = semi_major_axis_au * AU_TO_METERS
    teq = host_teff_k * math.sqrt(host_radius_m / (2.0 * a_m)) * ((1.0 - albedo) ** 0.25)
    return max(10.0, teq)

def estimate_albedo(planet_class: PlanetClass) -> float:
    """Provides representative Bond albedo for each planet class."""
    if planet_class == PlanetClass.GAS_GIANT:
        return 0.52
    elif planet_class == PlanetClass.ICE_GIANT:
        return 0.48
    elif planet_class == PlanetClass.DWARF:
        return 0.50
    elif planet_class == PlanetClass.ROGUE:
        return 0.10
    else:  # Terrestrial
        return 0.30
