import json
import math
from astroquery.jplhorizons import Horizons
from astroquery.simbad import Simbad
from astropy.time import Time
import astropy.units as u

# --- Constants ---
AU_TO_METERS = 149597870700.0
DEG_TO_RAD = math.pi / 180.0

class CelestialImporter:
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

    def add_star_manual(self, name, body_id, **kwargs):
        """Adds a star to the registry manually with given physical parameters."""
        star = {
            "name": name,
            "body_id": body_id,
            "position": {"x": 0, "y": 0, "z": 0},
            "rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
        }
        star.update(kwargs)
        self.stars.append(star)
        self.star_indices[name] = len(self.stars) - 1
        print(f"Added star {name}")

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
        plx = float(result['plx_value'][0]) if not result['plx_value'].mask[0] else None
        dist_pc = (1000.0 / plx) if plx else 0.0
        
        # Calculate cartesian coordinates in meters (1 pc = 3.085677581e16 m)
        dist_m = dist_pc * 3.085677581e16
        pos_x = dist_m * math.cos(dec_rad) * math.cos(ra_rad)
        pos_y = dist_m * math.cos(dec_rad) * math.sin(ra_rad)
        pos_z = dist_m * math.sin(dec_rad)
        
        star = {
            "name": name,
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
        print(f"Added star {name} from Simbad")

    def add_stars_in_region(self, center_name, radius_degrees, limit=100, default_distance_pc=None, mass_kg_default=1.989e30, radius_m_default=696340000):
        """Fetches a batch of stars/objects around a specific region and adds them."""
        print(f"Fetching up to {limit} objects around {center_name} (radius {radius_degrees} deg)...")
        
        self.simbad.ROW_LIMIT = limit
        result = self.simbad.query_region(center_name, radius=radius_degrees * u.deg)
        self.simbad.ROW_LIMIT = 0 # reset
        
        if result is None:
            print(f"No objects found in region of {center_name}.")
            return
            
        count = 0
        for row in result:
            name = row['main_id']
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            body_id = name.replace(" ", "_").upper()
            
            ra_rad = float(row['ra']) * DEG_TO_RAD
            dec_rad = float(row['dec']) * DEG_TO_RAD
            
            plx = float(row['plx_value']) if 'plx_value' in result.colnames and not result['plx_value'].mask[count] else None
            
            if plx and plx > 0:
                dist_pc = 1000.0 / plx
            else:
                # Fallback to the galaxy's distance if we can't measure individual parallax
                dist_pc = default_distance_pc if default_distance_pc is not None else 0.0
                
            dist_m = dist_pc * 3.085677581e16
            pos_x = dist_m * math.cos(dec_rad) * math.cos(ra_rad)
            pos_y = dist_m * math.cos(dec_rad) * math.sin(ra_rad)
            pos_z = dist_m * math.sin(dec_rad)
            
            star = {
                "name": name,
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

    # NEW: Fetch 50 known stars/objects within the Andromeda Galaxy region!
    # M31 is roughly 780,000 parsecs away.
    importer.add_stars_in_region("M31", radius_degrees=1.0, limit=50, default_distance_pc=780000)
    
    
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
