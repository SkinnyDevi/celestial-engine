import math
import time
from typing import Any

import astropy.units as astrounits
from astropy.coordinates import SkyCoord
from astropy.table import Table, Row
from astroquery.gaia import Gaia
from astroquery.vizier import Vizier

from .models import (
    BaseCatalogProvider,
    CatalogSource,
    DistanceMethod,
    DistanceResult,
    StarRecord,
    classify_spectral_type,
    sanitize_name_and_id,
)
from .coords import (
    distance_from_parallax,
    create_skycoord_3d,
    skycoord_to_cartesian_meters,
    resolve_center_coord,
)
from core.math import safe_float

class GaiaDR3Provider(BaseCatalogProvider):
    """
    Provider for Gaia Data Release 3 (DR3).
    - Object Count: ~1.46 Billion
    - Distance Method: Geometric parallax (varpi) via Astropy Distance
    - Best Use Case: All-sky true 3D stellar positions
    """

    def __init__(self, use_tap: bool = True, timeout_sec: int = 45) -> None:
        self._use_tap = use_tap
        self._timeout_sec = timeout_sec
        # Configure ESA Gaia archive
        Gaia.ROW_LIMIT = -1

    @property
    def source(self) -> CatalogSource:
        return CatalogSource.GAIA_DR3

    @property
    def distance_method(self) -> DistanceMethod:
        return DistanceMethod.GEOMETRIC_PARALLAX

    def query_region(
        self,
        center: str | SkyCoord,
        radius_degrees: float,
        limit: int | None = 100,
        max_apparent_magnitude: float | None = None,
        default_distance_pc: float | None = None,
        **kwargs: Any
    ) -> list[StarRecord]:
        """
        Queries Gaia DR3 in a cone around center coordinates.
        Calculates geometric parallax distances with Astropy and maps to 3D Cartesian coordinates.
        """
        coord = resolve_center_coord(center)
        ra_deg = float(coord.ra.deg)
        dec_deg = float(coord.dec.deg)

        limit_desc = f"limit: {limit}" if (limit is not None and limit > 0) else "unlimited"
        mag_desc = f", max_mag: {max_apparent_magnitude}" if max_apparent_magnitude is not None else ""
        print(f"[GaiaDR3Provider] Submitting query for Gaia DR3 (radius: {radius_degrees}°, {limit_desc}{mag_desc})...")
        t0 = time.time()
        table = self._execute_query(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            radius_deg=radius_degrees,
            limit=limit,
            max_mag=max_apparent_magnitude
        )
        elapsed = time.time() - t0

        if table is None or len(table) == 0:
            print(f"[GaiaDR3Provider] Gaia DR3 query returned 0 rows in {elapsed:.2f}s.")
            return []

        total_rows = len(table)
        print(f"[GaiaDR3Provider] Received {total_rows} rows from Gaia DR3 in {elapsed:.2f}s. Computing 3D Cartesian coordinates...")

        records: list[StarRecord] = []
        for idx, row in enumerate(table, 1):
            record = self._row_to_star_record(row, default_distance_pc=default_distance_pc)
            if record is not None:
                records.append(record)
            if total_rows > 500 and (idx % 1000 == 0 or idx == total_rows):
                print(f"[GaiaDR3Provider] Progress: processed {idx}/{total_rows} stars ({(idx / total_rows) * 100:.1f}%)...")

        print(f"[GaiaDR3Provider] Complete: mapped {len(records)}/{total_rows} stars to 3D Cartesian space.")
        return records

    def resolve_distance(
        self,
        coord: SkyCoord,
        search_radius_arcsec: float = 2.0,
        source_id: int | None = None,
        **kwargs: Any
    ) -> DistanceResult | None:
        """Resolves distance and uncertainties for a target coordinate or Gaia Source ID."""
        if source_id is not None:
            table = self._query_by_source_id(source_id)
        else:
            # Query fast VizieR catalog first for single-object lookups to avoid ESA TAP job creation latency
            table = self._query_vizier_cone(
                ra_deg=float(coord.ra.deg),
                dec_deg=float(coord.dec.deg),
                radius_deg=search_radius_arcsec / 3600.0,
                limit=1
            )
            if table is None or len(table) == 0:
                # Fallback to ESA TAP if needed
                table = self._execute_query(
                    ra_deg=float(coord.ra.deg),
                    dec_deg=float(coord.dec.deg),
                    radius_deg=search_radius_arcsec / 3600.0,
                    limit=1
                )

        if table is None or len(table) == 0:
            return None

        row = table[0]
        plx = safe_float(row['parallax'], default=None)
        e_plx = safe_float(row['parallax_error'], default=None)

        return distance_from_parallax(
            parallax_mas=plx,
            parallax_error_mas=e_plx,
            source=self.source
        )

    def _query_vizier_cone(self, ra_deg: float, dec_deg: float, radius_deg: float, limit: int = 1) -> Table | None:
        """Fast indexed cone query against VizieR I/355/gaiadr3."""
        try:
            v = Vizier(catalog='I/355/gaiadr3', columns=['Source', 'RA_ICRS', 'DE_ICRS', 'Plx', 'e_Plx', 'Gmag'], row_limit=limit)
            sc = SkyCoord(ra=ra_deg * astrounits.deg, dec=dec_deg * astrounits.deg, frame='icrs')
            res = v.query_region(sc, radius=radius_deg * astrounits.deg)
            if res and len(res) > 0:
                t = res[0]
                t.rename_column('Source', 'source_id')
                t.rename_column('RA_ICRS', 'ra')
                t.rename_column('DE_ICRS', 'dec')
                t.rename_column('Plx', 'parallax')
                t.rename_column('e_Plx', 'parallax_error')
                t.rename_column('Gmag', 'phot_g_mean_mag')
                return t
        except Exception:
            pass
        return None

    def _execute_query(
        self,
        ra_deg: float,
        dec_deg: float,
        radius_deg: float,
        limit: int | None,
        max_mag: float | None = None
    ) -> Table | None:
        """Executes Gaia ADQL query via ESA TAP with automatic VizieR fallback if ESA TAP times out."""
        top_clause = f"TOP {limit} " if (limit is not None and limit > 0) else ""
        mag_clause = f"AND phot_g_mean_mag <= {max_mag} " if max_mag is not None else ""

        adql = f"""
        SELECT {top_clause}source_id, ra, dec, parallax, parallax_error,
               pmra, pmdec, phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag,
               bp_rp, teff_gspphot
        FROM gaiadr3.gaia_source
        WHERE 1=CONTAINS(
            POINT('ICRS', ra, dec),
            CIRCLE('ICRS', {ra_deg:.6f}, {dec_deg:.6f}, {radius_deg:.6f})
        )
        {mag_clause}
        ORDER BY phot_g_mean_mag ASC
        """

        if self._use_tap:
            try:
                job = Gaia.launch_job(adql)
                return job.get_results()
            except Exception as e:
                print(f"[GaiaDR3] ESA TAP query failed or timed out ({e}). Falling back to VizieR I/355...")

        # Fallback to VizieR I/355/gaiadr3
        try:
            v = Vizier(
                catalog='I/355/gaiadr3',
                columns=['Source', 'RA_ICRS', 'DE_ICRS', 'Plx', 'e_Plx', 'Gmag', 'BPmag', 'RPmag', 'BP-RP', 'Teff'],
                row_limit=limit if (limit is not None and limit > 0) else -1
            )
            sc = SkyCoord(ra=ra_deg * astrounits.deg, dec=dec_deg * astrounits.deg, frame='icrs')
            results = v.query_region(sc, radius=radius_deg * astrounits.deg)
            if results and len(results) > 0:
                t = results[0]
                # Normalize column names to match Gaia DR3 TAP output
                t.rename_column('Source', 'source_id')
                t.rename_column('RA_ICRS', 'ra')
                t.rename_column('DE_ICRS', 'dec')
                t.rename_column('Plx', 'parallax')
                t.rename_column('e_Plx', 'parallax_error')
                t.rename_column('Gmag', 'phot_g_mean_mag')
                t.rename_column('BPmag', 'phot_bp_mean_mag')
                t.rename_column('RPmag', 'phot_rp_mean_mag')
                t.rename_column('BP-RP', 'bp_rp')
                if 'Teff' in t.colnames:
                    t.rename_column('Teff', 'teff_gspphot')
                return t
        except Exception as e:
            print(f"[GaiaDR3] VizieR fallback failed: {e}")

        return None

    def _query_by_source_id(self, source_id: int) -> Table | None:
        """Fetches a star record by Gaia source_id."""
        adql = f"""
        SELECT source_id, ra, dec, parallax, parallax_error,
               pmra, pmdec, phot_g_mean_mag, bp_rp, teff_gspphot
        FROM gaiadr3.gaia_source
        WHERE source_id = {source_id}
        """
        try:
            job = Gaia.launch_job(adql)
            return job.get_results()
        except Exception:
            try:
                v = Vizier(catalog='I/355/gaiadr3', columns=['Source', 'RA_ICRS', 'DE_ICRS', 'Plx', 'e_Plx', 'Gmag', 'BP-RP', 'Teff'])
                res = v.query_constraints(Source=source_id)
                if res and len(res) > 0:
                    t = res[0]
                    t.rename_column('Source', 'source_id')
                    t.rename_column('RA_ICRS', 'ra')
                    t.rename_column('DE_ICRS', 'dec')
                    t.rename_column('Plx', 'parallax')
                    t.rename_column('e_Plx', 'parallax_error')
                    t.rename_column('Gmag', 'phot_g_mean_mag')
                    t.rename_column('BP-RP', 'bp_rp')
                    if 'Teff' in t.colnames:
                        t.rename_column('Teff', 'teff_gspphot')
                    return t
            except Exception:
                pass
        return None

    def _row_to_star_record(self, row: Row | Any, default_distance_pc: float | None = None) -> StarRecord | None:
        """Transforms a Gaia DR3 row into a standardized StarRecord with Astropy 3D coordinates."""
        source_id = int(row['source_id'])
        ra_deg = float(row['ra'])
        dec_deg = float(row['dec'])

        plx = safe_float(row['parallax'], default=None)
        e_plx = safe_float(row['parallax_error'], default=None)

        dist_res = distance_from_parallax(
            parallax_mas=plx,
            parallax_error_mas=e_plx,
            source=self.source,
            fallback_pc=default_distance_pc
        )

        # 3D Mapping via Astropy SkyCoord
        sc_3d = create_skycoord_3d(ra_deg, dec_deg, dist_res.distance_pc)
        cart_pos = skycoord_to_cartesian_meters(sc_3d)

        g_mag = safe_float(row['phot_g_mean_mag'], default=None)
        teff = safe_float(row['teff_gspphot'], default=None) if 'teff_gspphot' in row.colnames else None
        bp_rp = safe_float(row['bp_rp'], default=None) if 'bp_rp' in row.colnames else None

        # Derive spectral classification and surface temperature
        stype, ssub, derived_teff = classify_spectral_type(teff_k=teff, bp_rp=bp_rp)

        clean_name, body_id = sanitize_name_and_id(f"Gaia DR3 {source_id}", fallback_prefix=f"GAIA_{source_id}")

        return StarRecord(
            name=clean_name,
            body_id=body_id,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            distance=dist_res,
            apparent_magnitude=g_mag,
            magnitude_band="G",
            spectral_type=stype,
            spectral_subtype=ssub,
            surface_temperature_k=(teff if teff is not None else derived_teff),
            cartesian_position_m=cart_pos,
            extra_metadata={
                "gaia_source_id": source_id,
                "bp_rp": bp_rp
            }
        )
