"""
Orbital mechanics and spatial coordinate transformations for moons and natural satellites.
"""

import math
from astropy.time import Time

from core.constants import G_CONST
from core.planets.coords import (
    solve_kepler,
    true_anomaly_from_eccentric,
    keplerian_to_cartesian,
    propagate_mean_anomaly,
)


def estimate_moon_period(semimajor_axis_km: float, host_mass_kg: float) -> float:
    """
    Computes orbital period in Earth days using Kepler's Third Law for a satellite:
    P = 2 * pi * sqrt(a^3 / (G * M_host))
    """
    if host_mass_kg <= 0 or semimajor_axis_km <= 0:
        return 1.0

    a_m = semimajor_axis_km * 1000.0
    mu = G_CONST * host_mass_kg
    period_seconds = 2.0 * math.pi * math.sqrt((a_m ** 3) / mu)
    return period_seconds / 86400.0


def keplerian_to_cartesian_moon(
    semimajor_axis_km: float,
    eccentricity: float,
    inclination_rad: float,
    longitude_ascending_node_rad: float,
    argument_periapsis_rad: float,
    mean_anomaly_rad: float,
) -> tuple[dict[str, float], float, float]:
    """
    Calculates 3D Cartesian position vector (in meters) relative to the host planet center
    from Keplerian orbital elements at a given mean anomaly.
    Returns (position_dict_meters, eccentric_anomaly, true_anomaly).
    """
    semimajor_axis_m = semimajor_axis_km * 1000.0
    return keplerian_to_cartesian(
        semimajor_axis_m=semimajor_axis_m,
        eccentricity=eccentricity,
        inclination_rad=inclination_rad,
        longitude_ascending_node_rad=longitude_ascending_node_rad,
        argument_periapsis_rad=argument_periapsis_rad,
        mean_anomaly_rad=mean_anomaly_rad,
    )
