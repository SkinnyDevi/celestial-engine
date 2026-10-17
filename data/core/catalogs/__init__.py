"""
Precise Distance and 3D Celestial Mapping Package
Integrates Gaia DR3, Bailer-Jones, StarHorse, and Hipparcos catalogs with Astropy.
"""

from .models import (
    CatalogSource,
    DistanceMethod,
    DistanceResult,
    StarRecord,
    BaseCatalogProvider,
    parse_spectral_type_str,
    classify_spectral_type,
    temperature_to_spectral_type,
    temperature_from_color,
    sanitize_name_and_id,
)
from .coords import (
    distance_from_parallax,
    distance_from_pc,
    distance_from_kpc,
    create_skycoord_3d,
    skycoord_to_cartesian_meters,
    is_dusty_or_dense_region,
    resolve_center_coord,
)
from .gaia import GaiaDR3Provider
from .bailer_jones import BailerJonesProvider
from .starhorse import StarHorseProvider
from .hipparcos import HipparcosProvider
from .resolver import PreciseDistanceResolver

__all__ = [
    "CatalogSource",
    "DistanceMethod",
    "DistanceResult",
    "StarRecord",
    "BaseCatalogProvider",
    "parse_spectral_type_str",
    "classify_spectral_type",
    "temperature_to_spectral_type",
    "temperature_from_color",
    "sanitize_name_and_id",
    "distance_from_parallax",
    "distance_from_pc",
    "distance_from_kpc",
    "create_skycoord_3d",
    "skycoord_to_cartesian_meters",
    "is_dusty_or_dense_region",
    "resolve_center_coord",
    "GaiaDR3Provider",
    "BailerJonesProvider",
    "StarHorseProvider",
    "HipparcosProvider",
    "PreciseDistanceResolver",
]
