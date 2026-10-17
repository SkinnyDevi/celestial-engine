import math
from typing import Any

import astropy.units as u
from astropy.coordinates import Distance, SkyCoord

from .models import DistanceMethod, DistanceResult, CatalogSource
from core.constants import PC_TO_METERS, DEG_TO_RAD

def distance_from_parallax(
    parallax_mas: float | None,
    parallax_error_mas: float | None = None,
    source: CatalogSource = CatalogSource.GAIA_DR3,
    fallback_pc: float | None = None
) -> DistanceResult:
    """
    Constructs an Astropy Distance and DistanceResult from trigonometric/geometric parallax in mas.
    Handles negative or null parallax by marking validity and applying optional fallbacks.
    Computes rigorous 1-sigma upper and lower bounds.
    """
    if parallax_mas is None or math.isnan(parallax_mas) or parallax_mas <= 0:
        dist_pc = fallback_pc if fallback_pc is not None else 0.0
        astropy_dist = Distance(value=dist_pc, unit=u.pc) if dist_pc > 0 else None
        return DistanceResult(
            distance_pc=dist_pc,
            method=DistanceMethod.GEOMETRIC_PARALLAX,
            source=source,
            parallax_mas=parallax_mas,
            parallax_error_mas=parallax_error_mas,
            astropy_distance=astropy_dist,
            is_valid=False,
            metadata={"note": "Non-positive or missing parallax"}
        )

    # Standard parallax inversion using Astropy Distance
    astropy_dist = Distance(parallax=parallax_mas * u.mas)
    dist_pc = float(astropy_dist.pc)

    lower_pc: float | None = None
    upper_pc: float | None = None

    if parallax_error_mas is not None and not math.isnan(parallax_error_mas) and parallax_error_mas > 0:
        # Distance lower bound corresponds to parallax + error
        p_max = parallax_mas + parallax_error_mas
        lower_pc = float(Distance(parallax=p_max * u.mas).pc)

        # Distance upper bound corresponds to parallax - error (if still positive)
        p_min = parallax_mas - parallax_error_mas
        if p_min > 0:
            upper_pc = float(Distance(parallax=p_min * u.mas).pc)
        else:
            # Significant line-of-sight stretching/unbounded parallax error
            upper_pc = None

    return DistanceResult(
        distance_pc=dist_pc,
        distance_error_lower_pc=lower_pc,
        distance_error_upper_pc=upper_pc,
        method=DistanceMethod.GEOMETRIC_PARALLAX,
        source=source,
        parallax_mas=parallax_mas,
        parallax_error_mas=parallax_error_mas,
        astropy_distance=astropy_dist,
        is_valid=True
    )

def distance_from_pc(
    dist_pc: float,
    lower_pc: float | None = None,
    upper_pc: float | None = None,
    method: DistanceMethod = DistanceMethod.BAYESIAN_PHOTOGEOMETRIC,
    source: CatalogSource = CatalogSource.BAILER_JONES,
    metadata: dict[str, Any] | None = None
) -> DistanceResult:
    """Constructs an Astropy Distance and DistanceResult from a direct distance in parsecs."""
    if dist_pc is None or math.isnan(dist_pc) or dist_pc <= 0:
        return DistanceResult(
            distance_pc=0.0,
            method=method,
            source=source,
            is_valid=False,
            metadata=metadata or {}
        )

    astropy_dist = Distance(value=dist_pc, unit=u.pc)
    return DistanceResult(
        distance_pc=dist_pc,
        distance_error_lower_pc=lower_pc,
        distance_error_upper_pc=upper_pc,
        method=method,
        source=source,
        astropy_distance=astropy_dist,
        is_valid=True,
        metadata=metadata or {}
    )

def distance_from_kpc(
    dist_kpc: float,
    lower_kpc: float | None = None,
    upper_kpc: float | None = None,
    method: DistanceMethod = DistanceMethod.STELLAR_MODELS,
    source: CatalogSource = CatalogSource.STARHORSE,
    metadata: dict[str, Any] | None = None
) -> DistanceResult:
    """Constructs an Astropy Distance and DistanceResult from distance in kiloparsecs (e.g. StarHorse)."""
    if dist_kpc is None or math.isnan(dist_kpc) or dist_kpc <= 0:
        return DistanceResult(
            distance_pc=0.0,
            method=method,
            source=source,
            is_valid=False,
            metadata=metadata or {}
        )

    astropy_dist = Distance(value=dist_kpc, unit=u.kpc)
    dist_pc = float(astropy_dist.to_value(u.pc))
    lower_pc = float(Distance(value=lower_kpc, unit=u.kpc).to_value(u.pc)) if lower_kpc is not None else None
    upper_pc = float(Distance(value=upper_kpc, unit=u.kpc).to_value(u.pc)) if upper_kpc is not None else None

    return DistanceResult(
        distance_pc=dist_pc,
        distance_error_lower_pc=lower_pc,
        distance_error_upper_pc=upper_pc,
        method=method,
        source=source,
        astropy_distance=astropy_dist,
        is_valid=True,
        metadata=metadata or {}
    )

def create_skycoord_3d(
    ra_deg: float,
    dec_deg: float,
    distance_or_pc: Distance | float
) -> SkyCoord:
    """
    Constructs an Astropy SkyCoord in ICRS frame with exact 3D distance representation.
    """
    if isinstance(distance_or_pc, Distance):
        dist = distance_or_pc
    else:
        dist = Distance(value=max(0.0, distance_or_pc), unit=u.pc)

    return SkyCoord(
        ra=ra_deg * u.deg,
        dec=dec_deg * u.deg,
        distance=dist,
        frame='icrs'
    )

def skycoord_to_cartesian_meters(coord: SkyCoord) -> dict[str, float]:
    """
    Extracts 3D Cartesian coordinates in meters from an Astropy SkyCoord representation.
    Uses double precision coordinates with the Sun at the origin (Heliocentric ICRS).
    """
    cart = coord.cartesian
    return {
        "x": float(cart.x.to_value(u.m)),
        "y": float(cart.y.to_value(u.m)),
        "z": float(cart.z.to_value(u.m))
    }

def is_dusty_or_dense_region(coord: SkyCoord, latitude_threshold_deg: float = 10.0) -> bool:
    """
    Checks if coordinates lie within the Galactic plane dust lane (|b| <= threshold).
    Useful for routing queries to StarHorse which accounts for extinction and dust models.
    """
    b_deg = float(coord.galactic.b.deg)
    return abs(b_deg) <= latitude_threshold_deg

def resolve_center_coord(center: str | SkyCoord) -> SkyCoord:
    """Resolves a target name (e.g. 'M31', 'Betelgeuse') or returns the existing SkyCoord."""
    if isinstance(center, SkyCoord):
        return center
    name = str(center).strip()
    if name.lower() in ("sun", "sol"):
        raise ValueError(
            "The Sun is our local star and the origin of the heliocentric coordinate system (distance = 0). "
            "It does not exist as an extra-solar directional target in astronomical sky catalogs. "
            "To query stars around the Sun, use a 3D physical distance search (e.g. add_nearby_stars)."
        )
    return SkyCoord.from_name(name)
