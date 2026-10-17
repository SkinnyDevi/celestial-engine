from astropy.coordinates import SkyCoord
from enum import Enum
import time
import re
import json
import math
from typing import Any, TextIO

import numpy as np
import astropy.units as astrounit
from astroquery.jplhorizons import Horizons, HorizonsClass
from astroquery.simbad import Simbad, SimbadClass
from astropy.time import Time
from astropy.table import Table, Row

from core.constants import *
from core.space import (
    OpticalMagBands,
    SpectralType,
    PlanetClass,
    AtmosphereType,
    MoonClass,
)
from core.math import *
from core.catalogs import (
    CatalogSource,
    DistanceMethod,
    DistanceResult,
    StarRecord,
    PreciseDistanceResolver,
    create_skycoord_3d,
    skycoord_to_cartesian_meters,
    distance_from_parallax,
    classify_spectral_type,
)

class CelestialImporter:
    sim_time: Time
    max_apparent_magnitude: float | None
    keep_unmeasured: bool
    orbits: list[dict[str, Any]]
    stars: list[dict[str, Any]]
    planets: list[dict[str, Any]]
    moons: list[dict[str, Any]]
    star_indices: dict[str, int]
    planet_indices: dict[str, int]
    simbad: SimbadClass
    distance_resolver: PreciseDistanceResolver

    def __init__(
        self,
        sim_time: Time,
        max_apparent_magnitude: float | None = None,
        keep_unmeasured: bool = True,
        distance_resolver: PreciseDistanceResolver | None = None,
        prefer_photogeometric: bool = True,
    ) -> None:
        self.sim_time: Time = sim_time
        self.max_apparent_magnitude: float | None = max_apparent_magnitude
        self.keep_unmeasured: bool = keep_unmeasured
        self.orbits: list[dict[str, Any]] = []
        self.stars: list[dict[str, Any]] = []
        self.planets: list[dict[str, Any]] = []
        self.moons: list[dict[str, Any]] = []
        
        self.star_indices: dict[str, int] = {}
        self.planet_indices: dict[str, int] = {}
        
        # Configure Simbad
        self.simbad: SimbadClass = Simbad()
        self.simbad.ROW_LIMIT = -1
        self._init_simbad_fields()

        # Configure Precise Distance Resolver
        self.distance_resolver: PreciseDistanceResolver = (
            distance_resolver if distance_resolver is not None else PreciseDistanceResolver(prefer_photogeometric=prefer_photogeometric)
        )

    def _init_simbad_fields(self) -> None:
        """Initializes votable fields on the Simbad query instance with retry for resilience."""

        fields_to_add: list[str] = ['plx_value', 'sp_type'] + OpticalMagBands.list()
        attempt: int
        for attempt in range(3):
            try:
                self.simbad.add_votable_fields(*fields_to_add)
                break
            except Exception as e:
                if attempt == 2:
                    print(f"Warning: Failed to configure Simbad votable fields ({e}). Basic fields will be used.")
                else:
                    time.sleep(1.0)

    def _get_apparent_magnitude(self, row: Row | Any) -> tuple[float, OpticalMagBands] | tuple[None, None]:
        """
        Extracts the best available apparent optical magnitude from a Simbad result row.
        Checks standard optical filters (V, G, g, r, R, B, I) in order of preference.
        Returns (float_magnitude, band_name) or (None, None).
        """

        band: str
        for band in OpticalMagBands.list():
            if band in row.colnames and not np.ma.is_masked(row[band]):
                val: float | None = safe_float(row[band], default=None)
                if val is not None:
                    return val, OpticalMagBands.from_str(band)

        return None, None

    def _fetch_orbit_jpl(self, jpl_id: str, center_id: str) -> tuple[int, dict[str, float], Table]:
        print(f"Fetching orbital data for JPL ID {jpl_id}...")
        obj: HorizonsClass = Horizons(id=jpl_id, location=center_id, epochs=self.sim_time.jd)
        elements: Table = obj.elements()
        vectors: Table = obj.vectors()
        
        orbit: dict[str, Any] = {
            "semimajor_axis": safe_float(elements['a'][0]) * AU_TO_METERS,
            "eccentricity": safe_float(elements['e'][0]),
            "inclination": safe_float(elements['incl'][0]) * DEG_TO_RAD,
            "longitude_of_ascending_node": safe_float(elements['Omega'][0]) * DEG_TO_RAD,
            "argument_of_periapsis": safe_float(elements['w'][0]) * DEG_TO_RAD,
            "mean_anomaly_at_epoch": safe_float(elements['M'][0]) * DEG_TO_RAD,
            "orbital_period_days": safe_float(elements['P'][0]),
            "center_position": {"x": 0.0, "y": 0.0, "z": 0.0}
        }
        
        self.orbits.append(orbit)
        
        position: dict[str, float] = {
            "x": safe_float(vectors['x'][0]) * AU_TO_METERS,
            "y": safe_float(vectors['y'][0]) * AU_TO_METERS,
            "z": safe_float(vectors['z'][0]) * AU_TO_METERS
        }
        return len(self.orbits) - 1, position, elements
    
    def parse_spectral_type(self, sp_str: str | bytes | Any | None) -> tuple[SpectralType, int] | tuple[None, None]:
        if not sp_str or np.ma.is_masked(sp_str):
            return None, None
            
        sp_clean: str = sp_str.decode('utf-8') if isinstance(sp_str, bytes) else str(sp_str)
        sp_clean = sp_clean.strip().upper()
        match: re.Match[str] | None = re.search(r'([OBAFGKM])(\d(?:\.\d)?)?', sp_clean)
        if not match:
            return None, None
            
        try:
            s_class: SpectralType = SpectralType[match.group(1)]
        except KeyError:
            return None, None
        s_sub: int = int(round(float(match.group(2)))) if match.group(2) else 0
        return s_class, s_sub

    def add_star_manual(self, name: str, body_id: str, **kwargs: Any) -> None:
        """Adds a star to the registry manually with given physical parameters."""
        clean_name: str = re.sub(r'[*]+', '', name).strip()
        clean_body_id: str = re.sub(r'[^A-Za-z0-9_]', '_', body_id).strip('_')[:31].upper()
        star: dict[str, Any] = {
            "name": clean_name,
            "body_id": clean_body_id,
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
        }
        for k, v in kwargs.items():
            star[k] = v.value if isinstance(v, Enum) else v
        self.stars.append(star)
        self.star_indices[name] = len(self.stars) - 1
        self.star_indices[clean_name] = len(self.stars) - 1
        print(f"Added star {clean_name}")

    def add_star_simbad(
        self,
        name: str,
        body_id: str,
        mass_kg: float,
        radius_m: float,
        max_apparent_magnitude: float | None = None,
        keep_unmeasured: bool | None = None,
        use_precise_distances: bool = False,
        precise_source: CatalogSource | str = CatalogSource.AUTO,
        **kwargs: Any,
    ) -> None:
        """Fetches RA/Dec/Distance for a star from Simbad and adds it, with optional magnitude filtering and precise distance enrichment."""
        print(f"Fetching Simbad data for {name}...")
        result: Table | None = self.simbad.query_object(name)
        if result is None:
            print(f"Failed to find {name} in Simbad.")
            return
        
        mag: float | None
        band: OpticalMagBands | None
        mag, band = self._get_apparent_magnitude(result[0])
        cutoff: float | None = self.max_apparent_magnitude if max_apparent_magnitude is None else max_apparent_magnitude
        keep_unm: bool = self.keep_unmeasured if keep_unmeasured is None else keep_unmeasured
        
        if cutoff is not None:
            if mag is not None and mag > cutoff:
                band_str: str = band.value if band is not None else ""
                print(f"Skipping {name}: apparent magnitude {mag:.2f} ({band_str}) is fainter than limit {cutoff}")
                return
            if mag is None and not keep_unm:
                print(f"Skipping {name}: no apparent magnitude measured and keep_unmeasured=False")
                return

        ra_deg: float = float(result['ra'][0])
        dec_deg: float = float(result['dec'][0])
        ra_rad: float = ra_deg * DEG_TO_RAD
        dec_rad: float = dec_deg * DEG_TO_RAD
        
        # Calculate distance in parsecs from parallax (if available) with Astropy
        plx: float | None = float(result['plx_value'][0]) if not np.ma.is_masked(result['plx_value'][0]) else None
        dist_res = distance_from_parallax(plx, source=CatalogSource.SIMBAD, fallback_pc=0.0)
        dist_pc: float = dist_res.distance_pc
        
        # Calculate 3D cartesian coordinates in meters using Astropy SkyCoord
        sc_3d = create_skycoord_3d(ra_deg, dec_deg, dist_pc)
        cart_pos = skycoord_to_cartesian_meters(sc_3d)
        
        clean_name: str = re.sub(r'[*]+', '', name).strip()
        clean_body_id: str = re.sub(r'[^A-Za-z0-9_]', '_', body_id).strip('_')[:31].upper()
        star: dict[str, Any] = {
            "name": clean_name,
            "body_id": clean_body_id,
            "position": cart_pos,
            "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            "right_ascension_rad": ra_rad,
            "declination_rad": dec_rad,
            "distance_pc": dist_pc,
            "mass_kg": mass_kg,
            "radius_m": radius_m
        }
        if mag is not None:
            star["apparent_magnitude"] = round(mag, 4)
        for k, v in kwargs.items():
            star[k] = v.value if isinstance(v, Enum) else v

        # Optional precision distance enrichment from Gaia DR3, Bailer-Jones, StarHorse, or Hipparcos
        if use_precise_distances:
            enriched = self.distance_resolver.enrich_star_dict(star, preferred_source=precise_source)
            if enriched:
                print(f"Enriched {clean_name} with precise distance from {star.get('distance_source')} ({star.get('distance_pc')} pc via {star.get('distance_method')})")

        self.stars.append(star)
        self.star_indices[name] = len(self.stars) - 1
        self.star_indices[clean_name] = len(self.stars) - 1
        
        # Parse and set spectral type with fallback to B-V color and temperature
        sp_type_str: Any = result['sp_type'][0] if 'sp_type' in result.colnames and not np.ma.is_masked(result['sp_type'][0]) else None
        b_mag = safe_float(result['B'][0], default=None) if 'B' in result.colnames and not np.ma.is_masked(result['B'][0]) else None
        v_mag = safe_float(result['V'][0], default=None) if 'V' in result.colnames and not np.ma.is_masked(result['V'][0]) else None
        b_v = (b_mag - v_mag) if (b_mag is not None and v_mag is not None) else None

        stype, ssubtype, teff = classify_spectral_type(sp_str=sp_type_str, b_v=b_v)
        star["spectral_type"] = stype.value
        star["spectral_subtype"] = ssubtype
        if "surface_temperature_k" not in star:
            star["surface_temperature_k"] = round(float(teff), 2)
            
        mag_str: str = f" (mag {mag:.2f} [{band.value}])" if mag is not None and band is not None else ""
        print(f"Added star {clean_name}{mag_str} from Simbad [Spectral: {stype.name}{ssubtype}, Teff: {teff:.0f}K]")

    def add_nearby_stars(
        self,
        max_distance_ly: float | None = None,
        max_distance_pc: float | None = None,
        limit: int | None = 50,
        mass_kg_default: float = 1.989e30,
        radius_m_default: float = 696340000.0,
        max_apparent_magnitude: float | None = None,
        keep_unmeasured: bool | None = None,
        use_precise_distances: bool = False,
        precise_source: CatalogSource | str = CatalogSource.AUTO,
    ) -> int:
        """
        Fetches stars within a 3D physical distance from the Sun (measured by parallax).
        `max_distance_ly`: Distance limit in light-years.
        `max_distance_pc`: Distance limit in parsecs.
        `limit`: Maximum number of stars to fetch (-1 or None for unlimited).
        `max_apparent_magnitude`: Apparent magnitude cutoff (drops stars fainter than this).
        `keep_unmeasured`: Whether to keep stars without catalog magnitude measurement.
        `use_precise_distances`: Whether to enrich distances using precision catalogs (Gaia, Bailer-Jones, etc.).
        """
        cutoff: float | None = self.max_apparent_magnitude if max_apparent_magnitude is None else max_apparent_magnitude
        keep_unm: bool = self.keep_unmeasured if keep_unmeasured is None else keep_unmeasured

        if max_distance_pc is None:
            if max_distance_ly is not None:
                max_distance_pc = max_distance_ly * LY_TO_PC
            else:
                max_distance_pc = 5.0  # default ~16.3 light-years
        
        dist_ly: float = max_distance_pc / LY_TO_PC
        min_plx: float = 1000.0 / max_distance_pc
        limit_desc: str = f"up to {limit}" if (limit is not None and limit > 0) else "all"
        mag_desc: str = f" with mag <= {cutoff}" if cutoff is not None else ""
        print(f"Fetching {limit_desc} nearby stars within {dist_ly:.1f} ly ({max_distance_pc:.1f} pc) of the Sun{mag_desc}...")
        
        top_clause: str = f"TOP {limit} " if (limit is not None and limit > 0) else ""
        query: str = (
            f"SELECT {top_clause}b.main_id, b.ra, b.dec, b.plx_value, b.otype, b.sp_type, "
            f"a.V, a.G, a.B, a.R, a.I "
            f"FROM basic b "
            f"LEFT JOIN allfluxes a ON b.oid = a.oidref "
            f"WHERE b.plx_value >= {min_plx:.4f} "
            f"ORDER BY plx_value DESC"
        )
        
        result: Table | None
        try:
            result = self.simbad.query_tap(query)
        except Exception as e:
            print(f"Failed to query nearby stars via TAP: {e}")
            return
            
        if result is None or len(result) == 0:
            print("No nearby stars found matching criteria.")
            return

        count: int = 0
        faint_filtered: int = 0
        unmeasured_filtered: int = 0
        row: Row
        for row in result:
            name: str | bytes = row['main_id']
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            name = name.strip()
            
            # Skip exoplanets
            otype: str = str(row['otype']) if ('otype' in result.colnames and not np.ma.is_masked(row['otype'])) else ''
            if otype.startswith('Pl'):
                continue
                
            clean_name: str = re.sub(r'[*]+', '', name).strip()
            if clean_name in self.star_indices or name in self.star_indices:
                continue

            mag: float | None
            band: OpticalMagBands | None
            mag, band = self._get_apparent_magnitude(row)
            if cutoff is not None:
                if mag is not None and mag > cutoff:
                    faint_filtered += 1
                    continue
                if mag is None and not keep_unm:
                    unmeasured_filtered += 1
                    continue
                
            body_id: str = re.sub(r'[^A-Za-z0-9_]', '_', clean_name).strip('_')[:31].upper()
            
            ra_deg: float = float(row['ra'])
            dec_deg: float = float(row['dec'])
            ra_rad: float = ra_deg * DEG_TO_RAD
            dec_rad: float = dec_deg * DEG_TO_RAD
            plx: float = float(row['plx_value'])
            dist_res = distance_from_parallax(plx, source=CatalogSource.SIMBAD)
            dist_pc: float = dist_res.distance_pc
            
            sc_3d = create_skycoord_3d(ra_deg, dec_deg, dist_pc)
            cart_pos = skycoord_to_cartesian_meters(sc_3d)
            
            star: dict[str, Any] = {
                "name": clean_name,
                "body_id": body_id,
                "position": cart_pos,
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                "right_ascension_rad": ra_rad,
                "declination_rad": dec_rad,
                "distance_pc": dist_pc,
                "mass_kg": mass_kg_default,
                "radius_m": radius_m_default
            }
            if mag is not None:
                star["apparent_magnitude"] = round(mag, 4)

            # Optional precision distance enrichment from Gaia DR3, Bailer-Jones, StarHorse, or Hipparcos
            if use_precise_distances:
                self.distance_resolver.enrich_star_dict(star, preferred_source=precise_source)

            self.stars.append(star)
            self.star_indices[name] = len(self.stars) - 1
            self.star_indices[clean_name] = len(self.stars) - 1

            sp_type_str: Any = row['sp_type'] if ('sp_type' in result.colnames and not np.ma.is_masked(row['sp_type'])) else None
            b_mag = safe_float(row['B'], default=None) if 'B' in result.colnames and not np.ma.is_masked(row['B']) else None
            v_mag = safe_float(row['V'], default=None) if 'V' in result.colnames and not np.ma.is_masked(row['V']) else None
            b_v = (b_mag - v_mag) if (b_mag is not None and v_mag is not None) else None

            stype, ssubtype, teff = classify_spectral_type(sp_str=sp_type_str, b_v=b_v)
            star["spectral_type"] = stype.value
            star["spectral_subtype"] = ssubtype
            if "surface_temperature_k" not in star:
                star["surface_temperature_k"] = round(float(teff), 2)

            count += 1
            
        msg: str = f"Added {count} nearby stars around the Sun."
        if faint_filtered > 0 or unmeasured_filtered > 0:
            msg += f" (Filtered {faint_filtered} faint stars with mag > {cutoff}"
            if unmeasured_filtered > 0:
                msg += f", {unmeasured_filtered} unmeasured"
            msg += ")"
        print(msg)
        return count

    def add_stars_in_region(
        self,
        center_name: str,
        radius_degrees: float,
        limit: int | None = 100,
        default_distance_pc: float | None = None,
        mass_kg_default: float = 1.989e30,
        radius_m_default: float = 696340000.0,
        max_apparent_magnitude: float | None = None,
        keep_unmeasured: bool | None = None,
        use_precise_distances: bool = False,
        precise_source: CatalogSource | str = CatalogSource.AUTO,
    ) -> None:
        """
        Fetches a batch of stars/objects around a specific celestial region (cone in the sky) and adds them.
        Ideal for extra-solar targets such as galaxies (e.g. 'M31'), nebulae, or clusters.
        `max_apparent_magnitude`: Apparent magnitude cutoff (drops objects fainter than this).
        `keep_unmeasured`: Whether to keep objects without catalog magnitude measurement.
        `use_precise_distances`: Enrich stars with precise distances from Gaia DR3, Bailer-Jones, StarHorse, or Hipparcos.
        """
        cutoff: float | None = self.max_apparent_magnitude if max_apparent_magnitude is None else max_apparent_magnitude
        keep_unm: bool = self.keep_unmeasured if keep_unmeasured is None else keep_unmeasured

        dist_pc: float
        if default_distance_pc is not None and default_distance_pc > 50000:
            # We are querying an external galaxy: ignore foreground Milky Way stars
            dist_pc = default_distance_pc

        if center_name.strip().lower() == "sun":
            print(f"Notice: 'Sun' is our local star (origin of coordinates) and does not exist as an extra-solar target in SIMBAD's sky catalog.")
            print(f"Redirecting query to fetch nearby stars by 3D distance ({radius_degrees} ly) from the Sun...")
            return self.add_nearby_stars(
                max_distance_ly=radius_degrees, limit=limit,
                mass_kg_default=mass_kg_default, radius_m_default=radius_m_default,
                max_apparent_magnitude=cutoff, keep_unmeasured=keep_unm
            )

        limit_desc: str = f"up to {limit}" if (limit is not None and limit > 0) else "all"
        mag_desc: str = f" with mag <= {cutoff}" if cutoff is not None else ""
        print(f"Fetching {limit_desc} objects around {center_name} (radius {radius_degrees} deg){mag_desc}...")
        
        prev_limit: int = self.simbad.ROW_LIMIT
        self.simbad.ROW_LIMIT = limit if (limit is not None and limit > 0) else -1
        result: Table | None
        try:
            result = self.simbad.query_region(center_name, radius=radius_degrees * astrounit.deg)
        finally:
            self.simbad.ROW_LIMIT = prev_limit
        
        if result is None:
            print(f"No objects found in region of {center_name}.")
            return
            
        count: int = 0
        faint_filtered: int = 0
        unmeasured_filtered: int = 0
        total: int = len(result) if result is not None else 0
        row: Row
        for row in result:
            name: str | bytes = row['main_id']
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            name = name.strip()
            
            clean_name: str = re.sub(r'[*]+', '', name).strip()
            if clean_name in self.star_indices or name in self.star_indices:
                continue

            mag: float | None
            band: OpticalMagBands | None
            mag, band = self._get_apparent_magnitude(row)
            if cutoff is not None:
                if mag is not None and mag > cutoff:
                    faint_filtered += 1
                    continue
                if mag is None and not keep_unm:
                    unmeasured_filtered += 1
                    continue
                
            body_id: str = re.sub(r'[^A-Za-z0-9_]', '_', clean_name).strip('_')[:31].upper()
            
            ra_deg: float = float(row['ra'])
            dec_deg: float = float(row['dec'])
            ra_rad: float = ra_deg * DEG_TO_RAD
            dec_rad: float = dec_deg * DEG_TO_RAD
            
            has_plx: bool = 'plx_value' in result.colnames and not np.ma.is_masked(row['plx_value'])
            plx: float | None = float(row['plx_value']) if has_plx else None
            
            dist_res = distance_from_parallax(plx, source=CatalogSource.SIMBAD, fallback_pc=default_distance_pc)
            dist_pc = dist_res.distance_pc
                
            # Compute 3D Cartesian coordinates via Astropy SkyCoord
            sc_3d = create_skycoord_3d(ra_deg, dec_deg, dist_pc)
            cart_pos = skycoord_to_cartesian_meters(sc_3d)
            
            star: dict[str, Any] = {
                "name": clean_name,
                "body_id": body_id,
                "position": cart_pos,
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                "right_ascension_rad": ra_rad,
                "declination_rad": dec_rad,
                "distance_pc": dist_pc,
                "mass_kg": mass_kg_default,
                "radius_m": radius_m_default
            }
            if mag is not None:
                star["apparent_magnitude"] = round(mag, 4)

            # Optional precision distance enrichment from Gaia DR3, Bailer-Jones, StarHorse, or Hipparcos
            if use_precise_distances:
                self.distance_resolver.enrich_star_dict(star, preferred_source=precise_source)

            self.stars.append(star)
            self.star_indices[name] = len(self.stars) - 1
            self.star_indices[clean_name] = len(self.stars) - 1

            sp_type_str: Any = row['sp_type'] if ('sp_type' in result.colnames and not np.ma.is_masked(row['sp_type'])) else None
            b_mag = safe_float(row['B'], default=None) if 'B' in result.colnames and not np.ma.is_masked(row['B']) else None
            v_mag = safe_float(row['V'], default=None) if 'V' in result.colnames and not np.ma.is_masked(row['V']) else None
            b_v = (b_mag - v_mag) if (b_mag is not None and v_mag is not None) else None

            stype, ssubtype, teff = classify_spectral_type(sp_str=sp_type_str, b_v=b_v)
            star["spectral_type"] = stype.value
            star["spectral_subtype"] = ssubtype
            if "surface_temperature_k" not in star:
                star["surface_temperature_k"] = round(float(teff), 2)
            
            count += 1
            if count % 1000 == 0:
                print(f"Progress: added {count} stars (checked {count + faint_filtered + unmeasured_filtered}/{total})...")
            
        msg: str = f"Added {count} objects from {center_name} region."
        if faint_filtered > 0 or unmeasured_filtered > 0:
            msg += f" (Filtered {faint_filtered} faint objects with mag > {cutoff}"
            if unmeasured_filtered > 0:
                msg += f", {unmeasured_filtered} unmeasured"
            msg += ")"
        print(msg)

    def add_stars_from_catalog(
        self,
        center_name: str,
        radius_degrees: float,
        source: CatalogSource | str = CatalogSource.AUTO,
        limit: int | None = 100,
        default_distance_pc: float | None = None,
        mass_kg_default: float = 1.989e30,
        radius_m_default: float = 696340000.0,
        max_apparent_magnitude: float | None = None,
        keep_unmeasured: bool | None = None,
    ) -> int:
        """
        Fetches stars around a center region using precision distance catalogs:
        - Gaia DR3 (geometric parallax, all-sky true 3D stellar positions)
        - Bailer-Jones (Bayesian geometric & photogeometric, prevents line-of-sight stretching/errors)
        - StarHorse (multi-band optical/IR + stellar models for dust/dense fields)
        - Hipparcos (trigonometric parallax for bright foreground stars m < 6)
        """
        cutoff: float | None = self.max_apparent_magnitude if max_apparent_magnitude is None else max_apparent_magnitude
        keep_unm: bool = self.keep_unmeasured if keep_unmeasured is None else keep_unmeasured

        if center_name.strip().lower() in ("sun", "sol"):
            print(f"Notice: 'Sun' is our local star (origin of coordinates) and does not exist as an extra-solar target in sky catalogs.")
            print(f"Redirecting query to fetch nearby stars by 3D distance ({radius_degrees} ly) from the Sun...")
            return self.add_nearby_stars(
                max_distance_ly=radius_degrees,
                limit=limit,
                mass_kg_default=mass_kg_default,
                radius_m_default=radius_m_default,
                max_apparent_magnitude=cutoff,
                keep_unmeasured=keep_unm,
                use_precise_distances=False,
                precise_source=source,
            )

        records: list[StarRecord] = self.distance_resolver.query_region(
            center=center_name,
            radius_degrees=radius_degrees,
            source=source,
            limit=limit,
            max_apparent_magnitude=cutoff,
            default_distance_pc=default_distance_pc,
        )

        total_fetched = len(records)
        print(f"[CelestialImporter] Ingesting {total_fetched} stars from '{source if isinstance(source, str) else source.value}' into celestial engine...")

        added_count: int = 0
        faint_filtered: int = 0
        unmeasured_filtered: int = 0
        duplicate_filtered: int = 0

        for idx, rec in enumerate(records, 1):
            if rec.name in self.star_indices or rec.body_id in self.star_indices:
                duplicate_filtered += 1
                continue

            if cutoff is not None:
                if rec.apparent_magnitude is not None and rec.apparent_magnitude > cutoff:
                    faint_filtered += 1
                    continue
                if rec.apparent_magnitude is None and not keep_unm:
                    unmeasured_filtered += 1
                    continue

            if rec.mass_kg == 1.989e30 and mass_kg_default != 1.989e30:
                rec.mass_kg = mass_kg_default
            if rec.radius_m == 696340000.0 and radius_m_default != 696340000.0:
                rec.radius_m = radius_m_default

            star_dict = rec.to_engine_dict()
            star_dict["distance_method"] = rec.distance.method.value
            star_dict["distance_source"] = rec.distance.source.value
            if rec.distance.distance_error_lower_pc is not None:
                star_dict["distance_error_lower_pc"] = round(rec.distance.distance_error_lower_pc, 4)
            if rec.distance.distance_error_upper_pc is not None:
                star_dict["distance_error_upper_pc"] = round(rec.distance.distance_error_upper_pc, 4)

            self.stars.append(star_dict)
            self.star_indices[rec.name] = len(self.stars) - 1
            self.star_indices[rec.body_id] = len(self.stars) - 1
            added_count += 1

            if total_fetched > 1000 and (idx % 1000 == 0 or idx == total_fetched):
                print(f"[CelestialImporter] Ingestion progress: {idx}/{total_fetched} (added: {added_count}, skipped: {duplicate_filtered + faint_filtered + unmeasured_filtered})...")

        source_label = source if isinstance(source, str) else source.value
        msg = f"[CelestialImporter] Added {added_count} stars from catalog '{source_label}' in region {center_name}."
        filters = []
        if duplicate_filtered > 0:
            filters.append(f"{duplicate_filtered} duplicates")
        if faint_filtered > 0:
            filters.append(f"{faint_filtered} faint [mag > {cutoff}]")
        if unmeasured_filtered > 0:
            filters.append(f"{unmeasured_filtered} unmeasured")
        if filters:
            msg += f" (Filtered: {', '.join(filters)})"
        print(msg)
        return added_count

    def add_star_precise(
        self,
        name: str,
        body_id: str | None = None,
        source: CatalogSource | str = CatalogSource.AUTO,
        mass_kg: float = 1.989e30,
        radius_m: float = 696340000.0,
        max_apparent_magnitude: float | None = None,
        **kwargs: Any
    ) -> bool:
        """
        Adds a single star using precise distance resolving from Gaia DR3, Bailer-Jones,
        StarHorse, or Hipparcos based on the star's magnitude and position.
        """
        clean_name = re.sub(r'[*]+', '', name).strip()
        bid = body_id or re.sub(r'[^A-Za-z0-9_]', '_', clean_name).strip('_')[:31].upper()

        if clean_name in self.star_indices or bid in self.star_indices:
            print(f"Star {clean_name} already exists in registry.")
            return False

        if clean_name.lower() in ("sun", "sol"):
            print("Notice: 'Sun' is our local star at coordinate origin (0, 0, 0).")
            self.add_star_manual(
                clean_name, bid,
                mass_kg=1.989e30, radius_m=696340000.0,
                spectral_type=SpectralType.G, spectral_subtype=2,
                surface_temperature_k=5778.0
            )
            return True

        # Attempt Hipparcos query if source is Hipparcos or name looks like HIP
        src = CatalogSource.from_string(source) if isinstance(source, str) else source
        if src == CatalogSource.HIPPARCOS or clean_name.upper().startswith("HIP"):
            records = self.distance_resolver.hipparcos.query_object(clean_name)
            if records:
                rec = records[0]
                rec.name = clean_name
                rec.body_id = bid
                star_dict = rec.to_engine_dict()
                star_dict["distance_method"] = rec.distance.method.value
                star_dict["distance_source"] = rec.distance.source.value
                self.stars.append(star_dict)
                self.star_indices[clean_name] = len(self.stars) - 1
                self.star_indices[bid] = len(self.stars) - 1
                print(f"Added {clean_name} from Hipparcos with parallax {rec.distance.parallax_mas} mas ({rec.distance.distance_pc:.2f} pc).")
                return True

        # Resolve coordinates via SkyCoord or Simbad
        try:
            sc = SkyCoord.from_name(clean_name)
        except Exception:
            sim_res = self.simbad.query_object(clean_name)
            if sim_res is None or len(sim_res) == 0:
                print(f"Could not resolve celestial position for {clean_name}.")
                return False
            sc = SkyCoord(ra=float(sim_res['ra'][0]) * astrounit.deg, dec=float(sim_res['dec'][0]) * astrounit.deg, frame='icrs')

        dist_res = self.distance_resolver.resolve_precise_distance(
            coord=sc,
            preferred_source=src
        )

        if dist_res is None or not dist_res.is_valid:
            print(f"Could not determine precise distance for {clean_name}. Using Simbad fallback...")
            self.add_star_simbad(name=clean_name, body_id=bid, mass_kg=mass_kg, radius_m=radius_m, **kwargs)
            return True

        sc_3d = create_skycoord_3d(float(sc.ra.deg), float(sc.dec.deg), dist_res.distance_pc)
        cart_pos = skycoord_to_cartesian_meters(sc_3d)

        star: dict[str, Any] = {
            "name": clean_name,
            "body_id": bid,
            "position": cart_pos,
            "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            "right_ascension_rad": float(sc.ra.rad),
            "declination_rad": float(sc.dec.rad),
            "distance_pc": round(dist_res.distance_pc, 4),
            "mass_kg": mass_kg,
            "radius_m": radius_m,
            "distance_method": dist_res.method.value,
            "distance_source": dist_res.source.value,
        }
        if dist_res.distance_error_lower_pc is not None:
            star["distance_error_lower_pc"] = round(dist_res.distance_error_lower_pc, 4)
        if dist_res.distance_error_upper_pc is not None:
            star["distance_error_upper_pc"] = round(dist_res.distance_error_upper_pc, 4)

        for k, v in kwargs.items():
            star[k] = v.value if isinstance(v, Enum) else v

        self.stars.append(star)
        self.star_indices[clean_name] = len(self.stars) - 1
        self.star_indices[bid] = len(self.stars) - 1
        print(f"Added star {clean_name} using {dist_res.source.value} ({dist_res.distance_pc:.2f} pc via {dist_res.method.value})")
        return True

    def add_planet(self, name: str, body_id: str, jpl_id: str, center_id: str, host_star_name: str, **kwargs: Any) -> None:
        """Fetches orbital data from JPL Horizons and adds a planet."""
        orbit_idx: int
        position: dict[str, float]
        elements: Table
        orbit_idx, position, elements = self._fetch_orbit_jpl(jpl_id, center_id)
        
        planet: dict[str, Any] = {
            "name": name,
            "body_id": body_id,
            "host_star_index": self.star_indices[host_star_name],
            "orbit_index": orbit_idx,
            "position": position,
            "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            "semi_major_axis_au": safe_float(elements['a'][0]),
            "eccentricity": safe_float(elements['e'][0]),
            "inclination_rad": safe_float(elements['incl'][0]) * DEG_TO_RAD,
            "longitude_ascending_node_rad": safe_float(elements['Omega'][0]) * DEG_TO_RAD,
            "argument_periapsis_rad": safe_float(elements['w'][0]) * DEG_TO_RAD,
            "mean_anomaly_rad": safe_float(elements['M'][0]) * DEG_TO_RAD,
            "orbital_period_days": safe_float(elements['P'][0]),
        }

        # Auto-compute surface gravity and density if mass and radius are present
        mass: float | None = kwargs.get("mass_kg")
        radius: float | None = kwargs.get("radius_m")
        if mass and radius and radius > 0:
            if "surface_gravity_m_s2" not in kwargs:
                planet["surface_gravity_m_s2"] = (G_CONST * mass) / (radius ** 2)
            if "density_kg_m3" not in kwargs:
                volume: float = (4.0 / 3.0) * math.pi * (radius ** 3)
                planet["density_kg_m3"] = mass / volume

        for k, v in kwargs.items():
            planet[k] = v.value if isinstance(v, Enum) else v
        self.planets.append(planet)
        self.planet_indices[name] = len(self.planets) - 1
        self.planet_indices[body_id] = len(self.planets) - 1
        print(f"Added planet {name}")

    def add_moon(self, name: str, body_id: str, jpl_id: str, center_id: str, host_planet_name: str, **kwargs: Any) -> None:
        """Fetches orbital data from JPL Horizons and adds a moon."""
        orbit_idx: int
        position: dict[str, float]
        elements: Table
        orbit_idx, position, elements = self._fetch_orbit_jpl(jpl_id, center_id)
        
        moon: dict[str, Any] = {
            "name": name,
            "body_id": body_id,
            "host_planet_index": self.planet_indices[host_planet_name],
            "orbit_index": orbit_idx,
            "position": position,
            "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            "semi_major_axis_km": safe_float(elements['a'][0]) * (AU_TO_METERS / 1000.0),
            "eccentricity": safe_float(elements['e'][0]),
            "inclination_rad": safe_float(elements['incl'][0]) * DEG_TO_RAD,
            "longitude_ascending_node_rad": safe_float(elements['Omega'][0]) * DEG_TO_RAD,
            "argument_periapsis_rad": safe_float(elements['w'][0]) * DEG_TO_RAD,
            "mean_anomaly_rad": safe_float(elements['M'][0]) * DEG_TO_RAD,
            "orbital_period_days": safe_float(elements['P'][0]),
        }

        # Auto-compute surface gravity if mass and radius are present
        mass: float | None = kwargs.get("mass_kg")
        radius: float | None = kwargs.get("radius_m")
        if mass and radius and radius > 0:
            if "surface_gravity_m_s2" not in kwargs:
                moon["surface_gravity_m_s2"] = (G_CONST * mass) / (radius ** 2)

        for k, v in kwargs.items():
            moon[k] = v.value if isinstance(v, Enum) else v
        self.moons.append(moon)
        print(f"Added moon {name}")

    def add_solar_system(self, include_moons: bool = True, include_dwarf_planets: bool = True) -> None:
        """
        Adds all celestial bodies of the Solar System with accurate physical parameters:
        - The Sun (G-type main-sequence star with temperatures, luminosity, magnetic field)
        - All 8 Major Planets (Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune)
        - Major Moons for all planets:
          * Earth: Moon (Luna)
          * Mars: Phobos, Deimos
          * Jupiter: Io, Europa, Ganymede, Callisto
          * Saturn: Mimas, Enceladus, Tethys, Dione, Rhea, Titan, Iapetus
          * Uranus: Miranda, Ariel, Umbriel, Titania, Oberon
          * Neptune: Proteus, Triton
        - Dwarf Planet Pluto and its moon Charon (if include_dwarf_planets is True)
        """
        print("Importing Solar System data...")

        # ---------------------------------------------------------------------
        # 1. Central Star: The Sun
        # ---------------------------------------------------------------------
        if "Sun" not in self.star_indices and "SUN" not in self.star_indices:
            self.add_star_manual(
                name="Sun",
                body_id="SUN",
                mass_kg=1.98847e30,
                radius_m=696340000,
                spectral_type=SpectralType.G,
                spectral_subtype=2,
                surface_temperature_k=5772.0,
                core_temperature_k=15000000.0,
                luminosity_w=3.828e26,
                bolometric_luminosity_w=3.828e26,
                rotation_period_days=25.05,
                magnetic_field_gauss=2.0
            )

        # ---------------------------------------------------------------------
        # 2. Major Planets
        # ---------------------------------------------------------------------
        # Mercury
        self.add_planet(
            name="Mercury", body_id="MERCURY", jpl_id="199", center_id="@sun", host_star_name="Sun",
            planet_class=PlanetClass.TERRESTRIAL,
            radius_m=2439700, mass_kg=3.3011e23,
            surface_temperature_k=440.0,
            atmosphere_type=AtmosphereType.THIN,
            surface_pressure_pa=1e-9,
            has_rings=0,
            albedo=0.106,
            axial_tilt_rad=0.034 * DEG_TO_RAD,
            rotation_period_days=58.646
        )

        # Venus
        self.add_planet(
            name="Venus", body_id="VENUS", jpl_id="299", center_id="@sun", host_star_name="Sun",
            planet_class=PlanetClass.TERRESTRIAL,
            radius_m=6051800, mass_kg=4.8675e24,
            surface_temperature_k=737.0,
            atmosphere_type=AtmosphereType.DENSE,
            surface_pressure_pa=9.3e6,
            has_rings=0,
            albedo=0.77,
            axial_tilt_rad=177.36 * DEG_TO_RAD,
            rotation_period_days=-243.02
        )

        # Earth
        self.add_planet(
            name="Earth", body_id="EARTH", jpl_id="399", center_id="@sun", host_star_name="Sun",
            planet_class=PlanetClass.TERRESTRIAL,
            radius_m=6371000, mass_kg=5.97237e24,
            surface_temperature_k=288.0,
            atmosphere_type=AtmosphereType.STANDARD,
            surface_pressure_pa=101325.0,
            has_rings=0,
            albedo=0.306,
            axial_tilt_rad=23.44 * DEG_TO_RAD,
            rotation_period_days=0.99726968,
            magnetic_field_gauss=0.5
        )

        # Mars
        self.add_planet(
            name="Mars", body_id="MARS", jpl_id="499", center_id="@sun", host_star_name="Sun",
            planet_class=PlanetClass.TERRESTRIAL,
            radius_m=3389500, mass_kg=6.4171e23,
            surface_temperature_k=210.0,
            atmosphere_type=AtmosphereType.THIN,
            surface_pressure_pa=610.0,
            has_rings=0,
            albedo=0.17,
            axial_tilt_rad=25.19 * DEG_TO_RAD,
            rotation_period_days=1.025957
        )

        # Jupiter
        self.add_planet(
            name="Jupiter", body_id="JUPITER", jpl_id="599", center_id="@sun", host_star_name="Sun",
            planet_class=PlanetClass.GAS_GIANT,
            radius_m=69911000, mass_kg=1.8982e27,
            surface_temperature_k=165.0,
            atmosphere_type=AtmosphereType.THICK_ENVELOPE,
            has_rings=1,
            ring_inner_radius_m=92000000, ring_outer_radius_m=226000000,
            albedo=0.538,
            axial_tilt_rad=3.13 * DEG_TO_RAD,
            rotation_period_days=0.41354,
            magnetic_field_gauss=4.28
        )

        # Saturn
        self.add_planet(
            name="Saturn", body_id="SATURN", jpl_id="699", center_id="@sun", host_star_name="Sun",
            planet_class=PlanetClass.GAS_GIANT,
            radius_m=58232000, mass_kg=5.6834e26,
            surface_temperature_k=134.0,
            atmosphere_type=AtmosphereType.THICK_ENVELOPE,
            has_rings=1,
            ring_inner_radius_m=74500000, ring_outer_radius_m=140220000,
            albedo=0.499,
            axial_tilt_rad=26.73 * DEG_TO_RAD,
            rotation_period_days=0.444,
            magnetic_field_gauss=0.22
        )

        # Uranus
        self.add_planet(
            name="Uranus", body_id="URANUS", jpl_id="799", center_id="@sun", host_star_name="Sun",
            planet_class=PlanetClass.ICE_GIANT,
            radius_m=25362000, mass_kg=8.681e25,
            surface_temperature_k=76.0,
            atmosphere_type=AtmosphereType.THICK_ENVELOPE,
            has_rings=1,
            ring_inner_radius_m=38000000, ring_outer_radius_m=51149000,
            albedo=0.517,
            axial_tilt_rad=97.77 * DEG_TO_RAD,
            rotation_period_days=-0.71833,
            magnetic_field_gauss=0.23
        )

        # Neptune
        self.add_planet(
            name="Neptune", body_id="NEPTUNE", jpl_id="899", center_id="@sun", host_star_name="Sun",
            planet_class=PlanetClass.ICE_GIANT,
            radius_m=24622000, mass_kg=1.024e26,
            surface_temperature_k=72.0,
            atmosphere_type=AtmosphereType.THICK_ENVELOPE,
            has_rings=1,
            ring_inner_radius_m=41900000, ring_outer_radius_m=62933000,
            albedo=0.442,
            axial_tilt_rad=28.32 * DEG_TO_RAD,
            rotation_period_days=0.6713,
            magnetic_field_gauss=0.14
        )

        # Pluto (Dwarf Planet)
        if include_dwarf_planets:
            self.add_planet(
                name="Pluto", body_id="PLUTO", jpl_id="999", center_id="@sun", host_star_name="Sun",
                planet_class=PlanetClass.DWARF,
                radius_m=1188300, mass_kg=1.303e22,
                surface_temperature_k=44.0,
                atmosphere_type=AtmosphereType.THIN,
                surface_pressure_pa=1.0,
                has_rings=0,
                albedo=0.52,
                axial_tilt_rad=122.53 * DEG_TO_RAD,
                rotation_period_days=-6.387
            )

        # ---------------------------------------------------------------------
        # 3. Major Moons
        # ---------------------------------------------------------------------
        if include_moons:
            # --- Earth's Moon ---
            self.add_moon(
                name="Moon", body_id="LUNA", jpl_id="301", center_id="@399", host_planet_name="Earth",
                moon_class=MoonClass.ROCKY,
                radius_m=1737400, mass_kg=7.342e22,
                surface_temperature_k=250.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=27.321661,
                albedo=0.12
            )

            # --- Mars's Moons ---
            self.add_moon(
                name="Phobos", body_id="PHOBOS", jpl_id="401", center_id="@499", host_planet_name="Mars",
                moon_class=MoonClass.CAPTURED,
                radius_m=11262, mass_kg=1.0659e16,
                surface_temperature_k=233.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=0.3189,
                albedo=0.071
            )
            self.add_moon(
                name="Deimos", body_id="DEIMOS", jpl_id="402", center_id="@499", host_planet_name="Mars",
                moon_class=MoonClass.CAPTURED,
                radius_m=6255, mass_kg=1.4762e15,
                surface_temperature_k=233.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=1.263,
                albedo=0.068
            )

            # --- Jupiter's Galilean Moons ---
            self.add_moon(
                name="Io", body_id="IO", jpl_id="501", center_id="@599", host_planet_name="Jupiter",
                moon_class=MoonClass.VOLCANIC,
                radius_m=1821600, mass_kg=8.9319e22,
                surface_temperature_k=130.0,
                atmosphere_type=AtmosphereType.THIN,
                is_tidally_locked=1,
                rotation_period_days=1.769,
                albedo=0.63
            )
            self.add_moon(
                name="Europa", body_id="EUROPA", jpl_id="502", center_id="@599", host_planet_name="Jupiter",
                moon_class=MoonClass.ICY,
                radius_m=1560800, mass_kg=4.7998e22,
                surface_temperature_k=102.0,
                atmosphere_type=AtmosphereType.THIN,
                is_tidally_locked=1,
                rotation_period_days=3.551,
                albedo=0.67
            )
            self.add_moon(
                name="Ganymede", body_id="GANYMEDE", jpl_id="503", center_id="@599", host_planet_name="Jupiter",
                moon_class=MoonClass.ICY,
                radius_m=2634100, mass_kg=1.4819e23,
                surface_temperature_k=110.0,
                atmosphere_type=AtmosphereType.THIN,
                is_tidally_locked=1,
                rotation_period_days=7.154,
                albedo=0.43
            )
            self.add_moon(
                name="Callisto", body_id="CALLISTO", jpl_id="504", center_id="@599", host_planet_name="Jupiter",
                moon_class=MoonClass.ICY,
                radius_m=2410300, mass_kg=1.0759e23,
                surface_temperature_k=134.0,
                atmosphere_type=AtmosphereType.THIN,
                is_tidally_locked=1,
                rotation_period_days=16.689,
                albedo=0.22
            )

            # --- Saturn's Major Moons ---
            self.add_moon(
                name="Mimas", body_id="MIMAS", jpl_id="601", center_id="@699", host_planet_name="Saturn",
                moon_class=MoonClass.ICY,
                radius_m=198200, mass_kg=3.75e19,
                surface_temperature_k=64.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=0.942,
                albedo=0.96
            )
            self.add_moon(
                name="Enceladus", body_id="ENCELADUS", jpl_id="602", center_id="@699", host_planet_name="Saturn",
                moon_class=MoonClass.ICY,
                radius_m=252100, mass_kg=1.08e20,
                surface_temperature_k=75.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=1.370,
                albedo=0.99
            )
            self.add_moon(
                name="Tethys", body_id="TETHYS", jpl_id="603", center_id="@699", host_planet_name="Saturn",
                moon_class=MoonClass.ICY,
                radius_m=531100, mass_kg=6.17e20,
                surface_temperature_k=86.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=1.888,
                albedo=0.8
            )
            self.add_moon(
                name="Dione", body_id="DIONE", jpl_id="604", center_id="@699", host_planet_name="Saturn",
                moon_class=MoonClass.ICY,
                radius_m=561400, mass_kg=1.095e21,
                surface_temperature_k=87.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=2.737,
                albedo=0.6
            )
            self.add_moon(
                name="Rhea", body_id="RHEA", jpl_id="605", center_id="@699", host_planet_name="Saturn",
                moon_class=MoonClass.ICY,
                radius_m=763800, mass_kg=2.306e21,
                surface_temperature_k=76.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=4.518,
                albedo=0.95
            )
            self.add_moon(
                name="Titan", body_id="TITAN", jpl_id="606", center_id="@699", host_planet_name="Saturn",
                moon_class=MoonClass.ROCKY,
                radius_m=2574700, mass_kg=1.3452e23,
                surface_temperature_k=94.0,
                atmosphere_type=AtmosphereType.DENSE,
                surface_pressure_pa=146700.0,
                is_tidally_locked=1,
                rotation_period_days=15.945,
                albedo=0.22
            )
            self.add_moon(
                name="Iapetus", body_id="IAPETUS", jpl_id="608", center_id="@699", host_planet_name="Saturn",
                moon_class=MoonClass.ICY,
                radius_m=734500, mass_kg=1.805e21,
                surface_temperature_k=110.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=79.321,
                albedo=0.2
            )

            # --- Uranus's Major Moons ---
            self.add_moon(
                name="Miranda", body_id="MIRANDA", jpl_id="705", center_id="@799", host_planet_name="Uranus",
                moon_class=MoonClass.ICY,
                radius_m=235800, mass_kg=6.59e19,
                surface_temperature_k=60.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=1.413,
                albedo=0.32
            )
            self.add_moon(
                name="Ariel", body_id="ARIEL", jpl_id="701", center_id="@799", host_planet_name="Uranus",
                moon_class=MoonClass.ICY,
                radius_m=578900, mass_kg=1.25e21,
                surface_temperature_k=60.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=2.520,
                albedo=0.39
            )
            self.add_moon(
                name="Umbriel", body_id="UMBRIEL", jpl_id="702", center_id="@799", host_planet_name="Uranus",
                moon_class=MoonClass.ICY,
                radius_m=584700, mass_kg=1.27e21,
                surface_temperature_k=75.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=4.144,
                albedo=0.21
            )
            self.add_moon(
                name="Titania", body_id="TITANIA", jpl_id="703", center_id="@799", host_planet_name="Uranus",
                moon_class=MoonClass.ICY,
                radius_m=788400, mass_kg=3.40e21,
                surface_temperature_k=70.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=8.706,
                albedo=0.27
            )
            self.add_moon(
                name="Oberon", body_id="OBERON", jpl_id="704", center_id="@799", host_planet_name="Uranus",
                moon_class=MoonClass.ICY,
                radius_m=761400, mass_kg=3.01e21,
                surface_temperature_k=75.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=13.463,
                albedo=0.23
            )

            # --- Neptune's Major Moons ---
            self.add_moon(
                name="Proteus", body_id="PROTEUS", jpl_id="808", center_id="@899", host_planet_name="Neptune",
                moon_class=MoonClass.ICY,
                radius_m=210000, mass_kg=4.4e19,
                surface_temperature_k=51.0,
                atmosphere_type=AtmosphereType.NONE,
                is_tidally_locked=1,
                rotation_period_days=1.122,
                albedo=0.096
            )
            self.add_moon(
                name="Triton", body_id="TRITON", jpl_id="801", center_id="@899", host_planet_name="Neptune",
                moon_class=MoonClass.ICY,
                radius_m=1353400, mass_kg=2.14e22,
                surface_temperature_k=38.0,
                atmosphere_type=AtmosphereType.THIN,
                surface_pressure_pa=1.4,
                is_tidally_locked=1,
                rotation_period_days=-5.877,
                albedo=0.76
            )

            # --- Pluto's Moon Charon ---
            if include_dwarf_planets and ("Pluto" in self.planet_indices or "PLUTO" in self.planet_indices):
                self.add_moon(
                    name="Charon", body_id="CHARON", jpl_id="901", center_id="@999", host_planet_name="Pluto",
                    moon_class=MoonClass.ICY,
                    radius_m=606000, mass_kg=1.586e21,
                    surface_temperature_k=53.0,
                    atmosphere_type=AtmosphereType.NONE,
                    is_tidally_locked=1,
                    rotation_period_days=-6.387,
                    albedo=0.38
                )

        print("Completed importing Solar System data.")

    def save(self, filepath: str) -> None:
        """Dumps all collected data to the JSON schema."""
        output_data: dict[str, Any] = {
            "$schema": "https://raw.githubusercontent.com/SkinnyDevi/celestial-engine/refs/heads/master/src/tests/data/schema.json",
            "sim_date": {
                "year": self.sim_time.datetime.year,
                "month": self.sim_time.datetime.month,
                "day": self.sim_time.datetime.day,
                "hour": self.sim_time.datetime.hour,
                "minute": self.sim_time.datetime.minute,
                "second": self.sim_time.datetime.second
            },
            "orbits": self.orbits,
            "stars": self.stars,
            "planets": self.planets,
            "moons": self.moons
        }
        f: TextIO
        with open(filepath, 'w') as f:
            json.dump(output_data, f, indent=4, default=lambda o: o.value if isinstance(o, Enum) else str(o))
        print(f"Successfully saved to {filepath}")