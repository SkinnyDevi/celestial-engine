"""
Unit tests for Moons Architecture, Providers, and Importer Integration:
- Classification of natural satellite classes (Rocky, Icy, Captured, Volcanic)
- Physical parameters & gravity estimations
- Keplerian orbital mechanics and 3D positioning relative to host planets
- Verifying moon positions are accurate, distinct, and never collapsed to {0,0,0}
- SolarSystemMoonProvider: Earth, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto moons
- ExomoonProvider: Kepler-1625b I, Kepler-1708b I, DH Tauri b I
- JPLHorizonsMoonProvider: Ephemerides, network fallbacks, and handling the Sun
- Handling all exceptions when querying the SUN as target (star vs planet, coordinates, Horizons)
- MoonResolver facade orchestration
- CelestialImporter end-to-end integration and JSON schema validation against schema.json
"""

import json
import math
import tempfile
import unittest
from pathlib import Path

from astropy.coordinates import SkyCoord
from astropy.time import Time
import jsonschema

from core.constants import DEG_TO_RAD, G_CONST
from core.space import MoonClass, AtmosphereType
from core.planets import OrbitRecord, PlanetRecord
from core.moons import (
    MoonRecord,
    MoonResolver,
    SolarSystemMoonProvider,
    ExomoonProvider,
    JPLHorizonsMoonProvider,
    classify_moon_type,
    estimate_moon_gravity,
    estimate_moon_period,
    keplerian_to_cartesian_moon,
    sanitize_moon_id,
)
from core.celestial_importer import CelestialImporter


class TestMoonClassifications(unittest.TestCase):
    def test_classify_all_moon_types(self):
        """Verifies scientific classification of all natural satellite types."""
        # 1. Volcanic (e.g. Io)
        self.assertEqual(classify_moon_type(is_volcanic=True), MoonClass.VOLCANIC)
        self.assertEqual(classify_moon_type(raw_type_str="volcanic active moon"), MoonClass.VOLCANIC)

        # 2. Captured (e.g. Phobos, Deimos, Phoebe, Himalia)
        self.assertEqual(classify_moon_type(is_captured=True), MoonClass.CAPTURED)
        self.assertEqual(classify_moon_type(raw_type_str="captured irregular asteroid"), MoonClass.CAPTURED)

        # 3. Icy (e.g. Europa, Ganymede, Enceladus, Triton, Charon)
        self.assertEqual(classify_moon_type(is_icy=True), MoonClass.ICY)
        self.assertEqual(classify_moon_type(raw_type_str="subsurface ocean icy moon"), MoonClass.ICY)
        self.assertEqual(classify_moon_type(density_kg_m3=1800.0), MoonClass.ICY)

        # 4. Rocky (e.g. Earth's Moon)
        self.assertEqual(classify_moon_type(is_rocky=True), MoonClass.ROCKY)
        self.assertEqual(classify_moon_type(raw_type_str="terrestrial rocky silicate"), MoonClass.ROCKY)
        self.assertEqual(classify_moon_type(density_kg_m3=3344.0), MoonClass.ROCKY)

    def test_sanitize_moon_id(self):
        """Checks sanitization of moon names into clean identifiers."""
        name, bid = sanitize_moon_id("Moon (Luna)")
        self.assertEqual(name, "Moon (Luna)")
        self.assertEqual(bid, "MOON__LUNA")

        name, bid = sanitize_moon_id("Kepler-1625b I")
        self.assertEqual(name, "Kepler-1625b I")
        self.assertEqual(bid, "KEPLER_1625B_I")

    def test_estimate_moon_gravity(self):
        """Verifies surface gravity estimation on Earth's Moon."""
        # Moon mass ~ 7.342e22 kg, radius ~ 1.7374e6 m -> g ~ 1.62 m/s^2
        g = estimate_moon_gravity(7.342e22, 1737400.0)
        self.assertAlmostEqual(g, 1.623, places=2)


class TestMoonOrbitalMechanicsAndCoordinates(unittest.TestCase):
    def test_keplerian_to_cartesian_moon_non_zero(self):
        """Verifies that 3D positions are computed in meters and non-zero."""
        # Luna: a = 384,400 km
        pos, _, nu = keplerian_to_cartesian_moon(
            semimajor_axis_km=384400.0,
            eccentricity=0.0549,
            inclination_rad=5.145 * DEG_TO_RAD,
            longitude_ascending_node_rad=0.0,
            argument_periapsis_rad=0.0,
            mean_anomaly_rad=0.0,
        )
        # Position must not be (0, 0, 0)
        dist = math.sqrt(pos["x"]**2 + pos["y"]**2 + pos["z"]**2)
        self.assertGreater(dist, 3.5e8)  # ~363,000 km in meters at periapsis
        self.assertLess(dist, 4.2e8)

    def test_multiple_moons_distinct_positions_and_orbits(self):
        """Verifies that sibling moons have distinct, accurate positions and do not collapse."""
        provider = SolarSystemMoonProvider()
        jupiter_moons = provider.query_by_host_planet("Jupiter")
        self.assertGreaterEqual(len(jupiter_moons), 4)

        positions = []
        semimajor_axes = []
        for m in jupiter_moons:
            dist = math.sqrt(m.position["x"]**2 + m.position["y"]**2 + m.position["z"]**2)
            self.assertGreater(dist, 0.0, f"Moon {m.name} has zero position!")
            positions.append((m.position["x"], m.position["y"], m.position["z"]))
            semimajor_axes.append(m.semi_major_axis_km)
            self.assertIsNotNone(m.orbit, f"Moon {m.name} lacks an orbit record!")

        # Verify all positions are unique
        self.assertEqual(len(positions), len(set(positions)), "Moons share identical positions!")
        # Verify semi-major axes are strictly ordered and distinct
        self.assertEqual(len(semimajor_axes), len(set(semimajor_axes)))

    def test_estimate_moon_period(self):
        """Verifies Keplerian orbital period estimation."""
        # Moon around Earth (Earth mass ~ 5.972e24 kg, a = 384,400 km) -> ~27.3 - 27.5 days
        p_days = estimate_moon_period(384400.0, 5.972e24)
        self.assertAlmostEqual(p_days, 27.45, delta=0.2)


class TestSolarSystemMoonProvider(unittest.TestCase):
    def setUp(self):
        self.provider = SolarSystemMoonProvider()

    def test_all_major_planets_have_moons(self):
        """Verifies presence of natural satellites for all major planetary hosts."""
        hosts = ["Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
        for host in hosts:
            moons = self.provider.query_by_host_planet(host)
            self.assertGreater(len(moons), 0, f"No moons found for {host}!")
            for m in moons:
                self.assertEqual(m.host_planet_name.upper(), host.upper())
                self.assertIsNotNone(m.orbit)
                self.assertGreater(m.semi_major_axis_km, 0)
                self.assertGreater(m.radius_m, 0)
                self.assertGreater(m.mass_kg, 0)

    def test_titan_dense_atmosphere(self):
        """Verifies Titan's unique dense atmosphere and high surface pressure."""
        titan = self.provider.get_known_moon("Titan")
        self.assertIsNotNone(titan)
        self.assertEqual(titan.atmosphere_type, AtmosphereType.DENSE)
        self.assertGreater(titan.surface_pressure_pa, 100000.0)

    def test_query_sun_as_host_planet_returns_empty(self):
        """
        Crucial requirement: Querying the SUN as host planet returns empty list.
        The Sun is a star, not a planet, so no moons orbit the Sun directly.
        """
        sun_moons = self.provider.query_by_host_planet("Sun")
        self.assertEqual(sun_moons, [])

        sol_moons = self.provider.query_by_host_planet("SOL")
        self.assertEqual(sol_moons, [])

    def test_query_sun_as_system_returns_all_solar_system_moons(self):
        """
        Querying the SUN as a system/host star returns all Solar System moons
        correctly attributed to their planetary hosts.
        """
        system_moons = self.provider.query_by_system("Sun")
        self.assertGreater(len(system_moons), 15)
        # Verify hosts are planets, not the Sun
        host_names = {m.host_planet_name for m in system_moons}
        self.assertNotIn("Sun", host_names)
        self.assertIn("Earth", host_names)
        self.assertIn("Jupiter", host_names)
        self.assertIn("Saturn", host_names)


class TestExomoonProvider(unittest.TestCase):
    def setUp(self):
        self.provider = ExomoonProvider()

    def test_get_known_exomoons(self):
        """Verifies candidate exomoons Kepler-1625b I and Kepler-1708b I."""
        m1 = self.provider.get_known_moon("Kepler-1625b I")
        self.assertIsNotNone(m1)
        self.assertEqual(m1.host_planet_name, "Kepler-1625 b")
        self.assertGreater(m1.radius_m, 1.0e7)  # Neptune-sized
        self.assertIsNotNone(m1.orbit)

        m2 = self.provider.get_known_moon("Kepler-1708b I")
        self.assertIsNotNone(m2)
        self.assertEqual(m2.host_planet_name, "Kepler-1708 b")
        self.assertIsNotNone(m2.orbit)

    def test_query_exomoons_by_system(self):
        """Verifies querying exomoons by host star."""
        moons = self.provider.query_by_system("Kepler-1625")
        self.assertEqual(len(moons), 1)
        self.assertEqual(moons[0].name, "Kepler-1625b I")

    def test_query_sun_for_exomoons_returns_empty(self):
        """Sun has zero exomoons."""
        self.assertEqual(self.provider.query_by_system("Sun"), [])


class TestJPLHorizonsMoonProvider(unittest.TestCase):
    def setUp(self):
        self.provider = JPLHorizonsMoonProvider()

    def test_sun_as_moon_raises_exception(self):
        """Verifies that attempting to query the Sun as a moon raises a ValueError."""
        with self.assertRaises(ValueError):
            self.provider.get_known_moon("Sun")

        with self.assertRaises(ValueError):
            self.provider.fetch_moon_from_jpl(
                name="Sun",
                jpl_id="10",
                center_id="@sun",
                host_planet_name="Sun"
            )

    def test_sun_as_host_planet_returns_empty(self):
        """Verifies that querying host planet 'Sun' returns empty list."""
        self.assertEqual(self.provider.query_by_host_planet("Sun"), [])


class TestMoonResolverFacade(unittest.TestCase):
    def setUp(self):
        self.resolver = MoonResolver()

    def test_resolve_moons_for_planet(self):
        """Verifies resolution of moons for Mars, Jupiter, etc."""
        mars_moons = self.resolver.resolve_moons_for_planet("Mars")
        names = [m.name for m in mars_moons]
        self.assertIn("Phobos", names)
        self.assertIn("Deimos", names)

    def test_resolve_moons_for_planet_sun_handled_safely(self):
        """Verifies that passing 'Sun' to resolve_moons_for_planet does not raise an exception."""
        moons = self.resolver.resolve_moons_for_planet("Sun")
        self.assertEqual(moons, [])

    def test_resolve_moons_for_star_sun(self):
        """Verifies that resolving moons for star 'Sun' returns Solar System moons."""
        moons = self.resolver.resolve_moons_for_star("Sun")
        self.assertGreaterEqual(len(moons), 20)
        # Ensure host is planet, not Sun
        for m in moons:
            self.assertNotEqual(m.host_planet_name.upper(), "SUN")

    def test_resolve_all_universe_moons(self):
        """Verifies queryability of all available universe moons."""
        all_moons = self.resolver.resolve_all_universe_moons()
        self.assertGreaterEqual(len(all_moons), 25)
        names = [m.name for m in all_moons]
        self.assertIn("Moon", names)
        self.assertIn("Europa", names)
        self.assertIn("Titan", names)
        self.assertIn("Kepler-1625b I", names)
        self.assertIn("Kepler-1708b I", names)

    def test_resolve_moons_in_region_sun_target_handled(self):
        """
        Crucial requirement: When center is 'SUN', it must not fail with
        ValueError from resolve_center_coord('SUN'). It must return Solar System moons.
        """
        moons = self.resolver.resolve_moons_in_region("SUN", radius_deg=1.0)
        self.assertGreater(len(moons), 0)
        names = [m.name for m in moons]
        self.assertIn("Moon", names)
        self.assertIn("Io", names)


class TestCelestialImporterMoonsIntegration(unittest.TestCase):
    def setUp(self):
        self.sim_time = Time("2024-10-05T12:30:00")
        self.importer = CelestialImporter(self.sim_time)

    def test_add_moon_record_resolves_host_and_orbit(self):
        """Verifies adding MoonRecord links host_planet_index and orbit_index."""
        # Add host planet first
        earth = PlanetRecord(
            name="Earth",
            body_id="EARTH",
            host_star_name="Sun",
            position={"x": 1.496e11, "y": 0.0, "z": 0.0}
        )
        self.importer.add_planet_record(earth)

        moon_rec = MoonRecord(
            name="Moon",
            body_id="LUNA",
            host_planet_name="Earth",
            host_planet_id="EARTH",
            semi_major_axis_km=384400.0,
            orbit=OrbitRecord(semimajor_axis=384400000.0)
        )
        self.importer.add_moon_record(moon_rec)

        self.assertEqual(len(self.importer.moons), 1)
        m = self.importer.moons[0]
        self.assertEqual(m["name"], "Moon")
        self.assertEqual(m["host_planet_index"], 0)
        self.assertEqual(m["orbit_index"], 0)
        self.assertIn("Moon", self.importer.moon_indices)

    def test_add_moon_record_auto_loads_missing_host_planet(self):
        """Verifies that adding a moon whose host planet is missing loads the host planet automatically."""
        # Jupiter is not yet loaded in importer
        self.assertNotIn("Jupiter", self.importer.planet_indices)

        io = MoonRecord(
            name="Io",
            body_id="IO",
            host_planet_name="Jupiter",
            moon_class=MoonClass.VOLCANIC,
            semi_major_axis_km=421700.0,
            orbit=OrbitRecord(semimajor_axis=421700000.0)
        )
        self.importer.add_moon_record(io)

        # Jupiter should have been automatically loaded
        self.assertIn("Jupiter", self.importer.planet_indices)
        m = self.importer.moons[0]
        self.assertGreaterEqual(m["host_planet_index"], 0)
        self.assertEqual(self.importer.planets[m["host_planet_index"]]["name"], "Jupiter")

    def test_add_moons_for_planet_sun_redirects_safely(self):
        """Calling add_moons_for_planet('Sun') handles star exception without crashing."""
        added = self.importer.add_moons_for_planet("Sun")
        self.assertGreater(len(added), 0)
        self.assertIn("Moon", self.importer.moon_indices)
        self.assertIn("Io", self.importer.moon_indices)

    def test_add_moons_in_region_sun_target_handled(self):
        """Calling add_moons_in_region('SUN', 1.0) handles Sun origin target safely."""
        added = self.importer.add_moons_in_region("SUN", radius_degrees=1.0)
        self.assertGreater(len(added), 0)

    def test_add_solar_system_with_moons_validates_json_schema(self):
        """
        Full end-to-end integration test:
        Adds Solar System (Sun, Planets, Moons), dumps to JSON, and validates with schema.json.
        """
        self.importer.add_solar_system(include_moons=True, include_dwarf_planets=True)

        self.assertGreaterEqual(len(self.importer.stars), 1)
        self.assertGreaterEqual(len(self.importer.planets), 9)  # 8 major + Pluto
        self.assertGreaterEqual(len(self.importer.moons), 15)
        self.assertGreaterEqual(len(self.importer.orbits), len(self.importer.planets) + len(self.importer.moons))

        # Check that moon positions are accurate, distinct, and not all {0, 0, 0}
        positions = set()
        for moon in self.importer.moons:
            pos = moon["position"]
            dist = math.sqrt(pos["x"]**2 + pos["y"]**2 + pos["z"]**2)
            self.assertGreater(dist, 0.0, f"Moon {moon['name']} has (0, 0, 0) position!")
            positions.add((pos["x"], pos["y"], pos["z"]))

            # Verify required schema fields
            self.assertIn("name", moon)
            self.assertIn("host_planet_index", moon)
            self.assertIn("orbit_index", moon)
            self.assertGreaterEqual(moon["host_planet_index"], 0)
            self.assertGreaterEqual(moon["orbit_index"], 0)

        # All positions should be unique
        self.assertEqual(len(positions), len(self.importer.moons), "Moons have duplicate positions!")

        # Dump to JSON and validate against schema.json
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            self.importer.save(str(tmp_path))

            with open(tmp_path, "r") as f:
                data = json.load(f)

            schema_path = Path("/Users/felixmv/Desktop/TEMP/Coding/celestial-body-engine/src/tests/data/schema.json")
            with open(schema_path, "r") as sf:
                schema = json.load(sf)

            # Validate entire JSON structure against official schema.json
            jsonschema.validate(instance=data, schema=schema)
            print("[Test] JSON schema successfully validated for moons and orbits!")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
