import unittest
import math
import astropy.units as astrounits
from astropy.coordinates import SkyCoord, Distance

from core.catalogs import (
    CatalogSource,
    DistanceMethod,
    StarRecord,
    PreciseDistanceResolver,
    create_skycoord_3d,
    skycoord_to_cartesian_meters,
    distance_from_parallax,
    distance_from_pc,
    distance_from_kpc,
    is_dusty_or_dense_region,
    classify_spectral_type,
)
from core.space import SpectralType
from core.constants import PC_TO_METERS, DEG_TO_RAD

class TestPreciseDistances(unittest.TestCase):
    def test_cartesian_mapping_accuracy(self):
        """Verifies that Astropy SkyCoord cartesian coordinates match mathematical spherical projections."""
        ra_deg = 45.0
        dec_deg = 30.0
        dist_pc = 100.0

        sc = create_skycoord_3d(ra_deg, dec_deg, dist_pc)
        cart = skycoord_to_cartesian_meters(sc)

        expected_dist_m = dist_pc * PC_TO_METERS
        ra_rad = ra_deg * DEG_TO_RAD
        dec_rad = dec_deg * DEG_TO_RAD
        expected_x = expected_dist_m * math.cos(dec_rad) * math.cos(ra_rad)
        expected_y = expected_dist_m * math.cos(dec_rad) * math.sin(ra_rad)
        expected_z = expected_dist_m * math.sin(dec_rad)

        self.assertAlmostEqual(cart["x"], expected_x, delta=abs(expected_x) * 1e-6)
        self.assertAlmostEqual(cart["y"], expected_y, delta=abs(expected_y) * 1e-6)
        self.assertAlmostEqual(cart["z"], expected_z, delta=abs(expected_z) * 1e-6)

    def test_distance_from_parallax_positive(self):
        """Verifies parallax inversion with Astropy Distance for positive parallax."""
        plx_mas = 10.0  # 10 mas = 100 pc
        e_plx_mas = 1.0  # 1 mas error -> lower 1000/11 = 90.9 pc, upper 1000/9 = 111.1 pc

        res = distance_from_parallax(plx_mas, e_plx_mas, source=CatalogSource.GAIA_DR3)
        self.assertTrue(res.is_valid)
        self.assertAlmostEqual(res.distance_pc, 100.0, places=3)
        self.assertAlmostEqual(res.distance_error_lower_pc, 1000.0 / 11.0, places=2)
        self.assertAlmostEqual(res.distance_error_upper_pc, 1000.0 / 9.0, places=2)
        self.assertAlmostEqual(res.distance_m, 100.0 * PC_TO_METERS, delta=100.0 * PC_TO_METERS * 1e-6)

    def test_distance_from_parallax_negative_or_zero(self):
        """Verifies that non-positive parallax is safely flagged without raising ValueError."""
        res_neg = distance_from_parallax(-2.5, fallback_pc=500.0)
        self.assertFalse(res_neg.is_valid)
        self.assertEqual(res_neg.distance_pc, 500.0)

        res_zero = distance_from_parallax(0.0)
        self.assertFalse(res_zero.is_valid)
        self.assertEqual(res_zero.distance_pc, 0.0)

    def test_starhorse_kpc_conversion(self):
        """Verifies StarHorse dist50 in kpc is properly converted to parsecs and meters."""
        dist_kpc = 2.5  # 2.5 kpc = 2500 pc
        res = distance_from_kpc(dist_kpc=dist_kpc, method=DistanceMethod.STELLAR_MODELS, source=CatalogSource.STARHORSE)
        self.assertTrue(res.is_valid)
        self.assertAlmostEqual(res.distance_pc, 2500.0, places=2)
        self.assertAlmostEqual(res.distance_kpc, 2.5, places=3)
        self.assertAlmostEqual(res.distance_m, 2500.0 * PC_TO_METERS, delta=2500.0 * PC_TO_METERS * 1e-6)

    def test_bailer_jones_error_percentiles(self):
        """Verifies Bailer-Jones 16th and 84th percentile bounds."""
        res = distance_from_pc(
            dist_pc=350.0,
            lower_pc=330.0,
            upper_pc=375.0,
            method=DistanceMethod.BAYESIAN_PHOTOGEOMETRIC,
            source=CatalogSource.BAILER_JONES
        )
        self.assertTrue(res.is_valid)
        self.assertEqual(res.distance_pc, 350.0)
        self.assertEqual(res.distance_error_lower_pc, 330.0)
        self.assertEqual(res.distance_error_upper_pc, 375.0)

    def test_galactic_plane_detection(self):
        """Verifies detection of dense/dusty galactic plane regions (|b| <= 10 deg)."""
        # Galactic center (Sgr A*) is in the galactic plane
        coord_gc = SkyCoord(ra=266.4168 * astrounits.deg, dec=-29.0078 * astrounits.deg, frame='icrs')
        self.assertTrue(is_dusty_or_dense_region(coord_gc, latitude_threshold_deg=10.0))

        # North Galactic Pole (b ~ 90 deg) is outside galactic plane
        coord_ngp = SkyCoord(ra=192.859 * astrounits.deg, dec=27.128 * astrounits.deg, frame='icrs')
        self.assertFalse(is_dusty_or_dense_region(coord_ngp, latitude_threshold_deg=10.0))

class TestPreciseDistanceResolver(unittest.TestCase):
    def setUp(self):
        self.resolver = PreciseDistanceResolver()

    def test_auto_routing_bright_star(self):
        """Bright stars (m < 6.0) should route to Hipparcos to avoid Gaia saturation."""
        coord = SkyCoord(ra=10.0 * astrounits.deg, dec=20.0 * astrounits.deg, frame='icrs')
        chosen_source = self.resolver.select_best_source(coord, apparent_mag=4.5)
        self.assertEqual(chosen_source, CatalogSource.HIPPARCOS)

    def test_auto_routing_dusty_dense_region(self):
        """Objects in the dusty Galactic plane (|b| <= 10 deg) should route to StarHorse."""
        coord_plane = SkyCoord(ra=266.4168 * astrounits.deg, dec=-29.0078 * astrounits.deg, frame='icrs')
        chosen_source = self.resolver.select_best_source(coord_plane, apparent_mag=12.0)
        self.assertEqual(chosen_source, CatalogSource.STARHORSE)

    def test_auto_routing_general_stars(self):
        """General stars outside the plane should route to Bailer-Jones to prevent line-of-sight stretching."""
        coord_high_b = SkyCoord(ra=192.859 * astrounits.deg, dec=27.128 * astrounits.deg, frame='icrs')
        chosen_source = self.resolver.select_best_source(coord_high_b, apparent_mag=12.0)
        self.assertEqual(chosen_source, CatalogSource.BAILER_JONES)

    def test_star_record_engine_dict_schema(self):
        """Verifies StarRecord to_engine_dict satisfies required format."""
        dist_res = distance_from_pc(250.0, lower_pc=240.0, upper_pc=260.0)
        sc = create_skycoord_3d(10.0, 20.0, 250.0)
        cart = skycoord_to_cartesian_meters(sc)

        rec = StarRecord(
            name="Vega",
            body_id="VEGA",
            ra_deg=10.0,
            dec_deg=20.0,
            distance=dist_res,
            apparent_magnitude=0.03,
            magnitude_band="V",
            spectral_type=SpectralType.A,
            spectral_subtype=0,
            surface_temperature_k=9602.0,
            cartesian_position_m=cart
        )

        d = rec.to_engine_dict()
        self.assertEqual(d["name"], "Vega")
        self.assertEqual(d["body_id"], "VEGA")
        self.assertEqual(d["spectral_type"], 2)  # A = 2
        self.assertEqual(d["spectral_subtype"], 0)
        self.assertEqual(d["distance_pc"], 250.0)
        self.assertIn("x", d["position"])
        self.assertIn("y", d["position"])
        self.assertIn("z", d["position"])
        self.assertEqual(d["apparent_magnitude"], 0.03)
        self.assertEqual(d["surface_temperature_k"], 9602.0)

    def test_spectral_classification_from_mk_str(self):
        """Verifies parsing of MK spectral strings into SpectralType and subtypes."""
        stype, sub, teff = classify_spectral_type(sp_str="G2V")
        self.assertEqual(stype, SpectralType.G)
        self.assertEqual(sub, 2)
        self.assertAlmostEqual(teff, 5778.0, delta=100.0)

        stype_m, sub_m, _ = classify_spectral_type(sp_str="M5.5")
        self.assertEqual(stype_m, SpectralType.M)
        self.assertEqual(sub_m, 6)

        stype_b, sub_b, _ = classify_spectral_type(sp_str="B0III")
        self.assertEqual(stype_b, SpectralType.B)
        self.assertEqual(sub_b, 0)

    def test_spectral_classification_from_teff(self):
        """Verifies mapping of stellar effective temperatures (Teff) to Morgan-Keenan classes."""
        # Solar temperature 5778 K -> G2
        stype_sun, sub_sun, _ = classify_spectral_type(teff_k=5778.0)
        self.assertEqual(stype_sun, SpectralType.G)
        self.assertEqual(sub_sun, 2)

        # Hot O-type star (40,000 K) -> O4
        stype_o, sub_o, _ = classify_spectral_type(teff_k=40000.0)
        self.assertEqual(stype_o, SpectralType.O)

        # Cool M-type dwarf (3000 K) -> M5
        stype_m, sub_m, _ = classify_spectral_type(teff_k=3000.0)
        self.assertEqual(stype_m, SpectralType.M)
        self.assertEqual(sub_m, 5)

        # Vega-like A-type star (9600 K) -> A1
        stype_a, sub_a, _ = classify_spectral_type(teff_k=9600.0)
        self.assertEqual(stype_a, SpectralType.A)

    def test_spectral_classification_from_color(self):
        """Verifies derivation of spectral types and temperatures from photometric colors."""
        # Solar-like color (BP - RP ~ 0.82)
        stype_g, sub_g, teff_g = classify_spectral_type(bp_rp=0.82)
        self.assertEqual(stype_g, SpectralType.G)
        self.assertAlmostEqual(teff_g, 5817.0, delta=50.0)

        # White/A-type star (BP - RP = 0.1) -> A3
        stype_a, _, teff_a = classify_spectral_type(bp_rp=0.1)
        self.assertEqual(stype_a, SpectralType.A)
        self.assertAlmostEqual(teff_a, 9246.0, delta=100.0)

        # Hot blue star (BP - RP = -0.1) -> B-type
        stype_b, _, teff_b = classify_spectral_type(bp_rp=-0.1)
        self.assertEqual(stype_b, SpectralType.B)
        self.assertGreater(teff_b, 10000.0)

    def test_star_record_engine_dict_auto_infers_spectral_type(self):
        """Verifies that StarRecord.to_engine_dict() guarantees spectral_type and spectral_subtype are never omitted."""
        dist_res = distance_from_pc(10.0)
        rec = StarRecord(
            name="Unclassified Star",
            body_id="UNCLASSIFIED",
            ra_deg=45.0,
            dec_deg=10.0,
            distance=dist_res,
            surface_temperature_k=3100.0  # M dwarf temperature, but no spectral_type set
        )
        # to_engine_dict() must auto-infer and include spectral_type and spectral_subtype
        d = rec.to_engine_dict()
        self.assertIn("spectral_type", d)
        self.assertEqual(d["spectral_type"], SpectralType.M.value)
        self.assertIn("spectral_subtype", d)
        self.assertIn("surface_temperature_k", d)
        self.assertEqual(d["surface_temperature_k"], 3100.0)

if __name__ == "__main__":
    unittest.main()
