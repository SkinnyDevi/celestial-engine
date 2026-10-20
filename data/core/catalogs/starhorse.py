from typing import Any
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
    classify_spectral_type,
    sanitize_name_and_id,
)
from .coords import (
    distance_from_kpc,
    create_skycoord_3d,
    skycoord_to_cartesian_meters,
    resolve_center_coord,
)
from core.math import safe_float

class StarHorseProvider(BaseCatalogProvider):
    """
    Provider for StarHorse (Anders et al. 2022) results for Gaia EDR3/DR3.
    - Catalog: I/354/starhorse2021 via VizieR
    - Object Count: ~360 Million
    - Distance Method: Multi-band optical (Gaia) + IR (2MASS, AllWISE) + PARSEC stellar evolutionary models
    - Best Use Case: Accurate distances through dust and dense fields (e.g. Galactic plane, bulge, obscured regions)
    """

    CATALOG_ID = 'I/354/starhorse2021'

    def __init__(self) -> None:
        self._vizier = Vizier(
            catalog=self.CATALOG_ID,
            columns=[
                'Source', 'RA_ICRS', 'DE_ICRS', 'dist50', 'mass50',
                'teff50', 'logg50', 'met50', 'AV50', 'fidelity',
                'GMAG0', 'BP-RP0'
            ]
        )

    @property
    def source(self) -> CatalogSource:
        return CatalogSource.STARHORSE

    @property
    def distance_method(self) -> DistanceMethod:
        return DistanceMethod.STELLAR_MODELS

    def query_region(
        self,
        center: str | SkyCoord,
        radius_degrees: float,
        limit: int | None = 100,
        default_distance_pc: float | None = None,
        **kwargs: Any
    ) -> list[StarRecord]:
        """
        Queries StarHorse stars in a cone around center coordinates.
        Ideal for dense and dusty fields where optical-only parallaxes suffer high extinction.
        """
        coord = resolve_center_coord(center)

        prev_limit = self._vizier.ROW_LIMIT
        self._vizier.ROW_LIMIT = limit if (limit is not None and limit > 0) else -1
        limit_desc = f"limit: {limit}" if (limit is not None and limit > 0) else "unlimited"
        print(f"[StarHorseProvider] Submitting cone query to VizieR {self.CATALOG_ID} (radius: {radius_degrees}°, {limit_desc})...")
        t0 = time.time()
        try:
            results = self._vizier.query_region(coord, radius=radius_degrees * astrounits.deg)
        finally:
            self._vizier.ROW_LIMIT = prev_limit
        elapsed = time.time() - t0

        if not results or len(results) == 0:
            print(f"[StarHorseProvider] VizieR query returned 0 rows in {elapsed:.2f}s.")
            return []

        table: Table = results[0]
        total_rows = len(table)
        print(f"[StarHorseProvider] Received {total_rows} rows from VizieR in {elapsed:.2f}s. Computing 3D Cartesian coordinates & stellar models...")

        records: list[StarRecord] = []
        for idx, row in enumerate(table, 1):
            rec = self._row_to_star_record(row, default_distance_pc=default_distance_pc)
            if rec is not None:
                records.append(rec)
            if total_rows > 500 and (idx % 1000 == 0 or idx == total_rows):
                print(f"[StarHorseProvider] Progress: processed {idx}/{total_rows} stars ({(idx / total_rows) * 100:.1f}%)...")

        print(f"[StarHorseProvider] Complete: mapped {len(records)}/{total_rows} stars with stellar models & 3D coordinates.")
        return records

    def resolve_distance(
        self,
        coord: SkyCoord,
        search_radius_arcsec: float = 2.0,
        source_id: int | None = None,
        **kwargs: Any
    ) -> DistanceResult | None:
        """
        Resolves StarHorse model distance and extinction for a star by Gaia Source ID or coordinates.
        """
        table: Table | None = None
        if source_id is not None:
            res = self._vizier.query_constraints(Source=source_id)
            if res and len(res) > 0:
                table = res[0]
        else:
            res = self._vizier.query_region(coord, radius=(search_radius_arcsec / 3600.0) * astrounits.deg)
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
        """Extracts distance from StarHorse dist50 (in kpc) and converts to pc via Astropy."""
        dist50_kpc = safe_float(row['dist50'], default=None)
        av = safe_float(row['AV50'], default=None)

        if dist50_kpc is not None and dist50_kpc > 0:
            return distance_from_kpc(
                dist_kpc=dist50_kpc,
                method=self.distance_method,
                source=self.source,
                metadata={"av_extinction": av, "fidelity": safe_float(row['fidelity'], default=1.0)}
            )
        else:
            default_pc = default_distance_pc if default_distance_pc is not None else 0.0
            return distance_from_kpc(
                dist_kpc=default_pc / 1000.0,
                method=DistanceMethod.DEFAULT_FALLBACK,
                source=self.source,
                metadata={"av_extinction": av}
            )

    def _row_to_star_record(
        self,
        row: Row | Any,
        default_distance_pc: float | None = None
    ) -> StarRecord | None:
        """Transforms a StarHorse row into a StarRecord with 3D Cartesian coordinates and stellar properties."""
        source_id = int(row['Source'])
        ra_deg = float(row['RA_ICRS'])
        dec_deg = float(row['DE_ICRS'])

        dist_res = self._extract_distance_result(row, default_distance_pc=default_distance_pc)

        # 3D Cartesian position via Astropy
        sc_3d = create_skycoord_3d(ra_deg, dec_deg, dist_res.distance_pc)
        cart_pos = skycoord_to_cartesian_meters(sc_3d)

        # Physical parameters derived from stellar models
        mass_solar = safe_float(row['mass50'], default=1.0)
        mass_kg = mass_solar * 1.989e30
        teff = safe_float(row['teff50'], default=None)
        logg = safe_float(row['logg50'], default=None)
        av = safe_float(row['AV50'], default=None)
        gmag = safe_float(row['GMAG0'], default=None) if 'GMAG0' in row.colnames else None
        bp_rp = safe_float(row['BP-RP0'], default=None) if 'BP-RP0' in row.colnames else None

        stype, ssub, derived_teff = classify_spectral_type(teff_k=teff, bp_rp=bp_rp)

        clean_name, body_id = sanitize_name_and_id(f"StarHorse {source_id}", fallback_prefix=f"SH_{source_id}")

        return StarRecord(
            name=clean_name,
            body_id=body_id,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            distance=dist_res,
            apparent_magnitude=gmag,
            magnitude_band="G" if gmag is not None else None,
            spectral_type=stype,
            spectral_subtype=ssub,
            surface_temperature_k=(teff if teff is not None else derived_teff),
            mass_kg=mass_kg,
            logg=logg,
            extinction_av=av,
            cartesian_position_m=cart_pos,
            extra_metadata={
                "gaia_source_id": source_id,
                "fidelity": safe_float(row['fidelity'], default=1.0),
                "metallicity": safe_float(row['met50'], default=None),
                "bp_rp": bp_rp
            }
        )
