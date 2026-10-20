from typing import Any
import time

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table, Row
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
    distance_from_pc,
    create_skycoord_3d,
    skycoord_to_cartesian_meters,
    resolve_center_coord,
)
from core.math import safe_float

class BailerJonesProvider(BaseCatalogProvider):
    """
    Provider for Bailer-Jones et al. (2021) distances to 1.47 billion stars in Gaia EDR3/DR3.
    - Catalog: I/352/gedr3dis via VizieR
    - Object Count: ~1.47 Billion
    - Distance Method: Bayesian geometric (rgeo) & photogeometric (rpgeo)
    - Best Use Case: Prevents line-of-sight stretching/errors by applying space density and stellar models
    """

    CATALOG_ID = 'I/352/gedr3dis'

    def __init__(self, prefer_photogeometric: bool = True) -> None:
        self.prefer_photogeometric = prefer_photogeometric
        self._vizier = Vizier(
            catalog=self.CATALOG_ID,
            columns=['Source', 'RA_ICRS', 'DE_ICRS', 'rgeo', 'b_rgeo', 'B_rgeo', 'rpgeo', 'b_rpgeo', 'B_rpgeo', 'Flag']
        )

    @property
    def source(self) -> CatalogSource:
        return CatalogSource.BAILER_JONES

    @property
    def distance_method(self) -> DistanceMethod:
        return DistanceMethod.BAYESIAN_PHOTOGEOMETRIC if self.prefer_photogeometric else DistanceMethod.BAYESIAN_GEOMETRIC

    def query_region(
        self,
        center: str | SkyCoord,
        radius_degrees: float,
        limit: int | None = 100,
        default_distance_pc: float | None = None,
        **kwargs: Any
    ) -> list[StarRecord]:
        """
        Queries Bailer-Jones distances in a cone around center coordinates.
        Maps coordinates to 3D Cartesian space using Bayesian distance estimates.
        """
        coord = resolve_center_coord(center)

        prev_limit = self._vizier.ROW_LIMIT
        self._vizier.ROW_LIMIT = limit if (limit is not None and limit > 0) else -1
        limit_desc = f"limit: {limit}" if (limit is not None and limit > 0) else "unlimited"
        print(f"[BailerJonesProvider] Submitting cone query to VizieR {self.CATALOG_ID} (radius: {radius_degrees}°, {limit_desc})...")
        t0 = time.time()
        results = None
        try:
            for attempt in range(3):
                try:
                    results = self._vizier.query_region(coord, radius=radius_degrees * u.deg)
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f"Warning: VizieR query failed after 3 attempts ({e}).")
                    else:
                        time.sleep(1.0)
        finally:
            self._vizier.ROW_LIMIT = prev_limit
        elapsed = time.time() - t0

        if not results or len(results) == 0:
            print(f"[BailerJonesProvider] VizieR query returned 0 rows in {elapsed:.2f}s.")
            return []

        table: Table = results[0]
        total_rows = len(table)
        print(f"[BailerJonesProvider] Received {total_rows} rows from VizieR in {elapsed:.2f}s. Fetching companion Gaia DR3 photometry & temperatures...")

        gaia_map = self._fetch_gaia_photometry_map(coord, radius_degrees, limit=limit)

        records: list[StarRecord] = []
        for idx, row in enumerate(table, 1):
            rec = self._row_to_star_record(row, default_distance_pc=default_distance_pc, gaia_map=gaia_map)
            if rec is not None:
                records.append(rec)
            if total_rows > 500 and (idx % 1000 == 0 or idx == total_rows):
                print(f"[BailerJonesProvider] Progress: processed {idx}/{total_rows} stars ({(idx / total_rows) * 100:.1f}%)...")

        print(f"[BailerJonesProvider] Complete: mapped {len(records)}/{total_rows} stars to 3D Cartesian space with spectral classification.")
        return records

    def _fetch_gaia_photometry_map(
        self,
        coord: SkyCoord,
        radius_degrees: float,
        limit: int | None = 100
    ) -> dict[int, Row | Any]:
        """Fetches companion Gaia DR3 Gmag, BP-RP, and Teff to enrich Bailer-Jones records."""
        try:
            row_limit = min(limit * 3, 10000) if (limit is not None and limit > 0) else -1
            v = Vizier(columns=['Source', 'Gmag', 'BP-RP', 'Teff'], row_limit=row_limit)
            res = v.query_region(coord, radius=radius_degrees * u.deg, catalog='I/355/gaiadr3')
            if res and len(res) > 0:
                tbl = res[0]
                return {int(r['Source']): r for r in tbl}
        except Exception:
            pass
        return {}

    def resolve_distance(
        self,
        coord: SkyCoord,
        search_radius_arcsec: float = 2.0,
        source_id: int | None = None,
        **kwargs: Any
    ) -> DistanceResult | None:
        """
        Resolves Bayesian distance for a star by Gaia Source ID or coordinates.
        Prevents line-of-sight elongation inherent to direct parallax inversion.
        """
        table: Table | None = None
        if source_id is not None:
            res = self._vizier.query_constraints(Source=source_id)
            if res and len(res) > 0:
                table = res[0]
        else:
            res = self._vizier.query_region(coord, radius=(search_radius_arcsec / 3600.0) * u.deg)
            if res and len(res) > 0:
                table = res[0]

        if table is None or len(table) == 0:
            return None

        row = table[0]
        return self._extract_distance_result(row)

    def _extract_distance_result(
        self,
        row: Row | Any,
        default_distance_pc: float | None = None
    ) -> DistanceResult:
        """Extracts Bayesian distance (photogeometric or geometric) and 16th/84th percentiles."""
        rpgeo = safe_float(row['rpgeo'], default=None)
        rgeo = safe_float(row['rgeo'], default=None)

        # Decide whether to use rpgeo (photogeometric) or rgeo (geometric)
        use_pgeo = self.prefer_photogeometric and rpgeo is not None and rpgeo > 0

        if use_pgeo:
            dist_pc = rpgeo
            b_err = safe_float(row['b_rpgeo'], default=None)
            B_err = safe_float(row['B_rpgeo'], default=None)
            method = DistanceMethod.BAYESIAN_PHOTOGEOMETRIC
        elif rgeo is not None and rgeo > 0:
            dist_pc = rgeo
            b_err = safe_float(row['b_rgeo'], default=None)
            B_err = safe_float(row['B_rgeo'], default=None)
            method = DistanceMethod.BAYESIAN_GEOMETRIC
        else:
            dist_pc = default_distance_pc if default_distance_pc is not None else 0.0
            b_err, B_err = None, None
            method = DistanceMethod.DEFAULT_FALLBACK

        return distance_from_pc(
            dist_pc=dist_pc,
            lower_pc=b_err,
            upper_pc=B_err,
            method=method,
            source=self.source,
            metadata={"flag": safe_float(row['Flag'], default=0)}
        )

    def _row_to_star_record(
        self,
        row: Row | Any,
        default_distance_pc: float | None = None,
        gaia_map: dict[int, Row | Any] | None = None
    ) -> StarRecord | None:
        """Transforms a Bailer-Jones row into a StarRecord with 3D Cartesian coordinates and spectral classification."""
        source_id = int(row['Source'])
        ra_deg = float(row['RA_ICRS'])
        dec_deg = float(row['DE_ICRS'])

        dist_res = self._extract_distance_result(row, default_distance_pc=default_distance_pc)

        # 3D Cartesian position via Astropy
        sc_3d = create_skycoord_3d(ra_deg, dec_deg, dist_res.distance_pc)
        cart_pos = skycoord_to_cartesian_meters(sc_3d)

        g_mag: float | None = None
        teff: float | None = None
        bp_rp: float | None = None

        if gaia_map and source_id in gaia_map:
            g_row = gaia_map[source_id]
            g_mag = safe_float(g_row['Gmag'], default=None) if 'Gmag' in g_row.colnames else None
            bp_rp = safe_float(g_row['BP-RP'], default=None) if 'BP-RP' in g_row.colnames else None
            teff = safe_float(g_row['Teff'], default=None) if 'Teff' in g_row.colnames else None

        stype, ssub, derived_teff = classify_spectral_type(teff_k=teff, bp_rp=bp_rp)

        clean_name, body_id = sanitize_name_and_id(f"Bailer-Jones {source_id}", fallback_prefix=f"BJ_{source_id}")

        return StarRecord(
            name=clean_name,
            body_id=body_id,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            distance=dist_res,
            apparent_magnitude=g_mag,
            magnitude_band="G" if g_mag is not None else None,
            spectral_type=stype,
            spectral_subtype=ssub,
            surface_temperature_k=(teff if teff is not None else derived_teff),
            cartesian_position_m=cart_pos,
            extra_metadata={
                "gaia_source_id": source_id,
                "rgeo_pc": safe_float(row['rgeo'], default=None),
                "rpgeo_pc": safe_float(row['rpgeo'], default=None),
                "flag": safe_float(row['Flag'], default=0),
                "bp_rp": bp_rp
            }
        )
