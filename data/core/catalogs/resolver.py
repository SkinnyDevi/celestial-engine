from typing import Any

import astropy.units as u
from astropy.coordinates import SkyCoord

from .models import (
    BaseCatalogProvider,
    CatalogSource,
    DistanceMethod,
    DistanceResult,
    StarRecord,
)
from .coords import (
    create_skycoord_3d,
    skycoord_to_cartesian_meters,
    is_dusty_or_dense_region,
    resolve_center_coord,
)
from .gaia import GaiaDR3Provider
from .bailer_jones import BailerJonesProvider
from .starhorse import StarHorseProvider
from .hipparcos import HipparcosProvider

class PreciseDistanceResolver:
    """
    Loosely coupled orchestrator and routing factory for precision astronomical distance estimation.
    Selects the optimal distance catalog based on astrophysical regime:
    - Hipparcos (I/239): Bright foreground stars (m < 6) where Gaia saturates
    - StarHorse (I/354): Dusty / dense fields (|b| <= 10 deg) using multi-band IR + stellar models
    - Bailer-Jones (I/352): Bayesian geometric/photogeometric distances preventing line-of-sight distortion
    - Gaia DR3: All-sky true 3D stellar positions
    """

    def __init__(
        self,
        gaia_provider: GaiaDR3Provider | None = None,
        bailer_jones_provider: BailerJonesProvider | None = None,
        starhorse_provider: StarHorseProvider | None = None,
        hipparcos_provider: HipparcosProvider | None = None,
        prefer_photogeometric: bool = True
    ) -> None:
        self.gaia: GaiaDR3Provider = gaia_provider or GaiaDR3Provider()
        self.bailer_jones: BailerJonesProvider = bailer_jones_provider or BailerJonesProvider(prefer_photogeometric=prefer_photogeometric)
        self.starhorse: StarHorseProvider = starhorse_provider or StarHorseProvider()
        self.hipparcos: HipparcosProvider = hipparcos_provider or HipparcosProvider()

        self._providers: dict[CatalogSource, BaseCatalogProvider] = {
            CatalogSource.GAIA_DR3: self.gaia,
            CatalogSource.BAILER_JONES: self.bailer_jones,
            CatalogSource.STARHORSE: self.starhorse,
            CatalogSource.HIPPARCOS: self.hipparcos,
        }

    def register_provider(self, source: CatalogSource, provider: BaseCatalogProvider) -> None:
        """Allows registering custom or mocked catalog providers."""
        self._providers[source] = provider

    def get_provider(self, source: CatalogSource | str) -> BaseCatalogProvider:
        """Retrieves catalog provider instance by source enum or name string."""
        if isinstance(source, str):
            source = CatalogSource.from_string(source)
        if source not in self._providers:
            raise ValueError(f"No provider registered for source '{source.value}'")
        return self._providers[source]

    def select_best_source(
        self,
        coord: SkyCoord,
        apparent_mag: float | None = None
    ) -> CatalogSource:
        """
        Determines the optimal catalog source according to the reference criteria:
        1. Bright foreground stars (m < 6.0) -> Hipparcos (avoids Gaia saturation)
        2. Dust / dense fields (|b| <= 10 deg) -> StarHorse (multi-band IR + dust models)
        3. All other stars -> Bailer-Jones (Bayesian distances preventing line-of-sight stretching)
        """
        if apparent_mag is not None and apparent_mag < 6.0:
            return CatalogSource.HIPPARCOS

        if is_dusty_or_dense_region(coord, latitude_threshold_deg=10.0):
            return CatalogSource.STARHORSE

        return CatalogSource.BAILER_JONES

    def resolve_precise_distance(
        self,
        coord: SkyCoord,
        apparent_mag: float | None = None,
        source_id: int | None = None,
        preferred_source: CatalogSource | str = CatalogSource.AUTO,
        search_radius_arcsec: float = 2.5
    ) -> DistanceResult | None:
        """
        Resolves the best distance for a given celestial point with automatic fallback.
        """
        src = CatalogSource.from_string(preferred_source) if isinstance(preferred_source, str) else preferred_source

        if src == CatalogSource.AUTO:
            src = self.select_best_source(coord, apparent_mag=apparent_mag)

        # Attempt query on primary source
        provider = self._providers.get(src)
        if provider is not None:
            try:
                res = provider.resolve_distance(coord, search_radius_arcsec=search_radius_arcsec, source_id=source_id)
                if res is not None and res.is_valid:
                    return res
            except Exception as e:
                print(f"[PreciseDistanceResolver] Primary query on {src.value} failed: {e}. Trying fallback...")

        # Fallback sequence: Bailer-Jones -> Gaia DR3 -> Hipparcos -> StarHorse
        fallback_order = [
            CatalogSource.BAILER_JONES,
            CatalogSource.GAIA_DR3,
            CatalogSource.HIPPARCOS,
            CatalogSource.STARHORSE
        ]
        for fallback_src in fallback_order:
            if fallback_src == src:
                continue
            fb_provider = self._providers.get(fallback_src)
            if fb_provider is not None:
                try:
                    res = fb_provider.resolve_distance(coord, search_radius_arcsec=search_radius_arcsec, source_id=source_id)
                    if res is not None and res.is_valid:
                        return res
                except Exception:
                    continue

        return None

    def query_region(
        self,
        center: str | SkyCoord,
        radius_degrees: float,
        source: CatalogSource | str = CatalogSource.AUTO,
        limit: int | None = 100,
        max_apparent_magnitude: float | None = None,
        default_distance_pc: float | None = None,
        **kwargs: Any
    ) -> list[StarRecord]:
        """
        Queries stars in a region using the specified or auto-selected catalog provider.
        """
        center_coord = resolve_center_coord(center)
        ra_deg = float(center_coord.ra.deg)
        dec_deg = float(center_coord.dec.deg)
        gal_l = float(center_coord.galactic.l.deg)
        gal_b = float(center_coord.galactic.b.deg)
        print(f"[PreciseDistanceResolver] Resolved target '{center}': RA = {ra_deg:.4f}°, Dec = {dec_deg:.4f}° (Galactic: l = {gal_l:.2f}°, b = {gal_b:.2f}°)")

        src = CatalogSource.from_string(source) if isinstance(source, str) else source
        if src == CatalogSource.AUTO:
            src = self.select_best_source(center_coord, apparent_mag=max_apparent_magnitude)
            reason = "bright star (m < 6.0)" if (max_apparent_magnitude is not None and max_apparent_magnitude < 6.0) else (
                "dense/dusty galactic plane (|b| <= 10°)" if abs(gal_b) <= 10.0 else "standard field (preventing line-of-sight stretching)"
            )
            print(f"[PreciseDistanceResolver] Auto-selected source: {src.value} (reason: {reason})")

        provider = self.get_provider(src)
        limit_desc = f"limit: {limit}" if (limit is not None and limit > 0) else "unlimited"
        mag_desc = f", max_mag: {max_apparent_magnitude}" if max_apparent_magnitude is not None else ""
        print(f"[PreciseDistanceResolver] Dispatching query to {provider.source.value} (method: {provider.distance_method.value}, radius: {radius_degrees}°, {limit_desc}{mag_desc})...")
        
        return provider.query_region(
            center=center_coord,
            radius_degrees=radius_degrees,
            limit=limit,
            max_apparent_magnitude=max_apparent_magnitude,
            default_distance_pc=default_distance_pc,
            **kwargs
        )

    def enrich_star_dict(
        self,
        star_dict: dict[str, Any],
        preferred_source: CatalogSource | str = CatalogSource.AUTO
    ) -> bool:
        """
        Enriches an existing star dictionary (e.g. from SIMBAD) with precise distance and 3D position.
        Updates 'distance_pc', 'position', and metadata in-place.
        Returns True if enriched with precise catalog distance, False otherwise.
        """
        ra_rad = star_dict.get("right_ascension_rad")
        dec_rad = star_dict.get("declination_rad")
        if ra_rad is None or dec_rad is None:
            return False

        coord = SkyCoord(ra=ra_rad * u.rad, dec=dec_rad * u.rad, frame='icrs')
        mag = star_dict.get("apparent_magnitude")

        dist_res = self.resolve_precise_distance(
            coord=coord,
            apparent_mag=mag,
            preferred_source=preferred_source
        )

        if dist_res is None or not dist_res.is_valid:
            return False

        # Recalculate 3D Cartesian coordinates with Astropy
        sc_3d = create_skycoord_3d(float(coord.ra.deg), float(coord.dec.deg), dist_res.distance_pc)
        cart = skycoord_to_cartesian_meters(sc_3d)

        star_dict["position"] = cart
        star_dict["distance_pc"] = round(dist_res.distance_pc, 4)
        star_dict["distance_method"] = dist_res.method.value
        star_dict["distance_source"] = dist_res.source.value

        if dist_res.distance_error_lower_pc is not None:
            star_dict["distance_error_lower_pc"] = round(dist_res.distance_error_lower_pc, 4)
        if dist_res.distance_error_upper_pc is not None:
            star_dict["distance_error_upper_pc"] = round(dist_res.distance_error_upper_pc, 4)

        return True
