"""
NASA Exoplanet Archive Provider
Integrates NASA Exoplanet Archive Composite Parameters table (pscomppars) via Astroquery.
Fetches real exoplanetary systems with complete physical and orbital characterization.
"""

from typing import Any
import re
import math
import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as astrounits

from core.constants import (
    AU_TO_METERS,
    DEG_TO_RAD,
    EARTH_MASS_KG,
    EARTH_RADIUS_M,
    JUPITER_MASS_KG,
    JUPITER_RADIUS_M,
    SOLAR_MASS_KG,
    SOLAR_RADIUS_M,
)
from core.math import safe_float
from core.space import PlanetClass, AtmosphereType
from core.planets.coords import (
    estimate_period_from_semimajor_axis,
    estimate_semimajor_axis_from_period,
    keplerian_to_cartesian,
)
from core.planets.models import (
    OrbitRecord,
    PlanetRecord,
    classify_atmosphere_type,
    classify_planet_type,
    estimate_albedo,
    estimate_density,
    estimate_equilibrium_temperature,
    estimate_mass_from_radius,
    estimate_radius_from_mass,
    estimate_surface_gravity,
    sanitize_planet_id,
)
from core.planets.providers.base import BasePlanetProvider

class NasaExoplanetProvider(BasePlanetProvider):
    """
    Decoupled NASA Exoplanet Archive provider utilizing astroquery.ipac.nexsci.nasa_exoplanet_archive.
    """

    def __init__(self, table_name: str = "pscomppars") -> None:
        self.table_name = table_name
        self._cache_host: dict[str, list[PlanetRecord]] = {}
        self._cache_region: dict[str, list[PlanetRecord]] = {}

    @property
    def name(self) -> str:
        return "nasa_exoplanet_archive"

    def query_by_host_star(self, host_name: str, host_id: str | None = None, **kwargs: Any) -> list[PlanetRecord]:
        """Queries all confirmed exoplanets orbiting the specified host star."""
        clean_host = host_name.strip()
        cache_key = clean_host.upper()
        if cache_key in self._cache_host:
            return self._cache_host[cache_key]

        try:
            from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive
        except ImportError:
            print("Warning: astroquery not available for NASA Exoplanet Archive.")
            return []

        # Try exact hostname match, or planet prefix match
        safe_name = clean_host.replace("'", "''")
        where_clause = f"hostname='{safe_name}' or hostname='{safe_name.replace('-', ' ')}' or hostname='{safe_name.replace(' ', '-')}' or pl_name like '{safe_name} %'"

        try:
            table = NasaExoplanetArchive.query_criteria(
                table=self.table_name,
                where=where_clause
            )
            if table is None or len(table) == 0:
                self._cache_host[cache_key] = []
                return []

            planets = self._table_to_records(table, default_host_name=clean_host, default_host_id=host_id)
            self._cache_host[cache_key] = planets
            return planets

        except Exception as e:
            print(f"Warning: NASA Exoplanet Archive query failed for host '{host_name}': {e}")
            return []

    def query_by_region(self, center_coord: SkyCoord, radius_deg: float, **kwargs: Any) -> list[PlanetRecord]:
        """Queries exoplanets within a cone of radius_deg around center_coord."""
        cache_key = f"{center_coord.ra.deg:.4f}_{center_coord.dec.deg:.4f}_{radius_deg:.2f}"
        if cache_key in self._cache_region:
            return self._cache_region[cache_key]

        try:
            from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive
        except ImportError:
            print("Warning: astroquery not available for NASA Exoplanet Archive.")
            return []

        try:
            table = NasaExoplanetArchive.query_region(
                table=self.table_name,
                coordinates=center_coord,
                radius=radius_deg * astrounits.deg
            )
            if table is None or len(table) == 0:
                self._cache_region[cache_key] = []
                return []

            planets = self._table_to_records(table)
            self._cache_region[cache_key] = planets
            return planets

        except Exception as e:
            print(f"Warning: NASA Exoplanet Archive region query failed: {e}")
            return []

    def query_by_distance(self, max_distance_pc: float, **kwargs: Any) -> list[PlanetRecord]:
        """Queries exoplanets within max_distance_pc of the Solar System (Sun)."""
        cache_key = f"DIST_{max_distance_pc:.2f}"
        if cache_key in self._cache_region:
            return self._cache_region[cache_key]

        try:
            from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive
        except ImportError:
            print("Warning: astroquery not available for NASA Exoplanet Archive.")
            return []

        try:
            table = NasaExoplanetArchive.query_criteria(
                table=self.table_name,
                where=f"sy_dist <= {max_distance_pc:.2f}"
            )
            if table is None or len(table) == 0:
                self._cache_region[cache_key] = []
                return []

            planets = self._table_to_records(table)
            self._cache_region[cache_key] = planets
            return planets

        except Exception as e:
            print(f"Warning: NASA Exoplanet Archive distance query failed: {e}")
            return []

    def get_known_planet(self, planet_name: str, **kwargs: Any) -> PlanetRecord | None:
        """Retrieves a single exoplanet by designation."""
        try:
            from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive
            safe_name = planet_name.strip().replace("'", "''")
            table = NasaExoplanetArchive.query_criteria(
                table=self.table_name,
                where=f"pl_name='{safe_name}'"
            )
            if table is not None and len(table) > 0:
                records = self._table_to_records(table)
                return records[0] if records else None
        except Exception as e:
            print(f"Warning: Failed to fetch planet '{planet_name}': {e}")
        return None

    def _table_to_records(
        self,
        table: Any,
        default_host_name: str | None = None,
        default_host_id: str | None = None
    ) -> list[PlanetRecord]:
        """Converts Astropy Table rows from pscomppars to PlanetRecord instances."""
        records: list[PlanetRecord] = []
        seen_names: set[str] = set()

        for row in table:
            pl_name_raw = row['pl_name']
            if isinstance(pl_name_raw, bytes):
                pl_name_raw = pl_name_raw.decode('utf-8')
            pl_name_raw = str(pl_name_raw).strip()

            if pl_name_raw in seen_names:
                continue
            seen_names.add(pl_name_raw)

            name, body_id = sanitize_planet_id(pl_name_raw)

            # Host star
            host_name = default_host_name
            if 'hostname' in table.colnames and not np.ma.is_masked(row['hostname']):
                h = row['hostname']
                host_name = str(h.decode('utf-8') if isinstance(h, bytes) else h).strip()
            elif default_host_name is None:
                # Derive from planet name (e.g. 'TRAPPIST-1 b' -> 'TRAPPIST-1')
                host_name = re.sub(r'\s+[a-z]$', '', name, flags=re.IGNORECASE).strip()

            host_id = default_host_id
            if host_id is None and host_name:
                _, host_id = sanitize_planet_id(host_name, fallback_prefix="STAR")

            # Orbital parameters
            # Semi-major axis (AU -> m)
            a_au = safe_float(row['pl_orbsmax']) if 'pl_orbsmax' in table.colnames else 0.0
            p_days = safe_float(row['pl_orbper']) if 'pl_orbper' in table.colnames else 0.0

            if a_au <= 0.0 and p_days > 0.0:
                a_m = estimate_semimajor_axis_from_period(p_days)
                a_au = a_m / AU_TO_METERS
            elif a_au > 0.0 and p_days <= 0.0:
                a_m = a_au * AU_TO_METERS
                p_days = estimate_period_from_semimajor_axis(a_m)
            elif a_au <= 0.0 and p_days <= 0.0:
                a_au = 1.0
                a_m = AU_TO_METERS
                p_days = 365.25
            else:
                a_m = a_au * AU_TO_METERS

            ecc = safe_float(row['pl_orbeccen']) if 'pl_orbeccen' in table.colnames else 0.0
            inc_deg = safe_float(row['pl_orbincl']) if 'pl_orbincl' in table.colnames else 0.0
            inc_rad = inc_deg * DEG_TO_RAD
            w_deg = safe_float(row['pl_orblper']) if 'pl_orblper' in table.colnames else 0.0
            w_rad = w_deg * DEG_TO_RAD
            omega_rad = 0.0  # Longitude of ascending node rarely constrained for exoplanets

            # Mean anomaly at epoch
            m_rad = 0.0
            if 'pl_tranmid' in table.colnames:
                # Use transit midpoint if present
                tranmid = safe_float(row['pl_tranmid'], default=0.0)
                if tranmid > 0 and p_days > 0:
                    phase = (tranmid % p_days) / p_days
                    m_rad = (phase * 2.0 * math.pi) % (2.0 * math.pi)

            # Calculate Cartesian relative position vector at this epoch
            pos, _, nu = keplerian_to_cartesian(
                semimajor_axis_m=a_m,
                eccentricity=ecc,
                inclination_rad=inc_rad,
                longitude_ascending_node_rad=omega_rad,
                argument_periapsis_rad=w_rad,
                mean_anomaly_rad=m_rad
            )

            # Build OrbitRecord
            orbit_rec = OrbitRecord(
                semimajor_axis=a_m,
                eccentricity=ecc,
                inclination=inc_rad,
                longitude_of_ascending_node=omega_rad,
                argument_of_periapsis=w_rad,
                mean_anomaly_at_epoch=m_rad,
                orbital_period_days=p_days,
                mean_anomaly=m_rad,
                true_anomaly=nu,
                center_position={"x": 0.0, "y": 0.0, "z": 0.0}
            )

            # Physical characteristics
            # Radius (meters)
            r_m: float | None = None
            if 'pl_rade' in table.colnames and not np.ma.is_masked(row['pl_rade']):
                r_e = safe_float(row['pl_rade'], default=0.0)
                if r_e > 0:
                    r_m = r_e * EARTH_RADIUS_M
            if r_m is None and 'pl_radj' in table.colnames and not np.ma.is_masked(row['pl_radj']):
                r_j = safe_float(row['pl_radj'], default=0.0)
                if r_j > 0:
                    r_m = r_j * JUPITER_RADIUS_M

            # Mass (kg)
            m_kg: float | None = None
            if 'pl_bmasse' in table.colnames and not np.ma.is_masked(row['pl_bmasse']):
                m_e = safe_float(row['pl_bmasse'], default=0.0)
                if m_e > 0:
                    m_kg = m_e * EARTH_MASS_KG
            if m_kg is None and 'pl_masse' in table.colnames and not np.ma.is_masked(row['pl_masse']):
                m_e = safe_float(row['pl_masse'], default=0.0)
                if m_e > 0:
                    m_kg = m_e * EARTH_MASS_KG
            if m_kg is None and 'pl_bmassj' in table.colnames and not np.ma.is_masked(row['pl_bmassj']):
                m_j = safe_float(row['pl_bmassj'], default=0.0)
                if m_j > 0:
                    m_kg = m_j * JUPITER_MASS_KG

            # Cross-estimation if one is missing
            if r_m is not None and m_kg is None:
                m_kg = estimate_mass_from_radius(r_m)
            elif m_kg is not None and r_m is None:
                r_m = estimate_radius_from_mass(m_kg)
            elif r_m is None and m_kg is None:
                r_m = EARTH_RADIUS_M
                m_kg = EARTH_MASS_KG

            # Density (kg/m^3)
            dens_kg_m3: float | None = None
            if 'pl_dens' in table.colnames and not np.ma.is_masked(row['pl_dens']):
                dens_g_cm3 = safe_float(row['pl_dens'], default=0.0)
                if dens_g_cm3 > 0:
                    dens_kg_m3 = dens_g_cm3 * 1000.0
            if dens_kg_m3 is None:
                dens_kg_m3 = estimate_density(m_kg, r_m)

            # Surface gravity
            g_m_s2 = estimate_surface_gravity(m_kg, r_m)

            # Equilibrium temperature
            teq_k = safe_float(row['pl_eqt']) if 'pl_eqt' in table.colnames else 0.0
            if teq_k <= 0.0:
                teq_k = estimate_equilibrium_temperature(a_au)

            # Coordinates
            ra_deg = safe_float(row['ra']) if 'ra' in table.colnames else 0.0
            dec_deg = safe_float(row['dec']) if 'dec' in table.colnames else 0.0
            dist_pc = safe_float(row['sy_dist']) if 'sy_dist' in table.colnames else 0.0
            if dist_pc <= 0.0 and 'sy_plx' in table.colnames:
                plx_mas = safe_float(row['sy_plx'])
                if plx_mas > 0.0:
                    dist_pc = 1000.0 / plx_mas

            # Host star parameters
            st_mass_sol = safe_float(row['st_mass'], default=1.0) if 'st_mass' in table.colnames else 1.0
            st_rad_sol = safe_float(row['st_rad'], default=1.0) if 'st_rad' in table.colnames else 1.0
            st_teff_k = safe_float(row['st_teff'], default=5778.0) if 'st_teff' in table.colnames else 5778.0
            st_spectype = str(row['st_spectype']).strip() if ('st_spectype' in table.colnames and not np.ma.is_masked(row['st_spectype'])) else None

            # Classification
            p_class = classify_planet_type(
                mass_kg=m_kg,
                radius_m=r_m,
                density_kg_m3=dens_kg_m3,
                has_host=True
            )
            atm_type = classify_atmosphere_type(
                planet_class=p_class,
                surface_temperature_k=teq_k,
                surface_gravity_m_s2=g_m_s2,
                mass_kg=m_kg
            )
            albedo = estimate_albedo(p_class)

            # Surface pressure estimate based on atmosphere
            surface_pressure_pa = 101325.0
            if atm_type == AtmosphereType.THICK_ENVELOPE:
                surface_pressure_pa = 1.0e7
            elif atm_type == AtmosphereType.DENSE:
                surface_pressure_pa = 9.0e6
            elif p_class == PlanetClass.DWARF:
                surface_pressure_pa = 1.0

            rec = PlanetRecord(
                name=name,
                body_id=body_id,
                host_star_name=host_name,
                host_star_id=host_id,

                planet_class=p_class,
                atmosphere_type=atm_type,
                position=pos,
                right_ascension_rad=ra_deg * DEG_TO_RAD,
                declination_rad=dec_deg * DEG_TO_RAD,
                distance_pc=dist_pc,
                semi_major_axis_au=a_au,
                eccentricity=ecc,
                inclination_rad=inc_rad,
                longitude_ascending_node_rad=omega_rad,
                argument_periapsis_rad=w_rad,
                mean_anomaly_rad=m_rad,
                orbital_period_days=p_days,
                mass_kg=m_kg,
                radius_m=r_m,
                density_kg_m3=dens_kg_m3,
                surface_gravity_m_s2=g_m_s2,
                albedo=albedo,
                surface_temperature_k=teq_k,
                surface_pressure_pa=surface_pressure_pa,
                has_rings=1 if p_class == PlanetClass.GAS_GIANT and "saturn" in name.lower() else 0,
                orbit=orbit_rec,
                extra_metadata={
                    "source": self.name,
                    "original_name": pl_name_raw,
                    "hostname": host_name,
                    "st_mass_kg": (st_mass_sol if st_mass_sol > 0 else 1.0) * SOLAR_MASS_KG,
                    "st_radius_m": (st_rad_sol if st_rad_sol > 0 else 1.0) * SOLAR_RADIUS_M,
                    "st_teff_k": st_teff_k if st_teff_k > 0 else 5778.0,
                    "st_spectype": st_spectype,
                }
            )
            records.append(rec)

        return records
