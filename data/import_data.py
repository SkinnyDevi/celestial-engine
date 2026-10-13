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

class CelestialImporter:
    SPECTRAL_MAP = {'O': 0, 'B': 1, 'A': 2, 'F': 3, 'G': 4, 'K': 5, 'M': 6}

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
            "semimajor_axis": float(elements['a'][0]) * AU_TO_METERS,
            "eccentricity": float(elements['e'][0]),
            "inclination": float(elements['incl'][0]) * DEG_TO_RAD,
            "longitude_of_ascending_node": float(elements['Omega'][0]) * DEG_TO_RAD,
            "argument_of_periapsis": float(elements['w'][0]) * DEG_TO_RAD,
            "mean_anomaly_at_epoch": float(elements['M'][0]) * DEG_TO_RAD,
            "orbital_period_days": float(elements['P'][0]),
            "center_position": {"x": 0, "y": 0, "z": 0}
        }
        
        self.orbits.append(orbit)
        
        position = {
            "x": float(vectors['x'][0]) * AU_TO_METERS,
            "y": float(vectors['y'][0]) * AU_TO_METERS,
            "z": float(vectors['z'][0]) * AU_TO_METERS
        }
        return len(self.orbits) - 1, position
    
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
            
            count += 1
            
        print(f"Added {count} objects from {center_name} region.")

    def add_planet(self, name, body_id, jpl_id, center_id, host_star_name, **kwargs):
        """Fetches orbital data from JPL Horizons and adds a planet."""
        orbit_idx, position = self._fetch_orbit_jpl(jpl_id, center_id)
        
        planet = {
            "name": name,
            "body_id": body_id,
            "host_star_index": self.star_indices[host_star_name],
            "orbit_index": orbit_idx,
            "position": position,
            "rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
        }
        planet.update(kwargs)
        self.planets.append(planet)
        self.planet_indices[name] = len(self.planets) - 1
        print(f"Added planet {name}")

    def add_moon(self, name, body_id, jpl_id, center_id, host_planet_name, **kwargs):
        """Fetches orbital data from JPL Horizons and adds a moon."""
        orbit_idx, position = self._fetch_orbit_jpl(jpl_id, center_id)
        
        moon = {
            "name": name,
            "body_id": body_id,
            "host_planet_index": self.planet_indices[host_planet_name],
            "orbit_index": orbit_idx,
            "position": position,
            "rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
        }
        moon.update(kwargs)
        self.moons.append(moon)
        print(f"Added moon {name}")
        
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
    importer = CelestialImporter(Time("2024-10-05T12:30:00"))
    
    # -------------------------------------------------------------------------
    # STARS & GALAXIES
    # -------------------------------------------------------------------------
    # Add our Sun manually
    importer.add_star_manual("Sun", "SUN", mass_kg=1.98847e30, radius_m=696340000, 
                             spectral_type=4, spectral_subtype=8)
    
    # Add Sirius dynamically via SIMBAD (requires providing mass/radius manually)
    importer.add_star_simbad("Sirius", "SIRIUS", mass_kg=4.01e30, radius_m=1190000000)
    
    # Add Alpha Centauri via SIMBAD (closest star system)
    importer.add_star_simbad("Alpha Centauri", "ALPHA_CENTAURI", mass_kg=2.2e30, radius_m=1.2e9)

    # Fetch nearby stars within 15 lightyears of the Sun (e.g. Proxima Centauri, Barnard's Star, etc.)
    # Use max_distance_ly for 3D distance sphere around the Sun, limit=-1 for unlimited
    importer.add_nearby_stars(max_distance_ly=15.0, limit=50)
    
    # Fetch stars within the Andromeda Galaxy (M31) sky region (angular cone)
    importer.add_stars_in_region("M31", radius_degrees=0.25, limit=-1, default_distance_pc=780000)
    
    
    # -------------------------------------------------------------------------
    # PLANETS (Solar System)
    # JPL ID: e.g. "399" for Earth, Center: "@sun" (Sun)
    # -------------------------------------------------------------------------
    importer.add_planet("Venus", "VENUS", jpl_id="299", center_id="@sun", host_star_name="Sun",
                        planet_class=0, radius_m=6051000, mass_kg=4.867e24, atmosphere_type=3)
    
    importer.add_planet("Earth", "EARTH", jpl_id="399", center_id="@sun", host_star_name="Sun",
                        planet_class=0, radius_m=6371000, mass_kg=5.972e24, atmosphere_type=2)
    
    importer.add_planet("Jupiter", "JUPITER", jpl_id="599", center_id="@sun", host_star_name="Sun",
                        planet_class=1, radius_m=69911000, mass_kg=1.898e27, atmosphere_type=4, has_rings=1)
    
    importer.add_planet("Saturn", "SATURN", jpl_id="699", center_id="@sun", host_star_name="Sun",
                        planet_class=1, radius_m=58232000, mass_kg=5.683e26, atmosphere_type=4, has_rings=1)


    # -------------------------------------------------------------------------
    # MOONS
    # JPL ID: e.g. "301" for Moon, Center: "@399" (Earth)
    # -------------------------------------------------------------------------
    # Earth's Moon
    importer.add_moon("Moon", "LUNA", jpl_id="301", center_id="@399", host_planet_name="Earth",
                      moon_class=0, radius_m=1737400, mass_kg=7.342e22)
    
    # Jupiter's Moons
    importer.add_moon("Io", "IO", jpl_id="501", center_id="@599", host_planet_name="Jupiter",
                      moon_class=0, radius_m=1821600, mass_kg=8.93e22)
    importer.add_moon("Europa", "EUROPA", jpl_id="502", center_id="@599", host_planet_name="Jupiter",
                      moon_class=0, radius_m=1560800, mass_kg=4.80e22)
    importer.add_moon("Ganymede", "GANYMEDE", jpl_id="503", center_id="@599", host_planet_name="Jupiter",
                      moon_class=0, radius_m=2634100, mass_kg=1.4819e23)
    importer.add_moon("Callisto", "CALLISTO", jpl_id="504", center_id="@599", host_planet_name="Jupiter",
                      moon_class=0, radius_m=2410300, mass_kg=1.0759e23)

    # Saturn's Moons
    importer.add_moon("Titan", "TITAN", jpl_id="606", center_id="@699", host_planet_name="Saturn",
                      moon_class=0, radius_m=2574700, mass_kg=1.345e23, atmosphere_type=3)

    # -------------------------------------------------------------------------
    # Save the file
    # -------------------------------------------------------------------------
    importer.save('real_world_data.json')

if __name__ == "__main__":
    main()
