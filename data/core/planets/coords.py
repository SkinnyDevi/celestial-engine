"""
Orbital mechanics and spatial coordinate transformations for planets and orbits.
"""

import math
from astropy.coordinates import SkyCoord
from astropy.time import Time
import astropy.units as astrounits

from core.constants import (
    AU_TO_METERS,
    DEG_TO_RAD,
    G_CONST,
    PC_TO_METERS,
    SOLAR_MASS_KG,
)

def solve_kepler(mean_anomaly_rad: float, eccentricity: float, max_iter: int = 15, tol: float = 1e-7) -> float:
    """
    Solves Kepler's Equation M = E - e * sin(E) using Newton-Raphson iteration.
    Matches the orbital calculation logic in src/core/space/orbit.c.
    """
    m = mean_anomaly_rad % (2.0 * math.pi)
    if m < 0:
        m += 2.0 * math.pi

    e = max(0.0, min(0.999999, eccentricity))
    eccentric_anomaly = m + e * math.sin(m) if e > 0.8 else m

    for _ in range(max_iter):
        f = eccentric_anomaly - e * math.sin(eccentric_anomaly) - m
        f_prime = 1.0 - e * math.cos(eccentric_anomaly)
        if abs(f_prime) < 1e-12:
            break
        delta = f / f_prime
        eccentric_anomaly -= delta
        if abs(delta) < tol:
            break

    return eccentric_anomaly

def true_anomaly_from_eccentric(eccentric_anomaly_rad: float, eccentricity: float) -> float:
    """Calculates true anomaly nu from eccentric anomaly E and eccentricity e."""
    e = max(0.0, min(0.999999, eccentricity))
    half_e = eccentric_anomaly_rad / 2.0
    nu = 2.0 * math.atan2(
        math.sqrt(1.0 + e) * math.sin(half_e),
        math.sqrt(1.0 - e) * math.cos(half_e)
    )
    return nu % (2.0 * math.pi)

def keplerian_to_cartesian(
    semimajor_axis_m: float,
    eccentricity: float,
    inclination_rad: float,
    longitude_ascending_node_rad: float,
    argument_periapsis_rad: float,
    mean_anomaly_rad: float
) -> tuple[dict[str, float], float, float]:
    """
    Calculates 3D Cartesian position vector (in meters) relative to the central body
    from Keplerian orbital elements at a given mean anomaly.
    Returns (position_dict, eccentric_anomaly, true_anomaly).
    """
    e = max(0.0, min(0.999999, eccentricity))
    eccentric_anomaly = solve_kepler(mean_anomaly_rad, e)
    nu = true_anomaly_from_eccentric(eccentric_anomaly, e)

    # Radial distance from focal point
    r = semimajor_axis_m * (1.0 - e * math.cos(eccentric_anomaly))

    # Coordinates in orbital plane (perifocal system)
    x_prime = r * math.cos(nu)
    y_prime = r * math.sin(nu)

    # Orbital Euler angles
    omega_node = longitude_ascending_node_rad
    arg_peri = argument_periapsis_rad
    inc = inclination_rad

    cos_omega = math.cos(omega_node)
    sin_omega = math.sin(omega_node)
    cos_w = math.cos(arg_peri)
    sin_w = math.sin(arg_peri)
    cos_i = math.cos(inc)
    sin_i = math.sin(inc)

    # Rotate from orbital plane to reference frame
    px = cos_omega * cos_w - sin_omega * sin_w * cos_i
    py = sin_omega * cos_w + cos_omega * sin_w * cos_i
    pz = sin_w * sin_i

    qx = -cos_omega * sin_w - sin_omega * cos_w * cos_i
    qy = -sin_omega * sin_w + cos_omega * cos_w * cos_i
    qz = cos_w * sin_i

    x = x_prime * px + y_prime * qx
    y = x_prime * py + y_prime * qy
    z = x_prime * pz + y_prime * qz

    return {"x": float(x), "y": float(y), "z": float(z)}, eccentric_anomaly, nu

def propagate_mean_anomaly(
    mean_anomaly_at_epoch_rad: float,
    orbital_period_days: float,
    epoch_time: Time,
    current_time: Time
) -> float:
    """Propagates mean anomaly from epoch_time to current_time based on orbital period."""
    if orbital_period_days <= 0:
        return mean_anomaly_at_epoch_rad

    dt_days = (current_time.jd - epoch_time.jd)
    mean_motion = (2.0 * math.pi) / orbital_period_days
    m = (mean_anomaly_at_epoch_rad + mean_motion * dt_days) % (2.0 * math.pi)
    if m < 0:
        m += 2.0 * math.pi
    return m

def estimate_semimajor_axis_from_period(
    period_days: float,
    host_star_mass_kg: float = SOLAR_MASS_KG,
    planet_mass_kg: float = 0.0
) -> float:
    """Estimates semi-major axis in meters using Kepler's Third Law."""
    if period_days <= 0:
        return AU_TO_METERS

    period_sec = period_days * 86400.0
    total_mass = host_star_mass_kg + planet_mass_kg
    mu = G_CONST * total_mass
    a_m = ((period_sec ** 2 * mu) / (4.0 * math.pi ** 2)) ** (1.0 / 3.0)
    return a_m

def estimate_period_from_semimajor_axis(
    semimajor_axis_m: float,
    host_star_mass_kg: float = SOLAR_MASS_KG,
    planet_mass_kg: float = 0.0
) -> float:
    """Estimates orbital period in days using Kepler's Third Law."""
    if semimajor_axis_m <= 0:
        return 365.25

    total_mass = host_star_mass_kg + planet_mass_kg
    mu = G_CONST * total_mass
    period_sec = 2.0 * math.pi * math.sqrt((semimajor_axis_m ** 3) / mu)
    return period_sec / 86400.0

def skycoord_to_cartesian_meters_planet(coord: SkyCoord) -> dict[str, float]:
    """
    Transforms a 3D SkyCoord into Cartesian coordinates (meters).
    Handles rogue planets and stars uniformly.
    """
    dist_m = float(coord.distance.to_value(astrounits.m))
    ra_rad = float(coord.ra.to_value(astrounits.rad))
    dec_rad = float(coord.dec.to_value(astrounits.rad))

    x = dist_m * math.cos(dec_rad) * math.cos(ra_rad)
    y = dist_m * math.cos(dec_rad) * math.sin(ra_rad)
    z = dist_m * math.sin(dec_rad)

    return {"x": x, "y": y, "z": z}
