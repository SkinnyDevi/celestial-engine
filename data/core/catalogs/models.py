from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any

import astropy.units as astrounits
from astropy.coordinates import Distance, SkyCoord

from core.space import SpectralType, OpticalMagBands
from core.constants import DEG_TO_RAD, PC_TO_METERS

class CatalogSource(str, Enum):
    """Supported astronomical catalog sources."""
    GAIA_DR3 = "gaia_dr3"
    BAILER_JONES = "bailer_jones"
    STARHORSE = "starhorse"
    HIPPARCOS = "hipparcos"
    SIMBAD = "simbad"
    AUTO = "auto"

    @classmethod
    def from_string(cls, val: str) -> "CatalogSource":
        cleaned = val.lower().replace("-", "_").strip()
        for item in cls:
            if item.value == cleaned:
                return item
        if cleaned in ("gaia", "gaiadr3", "gaia_source"):
            return cls.GAIA_DR3
        if cleaned in ("bj", "bailerjones", "i352", "gedr3dis", "gedr3dist"):
            return cls.BAILER_JONES
        if cleaned in ("sh", "star_horse", "i354", "starhorse2021"):
            return cls.STARHORSE
        if cleaned in ("hip", "hip_main", "i239", "hipparcos_main"):
            return cls.HIPPARCOS
        raise ValueError(f"Unknown CatalogSource: '{val}'. Valid options: {[s.value for s in cls]}")

class DistanceMethod(str, Enum):
    """Method utilized for distance estimation and 3D positioning."""
    GEOMETRIC_PARALLAX = "geometric_parallax"
    BAYESIAN_GEOMETRIC = "bayesian_geometric"
    BAYESIAN_PHOTOGEOMETRIC = "bayesian_photogeometric"
    STELLAR_MODELS = "stellar_models"
    TRIGONOMETRIC_PARALLAX = "trigonometric_parallax"
    DEFAULT_FALLBACK = "default_fallback"

@dataclass
class DistanceResult:
    """Encapsulates precise distance calculations and uncertainties computed with Astropy."""
    distance_pc: float
    distance_error_lower_pc: float | None = None
    distance_error_upper_pc: float | None = None
    method: DistanceMethod = DistanceMethod.GEOMETRIC_PARALLAX
    source: CatalogSource = CatalogSource.GAIA_DR3
    parallax_mas: float | None = None
    parallax_error_mas: float | None = None
    astropy_distance: Distance | None = None
    is_valid: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def distance_m(self) -> float:
        if self.astropy_distance is not None:
            return float(self.astropy_distance.to_value(astrounits.m))
        return self.distance_pc * PC_TO_METERS

    @property
    def distance_ly(self) -> float:
        if self.astropy_distance is not None:
            return float(self.astropy_distance.to_value(astrounits.lyr))
        return self.distance_pc * 3.261563777

    @property
    def distance_kpc(self) -> float:
        if self.astropy_distance is not None:
            return float(self.astropy_distance.to_value(astrounits.kpc))
        return self.distance_pc / 1000.0

@dataclass
class StarRecord:
    """Decoupled record representing a star with 3D spatial mapping and astrophysical attributes."""
    name: str
    body_id: str
    ra_deg: float
    dec_deg: float
    distance: DistanceResult
    apparent_magnitude: float | None = None
    magnitude_band: OpticalMagBands | str | None = None
    spectral_type: SpectralType | None = None
    spectral_subtype: int | None = None
    mass_kg: float = 1.989e30
    radius_m: float = 696340000.0
    surface_temperature_k: float | None = None
    logg: float | None = None
    extinction_av: float | None = None
    cartesian_position_m: dict[str, float] | None = None
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    def to_engine_dict(self) -> dict[str, Any]:
        """Converts to dictionary structure compatible with celestial engine JSON schema."""
        ra_rad = self.ra_deg * DEG_TO_RAD
        dec_rad = self.dec_deg * DEG_TO_RAD

        pos = self.cartesian_position_m
        if pos is None:
            dist_m = self.distance.distance_m
            pos = {
                "x": dist_m * astrounits.Quantity(self.dec_deg, astrounits.deg).to(astrounits.rad).value,
                "y": 0.0,
                "z": 0.0
            }

        engine_dict: dict[str, Any] = {
            "name": self.name,
            "body_id": self.body_id,
            "position": pos,
            "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            "right_ascension_rad": ra_rad,
            "declination_rad": dec_rad,
            "distance_pc": round(self.distance.distance_pc, 4),
            "mass_kg": self.mass_kg,
            "radius_m": self.radius_m
        }

        if self.apparent_magnitude is not None:
            engine_dict["apparent_magnitude"] = round(float(self.apparent_magnitude), 4)

        stype = self.spectral_type
        ssub = self.spectral_subtype
        temp = self.surface_temperature_k

        if stype is None or temp is None:
            c_stype, c_sub, c_temp = classify_spectral_type(
                teff_k=temp,
                bp_rp=self.extra_metadata.get("bp_rp"),
                b_v=self.extra_metadata.get("b_v")
            )
            if stype is None:
                stype = c_stype
                ssub = c_sub
            if temp is None:
                temp = c_temp

        engine_dict["spectral_type"] = stype.value
        engine_dict["spectral_subtype"] = ssub if ssub is not None else 0

        if temp is not None:
            engine_dict["surface_temperature_k"] = round(float(temp), 2)

        return engine_dict

def temperature_to_spectral_type(teff_k: float) -> tuple[SpectralType, int]:
    """
    Maps effective surface temperature Teff in Kelvin to Morgan-Keenan SpectralType and subtype (0-9).
    Subtype 0 corresponds to the hottest stars in that class, 9 to coolest.
    """
    if teff_k >= 30000.0:
        # O type: 50,000K (O0) down to 30,000K (O9)
        frac = max(0.0, min(1.0, (50000.0 - teff_k) / 20000.0))
        return SpectralType.O, int(round(frac * 9))
    elif teff_k >= 10000.0:
        # B type: 30,000K (B0) down to 10,000K (B9)
        frac = max(0.0, min(1.0, (30000.0 - teff_k) / 20000.0))
        return SpectralType.B, int(round(frac * 9))
    elif teff_k >= 7500.0:
        # A type: 10,000K (A0) down to 7,500K (A9)
        frac = max(0.0, min(1.0, (10000.0 - teff_k) / 2500.0))
        return SpectralType.A, int(round(frac * 9))
    elif teff_k >= 6000.0:
        # F type: 7,500K (F0) down to 6,000K (F9)
        frac = max(0.0, min(1.0, (7500.0 - teff_k) / 1500.0))
        return SpectralType.F, int(round(frac * 9))
    elif teff_k >= 5200.0:
        # G type: 6,000K (G0) down to 5,200K (G9). Sun (5778K) -> G2
        frac = max(0.0, min(1.0, (6000.0 - teff_k) / 800.0))
        return SpectralType.G, int(round(frac * 9))
    elif teff_k >= 3700.0:
        # K type: 5,200K (K0) down to 3,700K (K9)
        frac = max(0.0, min(1.0, (5200.0 - teff_k) / 1500.0))
        return SpectralType.K, int(round(frac * 9))
    else:
        # M type: 3,700K (M0) down to 2,400K (M9). Proxima (3042K) -> M5
        frac = max(0.0, min(1.0, (3700.0 - teff_k) / 1300.0))
        return SpectralType.M, int(round(frac * 9))

def spectral_type_to_temperature(stype: SpectralType, subtype: int = 0) -> float:
    """
    Estimates nominal effective surface temperature Teff (K) from MK SpectralType and subtype (0-9).
    """
    sub = max(0, min(9, subtype))
    frac = sub / 9.0
    ranges = {
        SpectralType.O: (50000.0, 30000.0),
        SpectralType.B: (30000.0, 10000.0),
        SpectralType.A: (10000.0, 7500.0),
        SpectralType.F: (7500.0, 6000.0),
        SpectralType.G: (6000.0, 5200.0),
        SpectralType.K: (5200.0, 3700.0),
        SpectralType.M: (3700.0, 2400.0),
    }
    t_high, t_low = ranges.get(stype, (5778.0, 5778.0))
    return round(t_high - frac * (t_high - t_low), 1)

def temperature_from_color(bp_rp: float | None = None, b_v: float | None = None) -> float | None:
    """
    Computes effective temperature Teff in Kelvin using the Ballesteros (2012) relation
    from (B - V) or Gaia (BP - RP) color index.
    """
    bv = b_v
    if bv is None and bp_rp is not None:
        # Empirical conversion from Gaia DR3 BP-RP to Johnson B-V
        bv = 0.78 * bp_rp

    if bv is None:
        return None

    try:
        denom1 = 0.92 * bv + 1.7
        denom2 = 0.92 * bv + 0.62
        if abs(denom1) < 1e-4 or abs(denom2) < 1e-4:
            return None
        teff = 4600.0 * (1.0 / denom1 + 1.0 / denom2)
        if teff <= 0 or teff > 100000:
            return None
        return round(teff, 1)
    except Exception:
        return None

def classify_spectral_type(
    sp_str: str | bytes | Any | None = None,
    teff_k: float | None = None,
    bp_rp: float | None = None,
    b_v: float | None = None,
    fallback_type: SpectralType = SpectralType.G,
    fallback_subtype: int = 2,
    fallback_teff: float = 5778.0
) -> tuple[SpectralType, int, float]:
    """
    Unified classifier for stars returning (SpectralType, subtype [0-9], surface_temperature_k).
    Resolves in priority order:
    1. Explicit MK spectral string (e.g. 'G2V', 'M2Ib')
    2. Effective temperature Teff in Kelvin (e.g. Gaia GSP-Phot, StarHorse teff50)
    3. Photometric color (BP - RP) or (B - V) via Ballesteros (2012)
    4. Fallback default (Solar analog G2, 5778K)
    """
    # 1. Parse explicit spectral string
    stype, ssub = parse_spectral_type_str(sp_str)
    if stype is not None:
        sub = ssub if ssub is not None else 0
        temp = teff_k if (teff_k is not None and teff_k > 0) else spectral_type_to_temperature(stype, sub)
        return stype, sub, temp

    # 2. Derive from effective temperature if available
    if teff_k is not None and teff_k > 0:
        stype, sub = temperature_to_spectral_type(teff_k)
        return stype, sub, teff_k

    # 3. Derive from color index (BP-RP or B-V)
    derived_teff = temperature_from_color(bp_rp=bp_rp, b_v=b_v)
    if derived_teff is not None and derived_teff > 0:
        stype, sub = temperature_to_spectral_type(derived_teff)
        return stype, sub, derived_teff

    # 4. Fallback
    return fallback_type, fallback_subtype, fallback_teff

def parse_spectral_type_str(sp_str: str | bytes | Any | None) -> tuple[SpectralType, int] | tuple[None, None]:
    """Helper to parse a spectral type string (e.g. 'G2V', 'M2Ib') into SpectralType enum and subtype."""
    if sp_str is None or (isinstance(sp_str, float) and astrounits.isnan(sp_str)):
        return None, None
    if isinstance(sp_str, bytes):
        sp_str = sp_str.decode('utf-8', errors='ignore')
    sp_str = str(sp_str).strip()
    if not sp_str:
        return None, None

    match = re.search(r'([OBAFGKM])\s*([0-9]+(?:\.[0-9]+)?)?', sp_str, re.IGNORECASE)
    if not match:
        return None, None

    letter = match.group(1).upper()
    try:
        s_class = SpectralType[letter]
    except KeyError:
        return None, None

    s_sub = int(round(float(match.group(2)))) if match.group(2) else 0
    return s_class, s_sub

def sanitize_name_and_id(raw_name: str, fallback_prefix: str = "STAR") -> tuple[str, str]:
    """Standardizes star name and generates engine-compliant body ID."""
    clean_name = re.sub(r'[*]+', '', raw_name).strip()
    if not clean_name:
        clean_name = fallback_prefix
    body_id = re.sub(r'[^A-Za-z0-9_]', '_', clean_name).strip('_')[:31].upper()
    if not body_id:
        body_id = fallback_prefix
    return clean_name, body_id

class BaseCatalogProvider(ABC):
    """
    Abstract Base Class for loosely-coupled star catalog distance providers.
    Every catalog provider implements region queries and individual distance resolution.
    """

    @property
    @abstractmethod
    def source(self) -> CatalogSource:
        """Returns the CatalogSource identifier."""
        pass

    @property
    @abstractmethod
    def distance_method(self) -> DistanceMethod:
        """Returns the primary distance method used by this provider."""
        pass

    @abstractmethod
    def query_region(
        self,
        center: str | SkyCoord,
        radius_degrees: float,
        limit: int | None = None,
        max_apparent_magnitude: float | None = None,
        **kwargs: Any
    ) -> list[StarRecord]:
        """Queries for stars within a cone / sky region."""
        pass

    @abstractmethod
    def resolve_distance(
        self,
        coord: SkyCoord,
        search_radius_arcsec: float = 2.0,
        source_id: int | None = None,
        **kwargs: Any
    ) -> DistanceResult | None:
        """Resolves distance for a specific sky coordinate or source ID."""
        pass
