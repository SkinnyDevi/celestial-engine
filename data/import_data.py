import json
import math
import re
import numpy as np
from astroquery.jplhorizons import Horizons
from astroquery.simbad import Simbad
from astropy.time import Time
import astropy.units as u

# --- Constants ---
AU_TO_METERS = 149597870700.0
DEG_TO_RAD = math.pi / 180.0
LY_TO_PC = 1.0 / 3.261563777
PC_TO_METERS = 3.085677581e16
G_CONST = 6.67430e-11  # Gravitational constant in m^3 kg^-1 s^-2

def safe_float(val, default=0.0):
    """Safely converts value to float, handling None, masked arrays, and NaN."""
    if val is None or np.ma.is_masked(val):
        return default
    try:
        f = float(val)
        return default if math.isnan(f) else f
    except (ValueError, TypeError):
        return default

class CelestialImporter:
    SPECTRAL_MAP = {'O': 0, 'B': 1, 'A': 2, 'F': 3, 'G': 4, 'K': 5, 'M': 6}

    # Planet Classes (matching PlanetClass enum in planet.h)
    PLANET_CLASS_TERRESTRIAL = 0
    PLANET_CLASS_GAS_GIANT = 1
    PLANET_CLASS_ICE_GIANT = 2
    PLANET_CLASS_DWARF = 3
    PLANET_CLASS_ROGUE = 4

    # Atmosphere Types (matching AtmosphereType enum in planet.h)
    ATMOSPHERE_NONE = 0
    ATMOSPHERE_THIN = 1
    ATMOSPHERE_STANDARD = 2
    ATMOSPHERE_DENSE = 3
    ATMOSPHERE_THICK_ENVELOPE = 4

    # Moon Classes (matching MoonClass enum in moon.h)
    MOON_CLASS_ROCKY = 0
    MOON_CLASS_ICY = 1
    MOON_CLASS_CAPTURED = 2
    MOON_CLASS_VOLCANIC = 3

    def __init__(self, sim_time):
        self.sim_time = sim_time
        self.orbits = []
        self.stars = []
        self.planets = []
        self.moons = []
        
        self.star_indices = {}
        self.planet_indices = {}
        
        # Configure Simbad
        self.simbad = Simbad()
        self.simbad.ROW_LIMIT = -1
        self.simbad.add_votable_fields('plx_value', 'sp_type')

    def _fetch_orbit_jpl(self, jpl_id, center_id):
        print(f"Fetching orbital data for JPL ID {jpl_id}...")
        obj = Horizons(id=jpl_id, location=center_id, epochs=self.sim_time.jd)
        elements = obj.elements()
        vectors = obj.vectors()
        
        orbit = {
            "semimajor_axis": safe_float(elements['a'][0]) * AU_TO_METERS,
            "eccentricity": safe_float(elements['e'][0]),
            "inclination": safe_float(elements['incl'][0]) * DEG_TO_RAD,
            "longitude_of_ascending_node": safe_float(elements['Omega'][0]) * DEG_TO_RAD,
            "argument_of_periapsis": safe_float(elements['w'][0]) * DEG_TO_RAD,
            "mean_anomaly_at_epoch": safe_float(elements['M'][0]) * DEG_TO_RAD,
            "orbital_period_days": safe_float(elements['P'][0]),
            "center_position": {"x": 0, "y": 0, "z": 0}
        }
        
        self.orbits.append(orbit)
        
        position = {
            "x": safe_float(vectors['x'][0]) * AU_TO_METERS,
            "y": safe_float(vectors['y'][0]) * AU_TO_METERS,
            "z": safe_float(vectors['z'][0]) * AU_TO_METERS
        }
        return len(self.orbits) - 1, position, elements
    
    def parse_spectral_type(self, sp_str):
        if not sp_str or np.ma.is_masked(sp_str):
            return None, None
        if isinstance(sp_str, bytes):
            sp_str = sp_str.decode('utf-8')
        sp_str = sp_str.strip().upper()
        match = re.search(r'([OBAFGKM])(\d(?:\.\d)?)?', sp_str)
        if not match:
            return None, None
        s_class = self.SPECTRAL_MAP[match.group(1)]
        s_sub = int(round(float(match.group(2)))) if match.group(2) else 0
        return s_class, s_sub

    def add_star_manual(self, name, body_id, **kwargs):
        """Adds a star to the registry manually with given physical parameters."""
        clean_name = re.sub(r'[*]+', '', name).strip()
        body_id = re.sub(r'[^A-Za-z0-9_]', '_', body_id).strip('_')[:31].upper()
        star = {
            "name": clean_name,
            "body_id": body_id,
            "position": {"x": 0, "y": 0, "z": 0},
            "rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
        }
        star.update(kwargs)
        self.stars.append(star)
        self.star_indices[name] = len(self.stars) - 1
        self.star_indices[clean_name] = len(self.stars) - 1
        print(f"Added star {clean_name}")

    def add_star_simbad(self, name, body_id, mass_kg, radius_m, **kwargs):
        """Fetches RA/Dec/Distance for a star from Simbad and adds it."""
        print(f"Fetching Simbad data for {name}...")
        result = self.simbad.query_object(name)
        if result is None:
            print(f"Failed to find {name} in Simbad.")
            return
        
        ra_rad = float(result['ra'][0]) * DEG_TO_RAD
        dec_rad = float(result['dec'][0]) * DEG_TO_RAD
        
        # Calculate distance in parsecs from parallax (if available)
        plx = float(result['plx_value'][0]) if not np.ma.is_masked(result['plx_value'][0]) else None
        dist_pc = (1000.0 / plx) if plx else 0.0
        
        # Calculate cartesian coordinates in meters
        dist_m = dist_pc * PC_TO_METERS
        pos_x = dist_m * math.cos(dec_rad) * math.cos(ra_rad)
        pos_y = dist_m * math.cos(dec_rad) * math.sin(ra_rad)
        pos_z = dist_m * math.sin(dec_rad)
        
        clean_name = re.sub(r'[*]+', '', name).strip()
        body_id = re.sub(r'[^A-Za-z0-9_]', '_', body_id).strip('_')[:31].upper()
        star = {
            "name": clean_name,
            "body_id": body_id,
            "position": {"x": pos_x, "y": pos_y, "z": pos_z},
            "rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
            "right_ascension_rad": ra_rad,
            "declination_rad": dec_rad,
            "distance_pc": dist_pc,
            "mass_kg": mass_kg,
            "radius_m": radius_m
        }
        star.update(kwargs)
        self.stars.append(star)
        self.star_indices[name] = len(self.stars) - 1
        self.star_indices[clean_name] = len(self.stars) - 1
        
        # Parse and set spectral type if available
        sp_type_str = result['sp_type'][0] if 'sp_type' in result.colnames and not np.ma.is_masked(result['sp_type'][0]) else None
        stype, ssubtype = self.parse_spectral_type(sp_type_str)
        if stype is not None:
            star["spectral_type"] = stype
            star["spectral_subtype"] = ssubtype
            
        print(f"Added star {clean_name} from Simbad")

    def add_nearby_stars(self, max_distance_ly=None, max_distance_pc=None, limit=50,
                         mass_kg_default=1.989e30, radius_m_default=696340000):
        """
        Fetches stars within a 3D physical distance from the Sun (measured by parallax).
        `max_distance_ly`: Distance limit in light-years.
        `max_distance_pc`: Distance limit in parsecs.
        `limit`: Maximum number of stars to fetch (-1 or None for unlimited).
        """
        if max_distance_pc is None:
            if max_distance_ly is not None:
                max_distance_pc = max_distance_ly * LY_TO_PC
            else:
                max_distance_pc = 5.0  # default ~16.3 light-years
        
        dist_ly = max_distance_pc / LY_TO_PC
        min_plx = 1000.0 / max_distance_pc
        limit_desc = f"up to {limit}" if (limit is not None and limit > 0) else "all"
        print(f"Fetching {limit_desc} nearby stars within {dist_ly:.1f} ly ({max_distance_pc:.1f} pc) of the Sun...")
        
        top_clause = f"TOP {limit} " if (limit is not None and limit > 0) else ""
        query = f"SELECT {top_clause}main_id, ra, dec, plx_value, otype, sp_type FROM basic WHERE plx_value >= {min_plx:.4f} ORDER BY plx_value DESC"
        
        try:
            result = self.simbad.query_tap(query)
        except Exception as e:
            print(f"Failed to query nearby stars via TAP: {e}")
            return
            
        if result is None or len(result) == 0:
            print("No nearby stars found matching criteria.")
            return

        count = 0
        for row in result:
            name = row['main_id']
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            name = name.strip()
            
            # Skip exoplanets
            otype = str(row['otype']) if ('otype' in result.colnames and not np.ma.is_masked(row['otype'])) else ''
            if otype.startswith('Pl'):
                continue
                
            clean_name = re.sub(r'[*]+', '', name).strip()
            if clean_name in self.star_indices or name in self.star_indices:
                continue
                
            body_id = re.sub(r'[^A-Za-z0-9_]', '_', clean_name).strip('_')[:31].upper()
            
            ra_rad = float(row['ra']) * DEG_TO_RAD
            dec_rad = float(row['dec']) * DEG_TO_RAD
            plx = float(row['plx_value'])
            dist_pc = 1000.0 / plx
            dist_m = dist_pc * PC_TO_METERS
            
            pos_x = dist_m * math.cos(dec_rad) * math.cos(ra_rad)
            pos_y = dist_m * math.cos(dec_rad) * math.sin(ra_rad)
            pos_z = dist_m * math.sin(dec_rad)
            
            star = {
                "name": clean_name,
                "body_id": body_id,
                "position": {"x": pos_x, "y": pos_y, "z": pos_z},
                "rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
                "right_ascension_rad": ra_rad,
                "declination_rad": dec_rad,
                "distance_pc": dist_pc,
                "mass_kg": mass_kg_default,
                "radius_m": radius_m_default
            }
            self.stars.append(star)
            self.star_indices[name] = len(self.stars) - 1
            self.star_indices[clean_name] = len(self.stars) - 1

            sp_type_str = row['sp_type'] if ('sp_type' in result.colnames and not np.ma.is_masked(row['sp_type'])) else None
            stype, ssubtype = self.parse_spectral_type(sp_type_str)
            if stype is not None:
                star["spectral_type"] = stype
                star["spectral_subtype"] = ssubtype

            count += 1
            
        print(f"Added {count} nearby stars around the Sun.")

    def add_stars_in_region(self, center_name, radius_degrees, limit=100, default_distance_pc=None, mass_kg_default=1.989e30, radius_m_default=696340000):
        """
        Fetches a batch of stars/objects around a specific celestial region (cone in the sky) and adds them.
        Ideal for extra-solar targets such as galaxies (e.g. 'M31'), nebulae, or clusters.
        """
        if default_distance_pc is not None and default_distance_pc > 50000:
            # We are querying an external galaxy: ignore foreground Milky Way stars
            dist_pc = default_distance_pc

        if center_name.strip().lower() == "sun":
            print(f"Notice: 'Sun' is our local star (origin of coordinates) and does not exist as an extra-solar target in SIMBAD's sky catalog.")
            print(f"Redirecting query to fetch nearby stars by 3D distance ({radius_degrees} ly) from the Sun...")
            return self.add_nearby_stars(max_distance_ly=radius_degrees, limit=limit, mass_kg_default=mass_kg_default, radius_m_default=radius_m_default)

        limit_desc = f"up to {limit}" if (limit is not None and limit > 0) else "all"
        print(f"Fetching {limit_desc} objects around {center_name} (radius {radius_degrees} deg)...")
        
        prev_limit = self.simbad.ROW_LIMIT
        self.simbad.ROW_LIMIT = limit if (limit is not None and limit > 0) else -1
        try:
            result = self.simbad.query_region(center_name, radius=radius_degrees * u.deg)
        finally:
            self.simbad.ROW_LIMIT = prev_limit
        
        if result is None:
            print(f"No objects found in region of {center_name}.")
            return
            
        count = 0
        total = len(result) if result is not None else 0
        for row in result:
            name = row['main_id']
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            name = name.strip()
            
            clean_name = re.sub(r'[*]+', '', name).strip()
            if clean_name in self.star_indices or name in self.star_indices:
                continue
                
            body_id = re.sub(r'[^A-Za-z0-9_]', '_', clean_name).strip('_')[:31].upper()
            
            ra_rad = float(row['ra']) * DEG_TO_RAD
            dec_rad = float(row['dec']) * DEG_TO_RAD
            
            has_plx = 'plx_value' in result.colnames and not np.ma.is_masked(row['plx_value'])
            plx = float(row['plx_value']) if has_plx else None
            
            if plx and plx > 0:
                dist_pc = 1000.0 / plx
            else:
                # Fallback to the galaxy's distance if we can't measure individual parallax
                dist_pc = default_distance_pc if default_distance_pc is not None else 0.0
                
            dist_m = dist_pc * PC_TO_METERS
            pos_x = dist_m * math.cos(dec_rad) * math.cos(ra_rad)
            pos_y = dist_m * math.cos(dec_rad) * math.sin(ra_rad)
            pos_z = dist_m * math.sin(dec_rad)
            
            star = {
                "name": clean_name,
                "body_id": body_id,
                "position": {"x": pos_x, "y": pos_y, "z": pos_z},
                "rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
                "right_ascension_rad": ra_rad,
                "declination_rad": dec_rad,
                "distance_pc": dist_pc,
                "mass_kg": mass_kg_default,
                "radius_m": radius_m_default
            }
            self.stars.append(star)
            self.star_indices[name] = len(self.stars) - 1
            self.star_indices[clean_name] = len(self.stars) - 1

            sp_type_str = row['sp_type'] if ('sp_type' in result.colnames and not np.ma.is_masked(row['sp_type'])) else None
            stype, ssubtype = self.parse_spectral_type(sp_type_str)
            if stype is not None:
                star["spectral_type"] = stype
                star["spectral_subtype"] = ssubtype
            
            print(f"DEBUG | {count + 1}/{total} | Added star {name}")
            count += 1
            
        print(f"Added {count} objects from {center_name} region.")

    def add_planet(self, name, body_id, jpl_id, center_id, host_star_name, **kwargs):
        """Fetches orbital data from JPL Horizons and adds a planet."""
        orbit_idx, position, elements = self._fetch_orbit_jpl(jpl_id, center_id)
        
        planet = {
            "name": name,
            "body_id": body_id,
            "host_star_index": self.star_indices[host_star_name],
            "orbit_index": orbit_idx,
            "position": position,
            "rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
            "semi_major_axis_au": safe_float(elements['a'][0]),
            "eccentricity": safe_float(elements['e'][0]),
            "inclination_rad": safe_float(elements['incl'][0]) * DEG_TO_RAD,
            "longitude_ascending_node_rad": safe_float(elements['Omega'][0]) * DEG_TO_RAD,
            "argument_periapsis_rad": safe_float(elements['w'][0]) * DEG_TO_RAD,
            "mean_anomaly_rad": safe_float(elements['M'][0]) * DEG_TO_RAD,
            "orbital_period_days": safe_float(elements['P'][0]),
        }

        # Auto-compute surface gravity and density if mass and radius are present
        mass = kwargs.get("mass_kg")
        radius = kwargs.get("radius_m")
        if mass and radius and radius > 0:
            if "surface_gravity_m_s2" not in kwargs:
                planet["surface_gravity_m_s2"] = (G_CONST * mass) / (radius ** 2)
            if "density_kg_m3" not in kwargs:
                volume = (4.0 / 3.0) * math.pi * (radius ** 3)
                planet["density_kg_m3"] = mass / volume

        planet.update(kwargs)
        self.planets.append(planet)
        self.planet_indices[name] = len(self.planets) - 1
        self.planet_indices[body_id] = len(self.planets) - 1
        print(f"Added planet {name}")

    def add_moon(self, name, body_id, jpl_id, center_id, host_planet_name, **kwargs):
        """Fetches orbital data from JPL Horizons and adds a moon."""
        orbit_idx, position, elements = self._fetch_orbit_jpl(jpl_id, center_id)
        
        moon = {
            "name": name,
            "body_id": body_id,
            "host_planet_index": self.planet_indices[host_planet_name],
            "orbit_index": orbit_idx,
            "position": position,
            "rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
            "semi_major_axis_km": safe_float(elements['a'][0]) * (AU_TO_METERS / 1000.0),
            "eccentricity": safe_float(elements['e'][0]),
            "inclination_rad": safe_float(elements['incl'][0]) * DEG_TO_RAD,
            "longitude_ascending_node_rad": safe_float(elements['Omega'][0]) * DEG_TO_RAD,
            "argument_periapsis_rad": safe_float(elements['w'][0]) * DEG_TO_RAD,
            "mean_anomaly_rad": safe_float(elements['M'][0]) * DEG_TO_RAD,
            "orbital_period_days": safe_float(elements['P'][0]),
        }

        # Auto-compute surface gravity if mass and radius are present
        mass = kwargs.get("mass_kg")
        radius = kwargs.get("radius_m")
        if mass and radius and radius > 0:
            if "surface_gravity_m_s2" not in kwargs:
                moon["surface_gravity_m_s2"] = (G_CONST * mass) / (radius ** 2)

        moon.update(kwargs)
        self.moons.append(moon)
        print(f"Added moon {name}")

    def add_solar_system(self, include_moons=True, include_dwarf_planets=True):
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
                spectral_type=4,  # Class G
                spectral_subtype=8,
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
            planet_class=self.PLANET_CLASS_TERRESTRIAL,
            radius_m=2439700, mass_kg=3.3011e23,
            surface_temperature_k=440.0,
            atmosphere_type=self.ATMOSPHERE_THIN,
            surface_pressure_pa=1e-9,
            has_rings=0,
            albedo=0.106,
            axial_tilt_rad=0.034 * DEG_TO_RAD,
            rotation_period_days=58.646
        )

        # Venus
        self.add_planet(
            name="Venus", body_id="VENUS", jpl_id="299", center_id="@sun", host_star_name="Sun",
            planet_class=self.PLANET_CLASS_TERRESTRIAL,
            radius_m=6051800, mass_kg=4.8675e24,
            surface_temperature_k=737.0,
            atmosphere_type=self.ATMOSPHERE_DENSE,
            surface_pressure_pa=9.3e6,
            has_rings=0,
            albedo=0.77,
            axial_tilt_rad=177.36 * DEG_TO_RAD,
            rotation_period_days=-243.02
        )

        # Earth
        self.add_planet(
            name="Earth", body_id="EARTH", jpl_id="399", center_id="@sun", host_star_name="Sun",
            planet_class=self.PLANET_CLASS_TERRESTRIAL,
            radius_m=6371000, mass_kg=5.97237e24,
            surface_temperature_k=288.0,
            atmosphere_type=self.ATMOSPHERE_STANDARD,
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
            planet_class=self.PLANET_CLASS_TERRESTRIAL,
            radius_m=3389500, mass_kg=6.4171e23,
            surface_temperature_k=210.0,
            atmosphere_type=self.ATMOSPHERE_THIN,
            surface_pressure_pa=610.0,
            has_rings=0,
            albedo=0.17,
            axial_tilt_rad=25.19 * DEG_TO_RAD,
            rotation_period_days=1.025957
        )

        # Jupiter
        self.add_planet(
            name="Jupiter", body_id="JUPITER", jpl_id="599", center_id="@sun", host_star_name="Sun",
            planet_class=self.PLANET_CLASS_GAS_GIANT,
            radius_m=69911000, mass_kg=1.8982e27,
            surface_temperature_k=165.0,
            atmosphere_type=self.ATMOSPHERE_THICK_ENVELOPE,
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
            planet_class=self.PLANET_CLASS_GAS_GIANT,
            radius_m=58232000, mass_kg=5.6834e26,
            surface_temperature_k=134.0,
            atmosphere_type=self.ATMOSPHERE_THICK_ENVELOPE,
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
            planet_class=self.PLANET_CLASS_ICE_GIANT,
            radius_m=25362000, mass_kg=8.681e25,
            surface_temperature_k=76.0,
            atmosphere_type=self.ATMOSPHERE_THICK_ENVELOPE,
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
            planet_class=self.PLANET_CLASS_ICE_GIANT,
            radius_m=24622000, mass_kg=1.024e26,
            surface_temperature_k=72.0,
            atmosphere_type=self.ATMOSPHERE_THICK_ENVELOPE,
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
                planet_class=self.PLANET_CLASS_DWARF,
                radius_m=1188300, mass_kg=1.303e22,
                surface_temperature_k=44.0,
                atmosphere_type=self.ATMOSPHERE_THIN,
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
                moon_class=self.MOON_CLASS_ROCKY,
                radius_m=1737400, mass_kg=7.342e22,
                surface_temperature_k=250.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=27.321661,
                albedo=0.12
            )

            # --- Mars's Moons ---
            self.add_moon(
                name="Phobos", body_id="PHOBOS", jpl_id="401", center_id="@499", host_planet_name="Mars",
                moon_class=self.MOON_CLASS_CAPTURED,
                radius_m=11262, mass_kg=1.0659e16,
                surface_temperature_k=233.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=0.3189,
                albedo=0.071
            )
            self.add_moon(
                name="Deimos", body_id="DEIMOS", jpl_id="402", center_id="@499", host_planet_name="Mars",
                moon_class=self.MOON_CLASS_CAPTURED,
                radius_m=6255, mass_kg=1.4762e15,
                surface_temperature_k=233.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=1.263,
                albedo=0.068
            )

            # --- Jupiter's Galilean Moons ---
            self.add_moon(
                name="Io", body_id="IO", jpl_id="501", center_id="@599", host_planet_name="Jupiter",
                moon_class=self.MOON_CLASS_VOLCANIC,
                radius_m=1821600, mass_kg=8.9319e22,
                surface_temperature_k=130.0,
                atmosphere_type=self.ATMOSPHERE_THIN,
                is_tidally_locked=1,
                rotation_period_days=1.769,
                albedo=0.63
            )
            self.add_moon(
                name="Europa", body_id="EUROPA", jpl_id="502", center_id="@599", host_planet_name="Jupiter",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=1560800, mass_kg=4.7998e22,
                surface_temperature_k=102.0,
                atmosphere_type=self.ATMOSPHERE_THIN,
                is_tidally_locked=1,
                rotation_period_days=3.551,
                albedo=0.67
            )
            self.add_moon(
                name="Ganymede", body_id="GANYMEDE", jpl_id="503", center_id="@599", host_planet_name="Jupiter",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=2634100, mass_kg=1.4819e23,
                surface_temperature_k=110.0,
                atmosphere_type=self.ATMOSPHERE_THIN,
                is_tidally_locked=1,
                rotation_period_days=7.154,
                albedo=0.43
            )
            self.add_moon(
                name="Callisto", body_id="CALLISTO", jpl_id="504", center_id="@599", host_planet_name="Jupiter",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=2410300, mass_kg=1.0759e23,
                surface_temperature_k=134.0,
                atmosphere_type=self.ATMOSPHERE_THIN,
                is_tidally_locked=1,
                rotation_period_days=16.689,
                albedo=0.22
            )

            # --- Saturn's Major Moons ---
            self.add_moon(
                name="Mimas", body_id="MIMAS", jpl_id="601", center_id="@699", host_planet_name="Saturn",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=198200, mass_kg=3.75e19,
                surface_temperature_k=64.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=0.942,
                albedo=0.96
            )
            self.add_moon(
                name="Enceladus", body_id="ENCELADUS", jpl_id="602", center_id="@699", host_planet_name="Saturn",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=252100, mass_kg=1.08e20,
                surface_temperature_k=75.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=1.370,
                albedo=0.99
            )
            self.add_moon(
                name="Tethys", body_id="TETHYS", jpl_id="603", center_id="@699", host_planet_name="Saturn",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=531100, mass_kg=6.17e20,
                surface_temperature_k=86.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=1.888,
                albedo=0.8
            )
            self.add_moon(
                name="Dione", body_id="DIONE", jpl_id="604", center_id="@699", host_planet_name="Saturn",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=561400, mass_kg=1.095e21,
                surface_temperature_k=87.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=2.737,
                albedo=0.6
            )
            self.add_moon(
                name="Rhea", body_id="RHEA", jpl_id="605", center_id="@699", host_planet_name="Saturn",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=763800, mass_kg=2.306e21,
                surface_temperature_k=76.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=4.518,
                albedo=0.95
            )
            self.add_moon(
                name="Titan", body_id="TITAN", jpl_id="606", center_id="@699", host_planet_name="Saturn",
                moon_class=self.MOON_CLASS_ROCKY,
                radius_m=2574700, mass_kg=1.3452e23,
                surface_temperature_k=94.0,
                atmosphere_type=self.ATMOSPHERE_DENSE,
                surface_pressure_pa=146700.0,
                is_tidally_locked=1,
                rotation_period_days=15.945,
                albedo=0.22
            )
            self.add_moon(
                name="Iapetus", body_id="IAPETUS", jpl_id="608", center_id="@699", host_planet_name="Saturn",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=734500, mass_kg=1.805e21,
                surface_temperature_k=110.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=79.321,
                albedo=0.2
            )

            # --- Uranus's Major Moons ---
            self.add_moon(
                name="Miranda", body_id="MIRANDA", jpl_id="705", center_id="@799", host_planet_name="Uranus",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=235800, mass_kg=6.59e19,
                surface_temperature_k=60.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=1.413,
                albedo=0.32
            )
            self.add_moon(
                name="Ariel", body_id="ARIEL", jpl_id="701", center_id="@799", host_planet_name="Uranus",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=578900, mass_kg=1.25e21,
                surface_temperature_k=60.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=2.520,
                albedo=0.39
            )
            self.add_moon(
                name="Umbriel", body_id="UMBRIEL", jpl_id="702", center_id="@799", host_planet_name="Uranus",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=584700, mass_kg=1.27e21,
                surface_temperature_k=75.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=4.144,
                albedo=0.21
            )
            self.add_moon(
                name="Titania", body_id="TITANIA", jpl_id="703", center_id="@799", host_planet_name="Uranus",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=788400, mass_kg=3.40e21,
                surface_temperature_k=70.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=8.706,
                albedo=0.27
            )
            self.add_moon(
                name="Oberon", body_id="OBERON", jpl_id="704", center_id="@799", host_planet_name="Uranus",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=761400, mass_kg=3.01e21,
                surface_temperature_k=75.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=13.463,
                albedo=0.23
            )

            # --- Neptune's Major Moons ---
            self.add_moon(
                name="Proteus", body_id="PROTEUS", jpl_id="808", center_id="@899", host_planet_name="Neptune",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=210000, mass_kg=4.4e19,
                surface_temperature_k=51.0,
                atmosphere_type=self.ATMOSPHERE_NONE,
                is_tidally_locked=1,
                rotation_period_days=1.122,
                albedo=0.096
            )
            self.add_moon(
                name="Triton", body_id="TRITON", jpl_id="801", center_id="@899", host_planet_name="Neptune",
                moon_class=self.MOON_CLASS_ICY,
                radius_m=1353400, mass_kg=2.14e22,
                surface_temperature_k=38.0,
                atmosphere_type=self.ATMOSPHERE_THIN,
                surface_pressure_pa=1.4,
                is_tidally_locked=1,
                rotation_period_days=-5.877,
                albedo=0.76
            )

            # --- Pluto's Moon Charon ---
            if include_dwarf_planets and ("Pluto" in self.planet_indices or "PLUTO" in self.planet_indices):
                self.add_moon(
                    name="Charon", body_id="CHARON", jpl_id="901", center_id="@999", host_planet_name="Pluto",
                    moon_class=self.MOON_CLASS_ICY,
                    radius_m=606000, mass_kg=1.586e21,
                    surface_temperature_k=53.0,
                    atmosphere_type=self.ATMOSPHERE_NONE,
                    is_tidally_locked=1,
                    rotation_period_days=-6.387,
                    albedo=0.38
                )

        print("Completed importing Solar System data.")

    def save(self, filepath):
        """Dumps all collected data to the JSON schema."""
        output_data = {
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
        with open(filepath, 'w') as f:
            json.dump(output_data, f, indent=4)
        print(f"Successfully saved to {filepath}")


def main():
    # 1. Initialize the importer with your simulation date
    SEARCH_DEGREES = 22.5

    importer = CelestialImporter(Time("2024-10-05T12:30:00"))
    
    # -------------------------------------------------------------------------
    # SOLAR SYSTEM (Sun, All 8 Planets, Dwarf Planet Pluto, and Major Moons)
    # -------------------------------------------------------------------------
    importer.add_solar_system(include_moons=True, include_dwarf_planets=True)

    # -------------------------------------------------------------------------
    # EXTRA-SOLAR STARS & GALAXIES (Optional demonstration)
    # -------------------------------------------------------------------------
    # Add Sirius dynamically via SIMBAD (requires providing mass/radius manually)
    importer.add_star_simbad("Sirius", "SIRIUS", mass_kg=4.01e30, radius_m=1190000000)
    
    # Add Alpha Centauri via SIMBAD (closest star system)
    importer.add_star_simbad("Alpha Centauri", "ALPHA_CENTAURI", mass_kg=2.2e30, radius_m=1.2e9)

    # Fetch nearby stars within 15 lightyears of the Sun (e.g. Proxima Centauri, Barnard's Star, etc.)
    # Use max_distance_ly for 3D distance sphere around the Sun, limit=-1 for unlimited
    importer.add_nearby_stars(max_distance_ly=15.0, limit=50)
    
    # Fetch stars within the Andromeda Galaxy (M31) sky region (angular cone)
    importer.add_stars_in_region("M31", radius_degrees=SEARCH_DEGREES, limit=-1, default_distance_pc=780000)

    # -------------------------------------------------------------------------
    # Save the file
    # -------------------------------------------------------------------------
    importer.save(f'real_world_data_{SEARCH_DEGREES}deg.json')

if __name__ == "__main__":
    main()
