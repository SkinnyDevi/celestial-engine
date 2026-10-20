from typing import Any
import re
import time

import astropy.units as astrounits
from astropy.coordinates import SkyCoord
from astropy.table import Table, Row
from astroquery.vizier import Vizier

from .models import (
    BaseCatalogProvider,
    CatalogSource,
    DistanceMethod,
    DistanceResult,
    StarRecord,
    parse_spectral_type_str,
    classify_spectral_type,
    sanitize_name_and_id,
)
from .coords import (
    distance_from_parallax,
    create_skycoord_3d,
    skycoord_to_cartesian_meters,
    resolve_center_coord,
)
from core.space import OpticalMagBands
from core.math import safe_float

class HipparcosProvider(BaseCatalogProvider):
    """
    Provider for the Hipparcos Main Catalogue (ESA 1997).
    - Catalog: I/239/hip_main via VizieR
    - Object Count: ~118,000
    - Distance Method: Trigonometric parallax via Astropy Distance
    - Best Use Case: Bright foreground stars (m < 6) where Gaia sensors saturate
    """

    CATALOG_ID = 'I/239/hip_main'

    def __init__(self) -> None:
        self._vizier = Vizier(
            catalog=self.CATALOG_ID,
            columns=['HIP', 'RAICRS', 'DEICRS', 'Plx', 'e_Plx', 'Vmag', 'B-V', 'SpType']
        )

    @property
    def source(self) -> CatalogSource:
        return CatalogSource.HIPPARCOS

    @property
    def distance_method(self) -> DistanceMethod:
        return DistanceMethod.TRIGONOMETRIC_PARALLAX

    def query_region(
        self,
        center: str | SkyCoord,
        radius_degrees: float,
        limit: int | None = 100,
        max_apparent_magnitude: float | None = 6.0,
        default_distance_pc: float | None = None,
        **kwargs: Any
    ) -> list[StarRecord]:
        """
        Queries Hipparcos stars in a cone around center coordinates.
        Ideal for bright foreground stars (m < 6.0) to prevent saturation errors.
        """
        coord = resolve_center_coord(center)

        prev_limit = self._vizier.ROW_LIMIT
        self._vizier.ROW_LIMIT = limit if (limit is not None and limit > 0) else -1
        limit_desc = f"limit: {limit}" if (limit is not None and limit > 0) else "unlimited"
        mag_desc = f", max_mag: {max_apparent_magnitude}" if max_apparent_magnitude is not None else ""
        print(f"[HipparcosProvider] Submitting cone query to VizieR {self.CATALOG_ID} (radius: {radius_degrees}°, {limit_desc}{mag_desc})...")
        t0 = time.time()
        try:
            results = self._vizier.query_region(coord, radius=radius_degrees * astrounits.deg)
        finally:
            self._vizier.ROW_LIMIT = prev_limit
        elapsed = time.time() - t0

        if not results or len(results) == 0:
            print(f"[HipparcosProvider] VizieR query returned 0 rows in {elapsed:.2f}s.")
            return []

        table: Table = results[0]
        total_rows = len(table)
        print(f"[HipparcosProvider] Received {total_rows} rows from VizieR in {elapsed:.2f}s. Computing 3D Cartesian coordinates...")

        records: list[StarRecord] = []
        for idx, row in enumerate(table, 1):
            v_mag = safe_float(row['Vmag'], default=None)
            if max_apparent_magnitude is not None and v_mag is not None and v_mag > max_apparent_magnitude:
                continue

            rec = self._row_to_star_record(row, default_distance_pc=default_distance_pc)
            if rec is not None:
                records.append(rec)
            if total_rows > 500 and (idx % 1000 == 0 or idx == total_rows):
                print(f"[HipparcosProvider] Progress: processed {idx}/{total_rows} stars ({(idx / total_rows) * 100:.1f}%)...")

        print(f"[HipparcosProvider] Complete: mapped {len(records)} stars to 3D Cartesian space.")
        return records

    def query_object(self, name_or_hip: str | int) -> list[StarRecord]:
        """Queries for a star in Hipparcos by HIP number or common name."""
        if isinstance(name_or_hip, int) or (isinstance(name_or_hip, str) and name_or_hip.isdigit()):
            hip_id = int(name_or_hip)
            res = self._vizier.query_constraints(HIP=hip_id)
            if res and len(res) > 0:
                rec = self._row_to_star_record(res[0][0])
                return [rec] if rec else []
            return []

        # Target name search
        coord = SkyCoord.from_name(str(name_or_hip))
        res = self._vizier.query_region(coord, radius=10.0 * astrounits.arcsec)
        if res and len(res) > 0:
            rec = self._row_to_star_record(res[0][0])
            if rec:
                rec.name = str(name_or_hip)
                _, body_id = sanitize_name_and_id(str(name_or_hip))
                rec.body_id = body_id
                return [rec]
        return []

    def resolve_distance(
        self,
        coord: SkyCoord,
        search_radius_arcsec: float = 3.0,
        source_id: int | None = None,
        **kwargs: Any
    ) -> DistanceResult | None:
        """
        Resolves trigonometric parallax distance for bright stars via Astropy Distance.
        """
        table: Table | None = None
        if source_id is not None:
            res = self._vizier.query_constraints(HIP=source_id)
            if res and len(res) > 0:
                table = res[0]
        else:
            res = self._vizier.query_region(coord, radius=(search_radius_arcsec / 3600.0) * astrounits.deg)
            if res and len(res) > 0:
                table = res[0]

        if table is None or len(table) == 0:
            return None

        row = table[0]
        plx = safe_float(row['Plx'], default=None)
        e_plx = safe_float(row['e_Plx'], default=None)

        return distance_from_parallax(
            parallax_mas=plx,
            parallax_error_mas=e_plx,
            source=self.source
        )

    def _row_to_star_record(
        self,
        row: Row | Any,
        default_distance_pc: float | None = None
    ) -> StarRecord | None:
        """Transforms a Hipparcos row into a StarRecord with 3D Cartesian coordinates."""
        hip_id = int(row['HIP'])
        ra_deg = float(row['RAICRS'])
        dec_deg = float(row['DEICRS'])

        plx = safe_float(row['Plx'], default=None)
        e_plx = safe_float(row['e_Plx'], default=None)

        dist_res = distance_from_parallax(
            parallax_mas=plx,
            parallax_error_mas=e_plx,
            source=self.source,
            fallback_pc=default_distance_pc
        )
        dist_res.method = DistanceMethod.TRIGONOMETRIC_PARALLAX

        # 3D Cartesian coordinates via Astropy SkyCoord
        sc_3d = create_skycoord_3d(ra_deg, dec_deg, dist_res.distance_pc)
        cart_pos = skycoord_to_cartesian_meters(sc_3d)

        v_mag = safe_float(row['Vmag'], default=None)
        b_v = safe_float(row['B-V'], default=None) if 'B-V' in row.colnames else None
        sp_type_str = row['SpType'] if ('SpType' in row.colnames and not row['SpType'] is None) else None
        stype, ssubtype, teff = classify_spectral_type(sp_str=sp_type_str, b_v=b_v)

        clean_name, body_id = sanitize_name_and_id(f"HIP {hip_id}", fallback_prefix=f"HIP_{hip_id}")

        return StarRecord(
            name=clean_name,
            body_id=body_id,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            distance=dist_res,
            apparent_magnitude=v_mag,
            magnitude_band=OpticalMagBands.V,
            spectral_type=stype,
            spectral_subtype=ssubtype,
            surface_temperature_k=teff,
            cartesian_position_m=cart_pos,
            extra_metadata={
                "hip_id": hip_id,
                "b_v": b_v
            }
        )
