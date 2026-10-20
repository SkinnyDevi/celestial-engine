"""
Unit tests for Planets Architecture and Providers:
- Classification of all planet types (Terrestrial, Gas Giant, Ice Giant, Dwarf, Rogue)
- Atmosphere classification
- Keplerian orbital mechanics and 3D positioning
- PlanetRecord and OrbitRecord engine schema serialization
- SolarSystemPlanetProvider, RoguePlanetProvider, NasaExoplanetProvider
- PlanetResolver facade orchestration
- CelestialImporter end-to-end integration and JSON schema validation
"""

import json
import math
import tempfile
import unittest
from pathlib import Path

import astropy.units as astrounits
from astropy.coordinates import SkyCoord
from astropy.table import Table
from astropy.time import Time
import jsonschema

from core.constants import (
    AU_TO_METERS,
    DEG_TO_RAD,
    EARTH_MASS_KG,
    EARTH_RADIUS_M,
    JUPITER_MASS_KG,
    JUPITER_RADIUS_M,
    PC_TO_METERS,
)
from core.space import PlanetClass, AtmosphereType
from core.planets import (
    OrbitRecord,
    PlanetRecord,
    PlanetResolver,
    RoguePlanetProvider,
    SolarSystemPlanetProvider,
    classify_atmosphere_type,
    classify_planet_type,
    estimate_albedo,
    estimate_density,
    estimate_equilibrium_temperature,
    estimate_mass_from_radius,
    estimate_period_from_semimajor_axis,
    estimate_radius_from_mass,
    estimate_semimajor_axis_from_period,
    estimate_surface_gravity,
    keplerian_to_cartesian,
    sanitize_planet_id,
    solve_kepler,
    true_anomaly_from_eccentric,
)
from core.planets.providers.nasa_exoplanet import NasaExoplanetProvider
from core.celestial_importer import CelestialImporter

class TestPlanetClassifications(unittest.TestCase):
    def test_classify_all_types(self):
        """Verifies scientific classification of all planet types."""
        # 1. Rogue planet (no host)
        self.assertEqual(classify_planet_type(has_host=False), PlanetClass.ROGUE)
        self.assertEqual(classify_planet_type(raw_type_str="free-floating planet"), PlanetClass.ROGUE)

        # 2. Dwarf planet
        self.assertEqual(classify_planet_type(is_dwarf=True), PlanetClass.DWARF)
        self.assertEqual(
            classify_planet_type(mass_kg=1.3e22, radius_m=1.18e6),
            PlanetClass.DWARF
        )

        # 3. Gas Giant (e.g. Jupiter, Saturn, Hot Jupiters)
        self.assertEqual(
            classify_planet_type(mass_kg=JUPITER_MASS_KG, radius_m=JUPITER_RADIUS_M),
            PlanetClass.GAS_GIANT
        )
        self.assertEqual(
            classify_planet_type(radius_m=7.0 * EARTH_RADIUS_M),
            PlanetClass.GAS_GIANT
        )

        # 4. Ice Giant (e.g. Neptune, Uranus, Sub-Neptunes)
        self.assertEqual(
            classify_planet_type(mass_kg=17.0 * EARTH_MASS_KG, radius_m=3.8 * EARTH_RADIUS_M),
            PlanetClass.ICE_GIANT
        )
        self.assertEqual(
            classify_planet_type(radius_m=2.5 * EARTH_RADIUS_M),
            PlanetClass.ICE_GIANT
        )

        # 5. Terrestrial (e.g. Earth, Mars, Venus, Mercury, Super-Earths)
        self.assertEqual(
            classify_planet_type(mass_kg=EARTH_MASS_KG, radius_m=EARTH_RADIUS_M),
            PlanetClass.TERRESTRIAL
        )
        self.assertEqual(
            classify_planet_type(mass_kg=0.1 * EARTH_MASS_KG, radius_m=0.53 * EARTH_RADIUS_M),
            PlanetClass.TERRESTRIAL
        )

    def test_classify_atmosphere_types(self):
        """Verifies atmosphere categorization across planetary environments."""
        # Gas giants and Ice giants always have thick gaseous envelopes
        self.assertEqual(
            classify_atmosphere_type(PlanetClass.GAS_GIANT),
            AtmosphereType.THICK_ENVELOPE
        )
        self.assertEqual(
            classify_atmosphere_type(PlanetClass.ICE_GIANT),
            AtmosphereType.THICK_ENVELOPE
        )

        # Hot rocky planet (Venus-like)
        self.assertEqual(
            classify_atmosphere_type(PlanetClass.TERRESTRIAL, surface_temperature_k=737.0, surface_gravity_m_s2=8.87),
            AtmosphereType.DENSE
        )

        # Earth-like temperate terrestrial planet
        self.assertEqual(
            classify_atmosphere_type(PlanetClass.TERRESTRIAL, surface_temperature_k=288.0, surface_gravity_m_s2=9.81),
            AtmosphereType.STANDARD
        )

        # Mars-like / low gravity cold terrestrial
        self.assertEqual(
            classify_atmosphere_type(PlanetClass.TERRESTRIAL, surface_temperature_k=210.0, surface_gravity_m_s2=3.7),
            AtmosphereType.THIN
        )

        # Airless body
        self.assertEqual(
            classify_atmosphere_type(PlanetClass.DWARF, surface_temperature_k=150.0),
            AtmosphereType.NONE
        )

    def test_physical_estimations(self):
        """Verifies mass-radius, surface gravity, and density calculations."""
        # Earth surface gravity ~ 9.81 m/s^2
        g = estimate_surface_gravity(EARTH_MASS_KG, EARTH_RADIUS_M)
        self.assertAlmostEqual(g, 9.81, places=1)

        # Earth bulk density ~ 5515 kg/m^3
        rho = estimate_density(EARTH_MASS_KG, EARTH_RADIUS_M)
        self.assertAlmostEqual(rho, 5515.0, delta=50.0)

        # Radius from mass and mass from radius consistency
        m_est = estimate_mass_from_radius(EARTH_RADIUS_M)
        self.assertAlmostEqual(m_est / EARTH_MASS_KG, 1.0, delta=0.1)

        r_est = estimate_radius_from_mass(EARTH_MASS_KG)
        self.assertAlmostEqual(r_est / EARTH_RADIUS_M, 1.0, delta=0.1)

class TestOrbitalMechanics(unittest.TestCase):
    def test_kepler_solver_circular_and_elliptical(self):
        """Verifies Newton-Raphson Kepler solver."""
        # Circular orbit (e = 0): M == E == nu
        m = 1.25
        e = solve_kepler(m, 0.0)
        self.assertAlmostEqual(e, m, places=6)
        nu = true_anomaly_from_eccentric(e, 0.0)
        self.assertAlmostEqual(nu, m, places=6)

        # Moderate eccentricity (e = 0.2)
        m2 = math.pi / 2.0
        e2 = solve_kepler(m2, 0.2)
        # Verify M = E - e * sin(E)
        m_check = e2 - 0.2 * math.sin(e2)
        self.assertAlmostEqual(m_check, m2, places=6)

    def test_keplerian_to_cartesian_position(self):
        """Verifies 3D Cartesian position vector calculation."""
        a_m = AU_TO_METERS
        e = 0.0  # Circular orbit
        inc = 0.0
        node = 0.0
        peri = 0.0

        # At M = 0: x should be a, y = 0, z = 0
        pos0, _, _ = keplerian_to_cartesian(a_m, e, inc, node, peri, mean_anomaly_rad=0.0)
        self.assertAlmostEqual(pos0["x"], a_m, delta=1.0)
        self.assertAlmostEqual(pos0["y"], 0.0, delta=1.0)
        self.assertAlmostEqual(pos0["z"], 0.0, delta=1.0)

        # At M = pi/2: x should be 0, y = a, z = 0
        pos90, _, _ = keplerian_to_cartesian(a_m, e, inc, node, peri, mean_anomaly_rad=math.pi / 2.0)
        self.assertAlmostEqual(pos90["x"], 0.0, delta=1.0)
        self.assertAlmostEqual(pos90["y"], a_m, delta=1.0)
        self.assertAlmostEqual(pos90["z"], 0.0, delta=1.0)

    def test_kepler_third_law_conversions(self):
        """Verifies period <-> semi-major axis conversions via Kepler's 3rd Law."""
        # 1 AU orbit around Sun should have ~365.25 day period
        p_days = estimate_period_from_semimajor_axis(AU_TO_METERS)
        self.assertAlmostEqual(p_days, 365.25, delta=1.0)

        a_est = estimate_semimajor_axis_from_period(365.25)
        self.assertAlmostEqual(a_est / AU_TO_METERS, 1.0, delta=0.01)

class TestPlanetProviders(unittest.TestCase):
    def test_solar_system_provider_all_classes(self):
        """Verifies Solar System provider outputs Terrestrial, Gas Giant, Ice Giant, and Dwarf planets."""
        prov = SolarSystemPlanetProvider()
        planets = prov.get_all_planets(include_dwarf=True)

        self.assertGreaterEqual(len(planets), 10)
        classes = {p.planet_class for p in planets}
        self.assertIn(PlanetClass.TERRESTRIAL, classes)
        self.assertIn(PlanetClass.GAS_GIANT, classes)
        self.assertIn(PlanetClass.ICE_GIANT, classes)
        self.assertIn(PlanetClass.DWARF, classes)

        # Check Saturn has rings
        saturn = next(p for p in planets if p.name == "Saturn")
        self.assertEqual(saturn.has_rings, 1)
        self.assertGreater(saturn.ring_outer_radius_m, saturn.ring_inner_radius_m)

        # Check Earth
        earth = next(p for p in planets if p.name == "Earth")
        self.assertEqual(earth.planet_class, PlanetClass.TERRESTRIAL)
        self.assertEqual(earth.atmosphere_type, AtmosphereType.STANDARD)
        self.assertAlmostEqual(earth.radius_m, EARTH_RADIUS_M, places=0)

    def test_rogue_planet_provider(self):
        """Verifies RoguePlanetProvider supplies free-floating planets with no host star."""
        prov = RoguePlanetProvider()
        rogues = prov.get_all_rogue_planets()

        self.assertGreaterEqual(len(rogues), 5)
        for r in rogues:
            self.assertEqual(r.planet_class, PlanetClass.ROGUE)
            self.assertEqual(r.host_star_index, -1)
            self.assertEqual(r.orbit_index, -1)
            self.assertIsNone(r.orbit)
            self.assertGreater(r.distance_pc, 0.0)
            # Verify 3D position vector magnitude matches distance
            d_m = math.sqrt(r.position["x"]**2 + r.position["y"]**2 + r.position["z"]**2)
            expected_m = r.distance_pc * PC_TO_METERS
            self.assertAlmostEqual(d_m, expected_m, delta=expected_m * 1e-4)

    def test_nasa_exoplanet_provider_parsing(self):
        """Verifies NasaExoplanetProvider table mapping with mock multi-planet catalog."""
        prov = NasaExoplanetProvider()

        # Construct synthetic table mimicking pscomppars
        mock_data = {
            "pl_name": ["TRAPPIST-1 b", "51 Pegasi b", "GJ 1214 b"],
            "hostname": ["TRAPPIST-1", "51 Pegasi", "GJ 1214"],
            "pl_orbsmax": [0.01154, 0.0527, 0.0141],
            "pl_orbper": [1.51, 4.23, 1.58],
            "pl_orbeccen": [0.006, 0.013, 0.0],
            "pl_orbincl": [89.7, 80.0, 88.7],
            "pl_orblper": [336.8, 58.0, 0.0],
            "pl_bmasse": [1.374, 150.0, 8.17],
            "pl_rade": [1.116, 13.0, 2.74],
            "pl_dens": [5.44, 0.8, 1.87],
            "pl_eqt": [397.0, 1250.0, 596.0],
            "ra": [346.626, 344.366, 257.784],
            "dec": [-5.043, 20.768, 4.953],
            "sy_dist": [12.43, 15.61, 14.64],
        }
        mock_table = Table(mock_data)

        records = prov._table_to_records(mock_table)
        self.assertEqual(len(records), 3)

        # Planet 1: TRAPPIST-1 b (Terrestrial)
        p1 = records[0]
        self.assertEqual(p1.name, "TRAPPIST-1 b")
        self.assertEqual(p1.host_star_name, "TRAPPIST-1")
        self.assertEqual(p1.planet_class, PlanetClass.TERRESTRIAL)
        self.assertAlmostEqual(p1.mass_kg, 1.374 * EARTH_MASS_KG, delta=0.01 * EARTH_MASS_KG)

        # Planet 2: 51 Pegasi b (Hot Jupiter - Gas Giant)
        p2 = records[1]
        self.assertEqual(p2.name, "51 Pegasi b")
        self.assertEqual(p2.planet_class, PlanetClass.GAS_GIANT)
        self.assertEqual(p2.atmosphere_type, AtmosphereType.THICK_ENVELOPE)

        # Planet 3: GJ 1214 b (Sub-Neptune - Ice Giant)
        p3 = records[2]
        self.assertEqual(p3.name, "GJ 1214 b")
        self.assertEqual(p3.planet_class, PlanetClass.ICE_GIANT)

    def test_planet_resolver_orchestration(self):
        """Verifies PlanetResolver facade routing between solar, rogue, and exoplanet providers."""
        resolver = PlanetResolver()

        # Solar host query
        sun_planets = resolver.resolve_planets_for_star("Sun")
        self.assertGreaterEqual(len(sun_planets), 8)

        # Rogue planets query
        rogues = resolver.resolve_rogue_planets()
        self.assertGreaterEqual(len(rogues), 5)

        # Specific known planet
        earth = resolver.get_known_planet("Earth")
        self.assertIsNotNone(earth)
        self.assertEqual(earth.name, "Earth")

class TestCelestialImporterIntegration(unittest.TestCase):
    def test_importer_records_and_schema_validation(self):
        """
        Creates a complete simulation with stars, Solar System planets,
        exoplanets, and rogue planets, and validates the output JSON against schema.json.
        """
        schema_path = Path(__file__).resolve().parent.parent.parent / "src" / "tests" / "data" / "schema.json"
        self.assertTrue(schema_path.exists(), f"schema.json must exist at {schema_path}")

        with open(schema_path, "r") as sf:
            schema = json.load(sf)

        importer = CelestialImporter(
            Time("2024-10-05T12:30:00"),
            max_apparent_magnitude=None
        )

        # 1. Add Sun
        importer.add_star_manual(
            name="Sun",
            body_id="SUN",
            spectral_type=4,
            spectral_subtype=2,
            mass_kg=1.98847e30,
            radius_m=696340000.0,
            surface_temperature_k=5772.0
        )

        # 2. Add Host Star for Exoplanets
        importer.add_star_manual(
            name="TRAPPIST-1",
            body_id="TRAPPIST_1",
            spectral_type=6,
            spectral_subtype=8,
            distance_pc=12.43,
            mass_kg=0.0898 * 1.98847e30,
            radius_m=0.1192 * 696340000.0,
            surface_temperature_k=2566.0
        )

        # 3. Add Solar System planets using records from provider
        sol_planets = importer.planet_resolver.resolve_solar_system_planets(include_dwarf_planets=True)
        for p in sol_planets:
            importer.add_planet_record(p)

        # 4. Add Exoplanet (Terrestrial)
        trappist_b = PlanetRecord(
            name="TRAPPIST-1 b",
            body_id="TRAPPIST_1_B",
            host_star_name="TRAPPIST-1",
            planet_class=PlanetClass.TERRESTRIAL,
            atmosphere_type=AtmosphereType.THIN,
            semi_major_axis_au=0.01154,
            eccentricity=0.0062,
            orbital_period_days=1.5108,
            mass_kg=1.374 * EARTH_MASS_KG,
            radius_m=1.116 * EARTH_RADIUS_M,
            surface_temperature_k=397.6,
            orbit=OrbitRecord(
                semimajor_axis=0.01154 * AU_TO_METERS,
                eccentricity=0.0062,
                orbital_period_days=1.5108,
            )
        )
        importer.add_planet_record(trappist_b)

        # 5. Add Rogue Planet (Free-floating)
        pso_rogue = PlanetRecord(
            name="PSO J318.5-22",
            body_id="PSO_J318_5_22",
            planet_class=PlanetClass.ROGUE,
            atmosphere_type=AtmosphereType.THICK_ENVELOPE,
            mass_kg=6.5 * JUPITER_MASS_KG,
            radius_m=1.53 * JUPITER_RADIUS_M,
            distance_pc=24.6,
            surface_temperature_k=1160.0,
            position={"x": 1e16, "y": 2e16, "z": -1e16},
            orbit=None
        )
        importer.add_planet_record(pso_rogue)

        # Verify all 5 planet classes are represented in simulation!
        classes_in_sim = {p["planet_class"] for p in importer.planets}
        self.assertEqual(
            classes_in_sim,
            {
                PlanetClass.TERRESTRIAL.value,
                PlanetClass.GAS_GIANT.value,
                PlanetClass.ICE_GIANT.value,
                PlanetClass.DWARF.value,
                PlanetClass.ROGUE.value,
            },
            "All 5 planet classes must be present in simulation!"
        )

        # Save to tempfile and validate against schema.json
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tf:
            temp_path = tf.name

        try:
            importer.save(temp_path)
            with open(temp_path, "r") as tf:
                saved_json = json.load(tf)

            # Strict jsonschema validation
            jsonschema.validate(instance=saved_json, schema=schema)
            print("[Test] JSON output successfully validated against official schema.json!")

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_exoplanet_auto_add_missing_host_star(self):
        """
        Tests that an exoplanet whose host star is not initially in the star array
        (e.g. HAT-P-16 b) automatically triggers creation of its host star at its
        true 3D interstellar position, preventing host_star_index from being -1
        and thus preventing the exoplanet from revolving around the Sun.
        """
        importer = CelestialImporter(Time("2024-01-01"))
        importer.add_solar_system(include_moons=False, include_dwarf_planets=False)

        hat_p_16_b = PlanetRecord(
            name="HAT-P-16 b",
            body_id="HAT_P_16_B",
            host_star_name="HAT-P-16",
            planet_class=PlanetClass.GAS_GIANT,
            right_ascension_rad=0.167081,
            declination_rad=0.741121,
            distance_pc=226.637,
            mass_kg=8.012e27,
            radius_m=93550265.0,
            orbit=OrbitRecord(
                semimajor_axis=6178392059.91,
                eccentricity=0.0462,
                inclination=1.542871,
                longitude_of_ascending_node=0.0,
                argument_of_periapsis=3.717551,
                mean_anomaly_at_epoch=2.294009,
                orbital_period_days=2.775967,
            )
        )

        importer.add_planet_record(hat_p_16_b)

        # Host star must have been automatically synthesized and added
        self.assertIn("HAT-P-16", importer.star_indices)
        host_idx = importer.star_indices["HAT-P-16"]
        self.assertGreaterEqual(host_idx, 0)
        self.assertNotEqual(importer.stars[host_idx]["name"], "Sun")

        # Planet must point to that host star index
        planet_dict = [p for p in importer.planets if p["name"] == "HAT-P-16 b"][0]
        self.assertEqual(planet_dict["host_star_index"], host_idx)
        self.assertGreater(planet_dict["host_star_index"], 0)

        # Host star distance must be ~226.6 pc, far from the Sun at (0, 0, 0)
        host_star_dict = importer.stars[host_idx]
        self.assertAlmostEqual(host_star_dict["distance_pc"], 226.637, places=2)
        star_pos = host_star_dict["position"]
        dist_from_origin = math.sqrt(star_pos["x"]**2 + star_pos["y"]**2 + star_pos["z"]**2)
        self.assertGreater(dist_from_origin, 1e18)

if __name__ == "__main__":
    unittest.main()
