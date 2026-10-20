from astropy.coordinates import SkyCoord
from enum import Enum
import time
import re
import json
import math
from typing import Any, TextIO

import numpy as np
import astropy.units as astrounits
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
    StarRecord,
    PreciseDistanceResolver,
    create_skycoord_3d,
    skycoord_to_cartesian_meters,
    distance_from_parallax,
    classify_spectral_type,
)
from core.planets import (
    PlanetRecord,
    OrbitRecord,
    PlanetResolver,
    NasaExoplanetProvider,
    SolarSystemPlanetProvider,
    RoguePlanetProvider,
)
from core.moons import (
    MoonRecord,
    MoonResolver,
    SolarSystemMoonProvider,
    ExomoonProvider,
    JPLHorizonsMoonProvider,
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
    moon_indices: dict[str, int]
    simbad: SimbadClass
    distance_resolver: PreciseDistanceResolver
    planet_resolver: PlanetResolver
    moon_resolver: MoonResolver

    def __init__(
        self,
        sim_time: Time,
        max_apparent_magnitude: float | None = None,
        keep_unmeasured: bool = True,
        distance_resolver: PreciseDistanceResolver | None = None,
        planet_resolver: PlanetResolver | None = None,
        moon_resolver: MoonResolver | None = None,
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
        self.moon_indices: dict[str, int] = {}
        
        # Configure Simbad
        self.simbad: SimbadClass = Simbad()
        self.simbad.ROW_LIMIT = -1
        self._init_simbad_fields()

        # Configure Precise Distance Resolver
        self.distance_resolver: PreciseDistanceResolver = (
            distance_resolver if distance_resolver is not None else PreciseDistanceResolver(prefer_photogeometric=prefer_photogeometric)
        )

        # Configure Planet Resolver
        self.planet_resolver: PlanetResolver = (
            planet_resolver if planet_resolver is not None else PlanetResolver()
        )

        # Configure Moon Resolver
        self.moon_resolver: MoonResolver = (
            moon_resolver if moon_resolver is not None else MoonResolver()
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
        include_exoplanets: bool = False,
        include_moons: bool = False,
    ) -> None:
        """
        Fetches a batch of stars/objects around a specific celestial region (cone in the sky) and adds them.
        Ideal for extra-solar targets such as galaxies (e.g. 'M31'), nebulae, or clusters.
        `max_apparent_magnitude`: Apparent magnitude cutoff (drops objects fainter than this).
        `keep_unmeasured`: Whether to keep objects without catalog magnitude measurement.
        `use_precise_distances`: Enrich stars with precise distances from Gaia DR3, Bailer-Jones, StarHorse, or Hipparcos.
        `include_exoplanets`: Automatically discover and import confirmed exoplanets orbiting stars in the region.
        `include_moons`: Automatically discover and import natural satellites/moons in the region.
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
            added = self.add_nearby_stars(
                max_distance_ly=radius_degrees, limit=limit,
                mass_kg_default=mass_kg_default, radius_m_default=radius_m_default,
                max_apparent_magnitude=cutoff, keep_unmeasured=keep_unm
            )
            if include_exoplanets:
                self.add_exoplanets_in_region(center_name, radius_degrees=radius_degrees, auto_add_host_stars=True)
            if include_moons:
                self.add_moons_in_region(center_name, radius_degrees=radius_degrees)
            return added

        limit_desc: str = f"up to {limit}" if (limit is not None and limit > 0) else "all"
        mag_desc: str = f" with mag <= {cutoff}" if cutoff is not None else ""
        print(f"Fetching {limit_desc} objects around {center_name} (radius {radius_degrees} deg){mag_desc}...")
        
        prev_limit: int = self.simbad.ROW_LIMIT
        self.simbad.ROW_LIMIT = limit if (limit is not None and limit > 0) else -1
        result: Table | None
        try:
            result = self.simbad.query_region(center_name, radius=radius_degrees * astrounits.deg)
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

        if include_exoplanets:
            self.add_exoplanets_in_region(center_name, radius_degrees=radius_degrees, auto_add_host_stars=True)
        if include_moons:
            self.add_moons_in_region(center_name, radius_degrees=radius_degrees)

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
        include_exoplanets: bool = False,
        include_moons: bool = False,
    ) -> int:
        """
        Fetches stars around a center region using precision distance catalogs:
        - Gaia DR3 (geometric parallax, all-sky true 3D stellar positions)
        - Bailer-Jones (Bayesian geometric & photogeometric, prevents line-of-sight stretching/errors)
        - StarHorse (multi-band optical/IR + stellar models for dust/dense fields)
        - Hipparcos (trigonometric parallax for bright foreground stars m < 6)
        - include_exoplanets: Automatically discover and import confirmed exoplanets orbiting stars in the region.
        - include_moons: Automatically discover and import natural satellites/moons in the region.
        """
        cutoff: float | None = self.max_apparent_magnitude if max_apparent_magnitude is None else max_apparent_magnitude
        keep_unm: bool = self.keep_unmeasured if keep_unmeasured is None else keep_unmeasured

        if center_name.strip().lower() in ("sun", "sol"):
            print(f"Notice: 'Sun' is our local star (origin of coordinates) and does not exist as an extra-solar target in sky catalogs.")
            print(f"Redirecting query to fetch nearby stars by 3D distance ({radius_degrees} ly) from the Sun...")
            added = self.add_nearby_stars(
                max_distance_ly=radius_degrees,
                limit=limit,
                mass_kg_default=mass_kg_default,
                radius_m_default=radius_m_default,
                max_apparent_magnitude=cutoff,
                keep_unmeasured=keep_unm,
                use_precise_distances=False,
                precise_source=source,
            )
            if include_exoplanets:
                self.add_exoplanets_in_region(center_name, radius_degrees=radius_degrees, auto_add_host_stars=True)
            if include_moons:
                self.add_moons_in_region(center_name, radius_degrees=radius_degrees)
            return added

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

        if include_exoplanets:
            self.add_exoplanets_in_region(center_name, radius_degrees=radius_degrees, auto_add_host_stars=True)
        if include_moons:
            self.add_moons_in_region(center_name, radius_degrees=radius_degrees)

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
            sc = SkyCoord(ra=float(sim_res['ra'][0]) * astrounits.deg, dec=float(sim_res['dec'][0]) * astrounits.deg, frame='icrs')

        dist_res = self.distance_resolver.resolve_precise_distance(
            coord=sc,
            preferred_source=src
        )

        if dist_res is None or not dist_res.is_valid:
            print(f"Could not determine precise distance for {clean_name}. Using Simbad fallback...")
            self.add_star_simbad(name=clean_name, body_id=bid, mass_kg=mass_kg, radius_m=radius_m, max_apparent_magnitude=max_apparent_magnitude, **kwargs)
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

    def add_planet_record(self, planet: PlanetRecord, orbit: OrbitRecord | None = None) -> None:
        """
        Adds a decoupled PlanetRecord (and optional OrbitRecord) to the simulation,
        resolving host star indices and orbit indices.
        """
        host_idx = -1
        if planet.planet_class != PlanetClass.ROGUE:
            if planet.host_star_name and planet.host_star_name in self.star_indices:
                host_idx = self.star_indices[planet.host_star_name]
            elif planet.host_star_id and planet.host_star_id in self.star_indices:
                host_idx = self.star_indices[planet.host_star_id]
            elif planet.host_star_name:
                for s_name, s_idx in self.star_indices.items():
                    if s_name.upper() in ("SUN", "SOL"):
                        continue
                    if planet.host_star_name.upper() in s_name.upper() or s_name.upper() in planet.host_star_name.upper():
                        host_idx = s_idx
                        break

            # If still not found and host star name is known, auto-create host star so the planet
            # never unintentionally falls back to the heliocentric origin (Sun) at (0, 0, 0)
            if host_idx < 0 and planet.host_star_name:
                from core.catalogs import sanitize_name_and_id
                host_clean, host_bid = sanitize_name_and_id(planet.host_star_name)
                if host_clean in self.star_indices:
                    host_idx = self.star_indices[host_clean]
                elif host_bid in self.star_indices:
                    host_idx = self.star_indices[host_bid]
                else:
                    effective_dist_pc = planet.distance_pc if planet.distance_pc > 0.0 else 30.0
                    ra_deg = planet.right_ascension_rad * (180.0 / math.pi)
                    dec_deg = planet.declination_rad * (180.0 / math.pi)

                    sc = create_skycoord_3d(ra_deg, dec_deg, effective_dist_pc)
                    cart_pos = skycoord_to_cartesian_meters(sc)

                    st_mass_kg = planet.extra_metadata.get("st_mass_kg", SOLAR_MASS_KG)
                    st_rad_m = planet.extra_metadata.get("st_radius_m", SOLAR_RADIUS_M)
                    st_teff_k = planet.extra_metadata.get("st_teff_k", 5778.0)
                    st_spectype = planet.extra_metadata.get("st_spectype")
                    s_type, s_sub = self.parse_spectral_type(st_spectype)
                    if s_type is None:
                        s_type = SpectralType.G
                        s_sub = 2

                    host_dict = {
                        "name": host_clean,
                        "body_id": host_bid,
                        "spectral_type": s_type.value,
                        "spectral_subtype": s_sub,
                        "position": cart_pos,
                        "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                        "right_ascension_rad": planet.right_ascension_rad,
                        "declination_rad": planet.declination_rad,
                        "distance_pc": effective_dist_pc,
                        "mass_kg": st_mass_kg,
                        "radius_m": st_rad_m,
                        "surface_temperature_k": st_teff_k,
                    }
                    self.stars.append(host_dict)
                    host_idx = len(self.stars) - 1
                    self.star_indices[host_clean] = host_idx
                    self.star_indices[host_bid] = host_idx
                    if planet.host_star_name != host_clean:
                        self.star_indices[planet.host_star_name] = host_idx

        planet.host_star_index = host_idx

        # Orbit
        orb = orbit if orbit is not None else planet.orbit
        if orb is not None:
            self.orbits.append(orb.to_engine_dict())
            planet.orbit_index = len(self.orbits) - 1
        else:
            planet.orbit_index = -1

        p_dict = planet.to_engine_dict()
        self.planets.append(p_dict)
        idx = len(self.planets) - 1
        self.planet_indices[planet.name] = idx
        self.planet_indices[planet.body_id] = idx
        p_class_name = planet.planet_class.name if hasattr(planet.planet_class, 'name') else str(planet.planet_class)
        print(f"Added planet {planet.name} ({p_class_name})")

    def add_exoplanets_for_star(
        self,
        host_star_name: str,
        add_host_if_missing: bool = True,
        include_moons: bool = False
    ) -> list[PlanetRecord]:
        """
        Queries and imports all confirmed exoplanets orbiting a given host star.
        If host star is missing and add_host_if_missing is True, attempts to resolve it first.
        If include_moons is True, also imports any natural satellites/exomoons in the system.
        """
        clean_host = host_star_name.strip()
        has_host = clean_host in self.star_indices or clean_host.upper() in self.star_indices
        if not has_host and add_host_if_missing:
            added = self.add_star_precise(clean_host, max_apparent_magnitude=float("inf"))
            if not added:
                self.add_star_simbad(
                    clean_host,
                    body_id=clean_host,
                    mass_kg=1.989e30,
                    radius_m=696340000.0,
                    max_apparent_magnitude=float("inf")
                )

        planets = self.planet_resolver.resolve_planets_for_star(clean_host)
        if not planets:
            print(f"No exoplanets found for host star '{clean_host}'.")
            return []

        added_planets: list[PlanetRecord] = []
        for p in planets:
            if p.name in self.planet_indices or p.body_id in self.planet_indices:
                continue
            self.add_planet_record(p)
            added_planets.append(p)

        print(f"Successfully imported {len(added_planets)} exoplanet(s) for host '{clean_host}'.")

        if include_moons:
            self.add_moons_for_star(clean_host)

        return added_planets

    def add_exoplanets_in_region(
        self,
        center: str | SkyCoord,
        radius_degrees: float,
        auto_add_host_stars: bool = True
    ) -> list[PlanetRecord]:
        """
        Discovers and imports exoplanets within a sky cone around center.
        Automatically links them to known or newly created host stars.
        """
        if isinstance(center, str) and center.strip().lower() in ("sun", "sol"):
            max_dist_pc = (radius_degrees / 3.26156) if radius_degrees > 0 else 30.0
            print(f"Querying confirmed exoplanets within {max_dist_pc:.1f} pc ({radius_degrees:.1f} ly) of the Sun...")
            planets = self.planet_resolver.resolve_exoplanets_by_distance(max_dist_pc)
        else:
            if isinstance(center, str):
                from core.catalogs import resolve_center_coord
                center_coord = resolve_center_coord(center)
            else:
                center_coord = center

            planets = self.planet_resolver.resolve_planets_in_region(
                center_coord=center_coord,
                radius_deg=radius_degrees,
                include_exoplanets=True,
                include_rogue=False
            )

        added_planets: list[PlanetRecord] = []
        for p in planets:
            if p.name in self.planet_indices or p.body_id in self.planet_indices:
                continue

            # Ensure host star is added
            if p.host_star_name and p.host_star_name not in self.star_indices and auto_add_host_stars:
                from core.catalogs import sanitize_name_and_id
                host_clean, host_bid = sanitize_name_and_id(p.host_star_name)
                if host_clean not in self.star_indices and host_bid not in self.star_indices:
                    # Calculate true 3D interstellar position from RA, Dec, and Distance
                    effective_dist_pc = p.distance_pc if p.distance_pc > 0.0 else 30.0
                    ra_deg = p.right_ascension_rad * (180.0 / math.pi)
                    dec_deg = p.declination_rad * (180.0 / math.pi)

                    sc = create_skycoord_3d(ra_deg, dec_deg, effective_dist_pc)
                    cart_pos = skycoord_to_cartesian_meters(sc)

                    st_mass_kg = p.extra_metadata.get("st_mass_kg", SOLAR_MASS_KG)
                    st_rad_m = p.extra_metadata.get("st_radius_m", SOLAR_RADIUS_M)
                    st_teff_k = p.extra_metadata.get("st_teff_k", 5778.0)
                    st_spectype = p.extra_metadata.get("st_spectype")
                    s_type, s_sub = self.parse_spectral_type(st_spectype)
                    if s_type is None:
                        s_type = SpectralType.G
                        s_sub = 2

                    host_dict = {
                        "name": host_clean,
                        "body_id": host_bid,
                        "spectral_type": s_type.value,
                        "spectral_subtype": s_sub,
                        "position": cart_pos,
                        "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                        "right_ascension_rad": p.right_ascension_rad,
                        "declination_rad": p.declination_rad,
                        "distance_pc": effective_dist_pc,
                        "mass_kg": st_mass_kg,
                        "radius_m": st_rad_m,
                        "surface_temperature_k": st_teff_k,
                    }
                    self.stars.append(host_dict)
                    self.star_indices[host_clean] = len(self.stars) - 1
                    self.star_indices[host_bid] = len(self.stars) - 1

            self.add_planet_record(p)
            added_planets.append(p)

        print(f"Imported {len(added_planets)} exoplanet(s) in region around target.")
        return added_planets

    def add_rogue_planets(
        self,
        center: str | SkyCoord | None = None,
        radius_degrees: float | None = None
    ) -> list[PlanetRecord]:
        """Imports rogue / free-floating interstellar planets."""
        center_coord = None
        is_sun = False
        if center is not None:
            if isinstance(center, str):
                if center.strip().lower() in ("sun", "sol"):
                    is_sun = True
                    center_coord = None
                else:
                    from core.catalogs import resolve_center_coord
                    center_coord = resolve_center_coord(center)
            else:
                center_coord = center

        rogues = self.planet_resolver.resolve_rogue_planets(
            center_coord=center_coord,
            radius_deg=radius_degrees
        )

        if is_sun and radius_degrees is not None and radius_degrees > 10.0:
            max_dist_pc = radius_degrees / 3.26156
            rogues = [r for r in rogues if r.distance_pc <= max_dist_pc]

        added: list[PlanetRecord] = []
        for r in rogues:
            if r.name in self.planet_indices or r.body_id in self.planet_indices:
                continue
            self.add_planet_record(r)
            added.append(r)

        print(f"Imported {len(added)} rogue planet(s).")
        return added

    def add_moon_record(self, moon: MoonRecord, orbit: OrbitRecord | None = None) -> None:
        """
        Adds a decoupled MoonRecord (and optional OrbitRecord) to the simulation,
        automatically resolving its host_planet_index and orbit_index.
        """
        host_idx = -1
        if moon.host_planet_name and moon.host_planet_name in self.planet_indices:
            host_idx = self.planet_indices[moon.host_planet_name]
        elif moon.host_planet_id and moon.host_planet_id in self.planet_indices:
            host_idx = self.planet_indices[moon.host_planet_id]
        elif moon.host_planet_name:
            for p_name, idx in self.planet_indices.items():
                if moon.host_planet_name.upper() == p_name.upper():
                    host_idx = idx
                    break

        # If host planet is not loaded yet, attempt to load it automatically from planet resolver
        if host_idx < 0 and moon.host_planet_name:
            host_planet = self.planet_resolver.get_known_planet(moon.host_planet_name)
            if host_planet is not None:
                self.add_planet_record(host_planet)
                host_idx = self.planet_indices.get(host_planet.name, -1)

        moon.host_planet_index = host_idx

        # Orbit
        orb = orbit if orbit is not None else moon.orbit
        if orb is not None:
            self.orbits.append(orb.to_engine_dict())
            moon.orbit_index = len(self.orbits) - 1
        else:
            moon.orbit_index = -1

        m_dict = moon.to_engine_dict()
        self.moons.append(m_dict)
        idx = len(self.moons) - 1
        self.moon_indices[moon.name] = idx
        self.moon_indices[moon.body_id] = idx
        m_class_name = moon.moon_class.name if hasattr(moon.moon_class, 'name') else str(moon.moon_class)
        print(f"Added moon {moon.name} ({m_class_name}) -> Host: {moon.host_planet_name} (index {host_idx})")

    def add_moons_for_planet(self, planet_name: str, **kwargs: Any) -> list[MoonRecord]:
        """
        Resolves and imports all natural satellites for a specified host planet.
        Gracefully handles the case where the Sun is passed as target:
        The Sun is a star, not a planet; natural satellites orbit planets. Redirects to add Solar System moons.
        """
        clean_name = planet_name.strip()
        if clean_name.upper() in ("SUN", "SOL", "THE SUN"):
            print("Notice: 'Sun' is a central star, not a planet. Natural satellites orbit planets. Importing Solar System moons...")
            return self.add_moons_for_star("Sun", **kwargs)

        moons = self.moon_resolver.resolve_moons_for_planet(clean_name, **kwargs)
        added: list[MoonRecord] = []
        for m in moons:
            if m.name in self.moon_indices or m.body_id in self.moon_indices:
                continue
            self.add_moon_record(m)
            added.append(m)

        print(f"Imported {len(added)} moon(s) for planet '{clean_name}'.")
        return added

    def add_moons_for_star(self, star_name: str, **kwargs: Any) -> list[MoonRecord]:
        """
        Resolves and imports all natural satellites in the planetary system of a specified star.
        For 'Sun' / 'Sol', imports all Solar System moons.
        """
        clean_name = star_name.strip()
        moons = self.moon_resolver.resolve_moons_for_star(clean_name, **kwargs)
        added: list[MoonRecord] = []
        for m in moons:
            if m.name in self.moon_indices or m.body_id in self.moon_indices:
                continue
            self.add_moon_record(m)
            added.append(m)

        print(f"Imported {len(added)} moon(s) for star/system '{clean_name}'.")
        return added

    def add_moons_in_region(
        self,
        center: str | SkyCoord,
        radius_degrees: float,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """
        Discovers and imports moons within a sky cone around center.
        Takes into account exceptions when querying the Sun as target:
        Avoids querying sky catalogs for the Sun and returns Solar System moons.
        """
        if isinstance(center, str) and center.strip().upper() in ("SUN", "SOL", "THE SUN"):
            print("Notice: Target is the Sun (coordinate origin). Importing Solar System natural satellites...")
            return self.add_moons_for_star("Sun", **kwargs)

        moons = self.moon_resolver.resolve_moons_in_region(center, radius_degrees, **kwargs)
        added: list[MoonRecord] = []
        for m in moons:
            if m.name in self.moon_indices or m.body_id in self.moon_indices:
                continue
            self.add_moon_record(m)
            added.append(m)

        print(f"Imported {len(added)} moon(s) in region around target.")
        return added

    def add_moon(self, name: str, body_id: str, jpl_id: str, center_id: str, host_planet_name: str, **kwargs: Any) -> None:
        """Fetches orbital data from JPL Horizons or precision catalog and adds a moon."""
        known = self.moon_resolver.get_known_moon(name)
        if known is not None:
            for k, v in kwargs.items():
                if hasattr(known, k):
                    setattr(known, k, v)
            self.add_moon_record(known)
            return

        try:
            orbit_idx, position, elements = self._fetch_orbit_jpl(jpl_id, center_id)
            moon: dict[str, Any] = {
                "name": name,
                "body_id": body_id,
                "host_planet_index": self.planet_indices.get(host_planet_name, -1),
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

            mass: float | None = kwargs.get("mass_kg")
            radius: float | None = kwargs.get("radius_m")
            if mass and radius and radius > 0:
                if "surface_gravity_m_s2" not in kwargs:
                    moon["surface_gravity_m_s2"] = (G_CONST * mass) / (radius ** 2)

            for k, v in kwargs.items():
                moon[k] = v.value if isinstance(v, Enum) else v
            self.moons.append(moon)
            self.moon_indices[name] = len(self.moons) - 1
            self.moon_indices[body_id] = len(self.moons) - 1
            print(f"Added moon {name}")
        except Exception as e:
            print(f"Failed to fetch orbit from JPL for {name} ({e})")

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
            self.add_moons_for_star("Sun", include_dwarf_planet_moons=include_dwarf_planets)

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