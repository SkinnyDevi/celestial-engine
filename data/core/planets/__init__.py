"""
Planets Package for Celestial Body Engine
Provides low-coupled architecture for importing and classifying all types of celestial planets:
- Terrestrial (rocky planets, Super-Earths)
- Gas Giants (Jupiter/Saturn analogues, Hot Jupiters)
- Ice Giants (Uranus/Neptune analogues, Sub-Neptunes)
- Dwarf Planets (Pluto, Ceres)
- Rogue Planets (interstellar free-floating planets)
"""

from core.space import PlanetClass, AtmosphereType
from .models import (
    OrbitRecord,
    PlanetRecord,
    sanitize_planet_id,
    classify_planet_type,
    classify_atmosphere_type,
    estimate_mass_from_radius,
    estimate_radius_from_mass,
    estimate_surface_gravity,
    estimate_density,
    estimate_equilibrium_temperature,
    estimate_albedo,
)
from .coords import (
    solve_kepler,
    true_anomaly_from_eccentric,
    keplerian_to_cartesian,
    estimate_semimajor_axis_from_period,
    estimate_period_from_semimajor_axis,
    skycoord_to_cartesian_meters_planet,
)
from .providers import (
    BasePlanetProvider,
    NasaExoplanetProvider,
    SolarSystemPlanetProvider,
    RoguePlanetProvider,
)
from .resolver import PlanetResolver

__all__ = [
    "PlanetClass",
    "AtmosphereType",
    "OrbitRecord",
    "PlanetRecord",
    "sanitize_planet_id",
    "classify_planet_type",
    "classify_atmosphere_type",
    "estimate_mass_from_radius",
    "estimate_radius_from_mass",
    "estimate_surface_gravity",
    "estimate_density",
    "estimate_equilibrium_temperature",
    "estimate_albedo",
    "solve_kepler",
    "true_anomaly_from_eccentric",
    "keplerian_to_cartesian",
    "estimate_semimajor_axis_from_period",
    "estimate_period_from_semimajor_axis",
    "skycoord_to_cartesian_meters_planet",
    "BasePlanetProvider",
    "NasaExoplanetProvider",
    "SolarSystemPlanetProvider",
    "RoguePlanetProvider",
    "PlanetResolver",
]
