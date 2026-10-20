"""
Moons package for Celestial Body Engine.
Provides low-coupled domain models, coordinates, providers, and resolver facade
for natural satellites across the universe (Solar System major/minor moons and extrasolar moons).
"""

from core.space import MoonClass
from core.moons.models import (
    MoonRecord,
    sanitize_moon_id,
    classify_moon_type,
    estimate_moon_gravity,
)
from core.moons.coords import (
    keplerian_to_cartesian_moon,
    estimate_moon_period,
)
from core.moons.providers import (
    BaseMoonProvider,
    SolarSystemMoonProvider,
    ExomoonProvider,
    JPLHorizonsMoonProvider,
)
from core.moons.resolver import MoonResolver

__all__ = [
    "MoonClass",
    "MoonRecord",
    "sanitize_moon_id",
    "classify_moon_type",
    "estimate_moon_gravity",
    "keplerian_to_cartesian_moon",
    "estimate_moon_period",
    "BaseMoonProvider",
    "SolarSystemMoonProvider",
    "ExomoonProvider",
    "JPLHorizonsMoonProvider",
    "MoonResolver",
]
