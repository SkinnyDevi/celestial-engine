#include "core/space/orbit.h"
#include <criterion/criterion.h>
#include <math.h>

Test(orbit_suite, test_circular_orbit) {
  CelestialBody_Orbit orbit = {0};
  orbit.semimajor_axis = 1.0;
  orbit.eccentricity = 0.0;
  orbit.inclination = 0.0;
  orbit.longitude_of_ascending_node = 0.0;
  orbit.argument_of_periapsis = 0.0;
  orbit.mean_anomaly_at_epoch = 0.0;
  orbit.orbital_period_days = 365.25;
  orbit.center_position = (Vector3){0.0, 0.0, 0.0};

  // At t=0, mean anomaly = 0, true anomaly = 0
  Vector3 pos = orbit_calculate_position(&orbit, 0.0);
  cr_assert_float_eq(pos.x, 1.0, 1e-5,
                     "Circular orbit X position at t=0 should be 1.0, got %f",
                     pos.x);
  cr_assert_float_eq(pos.y, 0.0, 1e-5,
                     "Circular orbit Y position at t=0 should be 0.0, got %f",
                     pos.y);
  cr_assert_float_eq(pos.z, 0.0, 1e-5,
                     "Circular orbit Z position at t=0 should be 0.0, got %f",
                     pos.z);

  // At t = period/4, mean anomaly = PI/2, true anomaly = PI/2 (since e=0)
  pos = orbit_calculate_position(&orbit, 365.25 / 4.0);
  cr_assert_float_eq(
      pos.x, 0.0, 1e-5,
      "Circular orbit X position at t=period/4 should be 0.0, got %f", pos.x);
  cr_assert_float_eq(
      pos.y, 0.0, 1e-5,
      "Circular orbit Y position at t=period/4 should be 0.0, got %f", pos.y);
  cr_assert_float_eq(
      pos.z, 1.0, 1e-5,
      "Circular orbit Z position at t=period/4 should be 1.0, got %f", pos.z);
}

Test(orbit_suite, test_kepler_equation_eccentric) {
  CelestialBody_Orbit orbit = {0};
  orbit.semimajor_axis = 2.0;
  orbit.eccentricity = 0.5;
  orbit.inclination = 0.0;
  orbit.longitude_of_ascending_node = 0.0;
  orbit.argument_of_periapsis = 0.0;
  orbit.mean_anomaly_at_epoch = 0.0;
  orbit.orbital_period_days = 100.0;
  orbit.center_position = (Vector3){0.0, 0.0, 0.0};

  // At t=0, at periapsis. r = a(1-e) = 2(1-0.5) = 1.0
  Vector3 pos = orbit_calculate_position(&orbit, 0.0);
  cr_assert_float_eq(pos.x, 1.0, 1e-5,
                     "Eccentric orbit X position at periapsis should be 1.0");
  cr_assert_float_eq(pos.y, 0.0, 1e-5);
  cr_assert_float_eq(pos.z, 0.0, 1e-5);

  // At t=period/2 (50 days), at apoapsis. r = a(1+e) = 2(1.5) = 3.0
  // Since it's apoapsis, x_prime = -3.0
  pos = orbit_calculate_position(&orbit, 50.0);
  cr_assert_float_eq(
      pos.x, -3.0, 1e-5,
      "Eccentric orbit X position at apoapsis should be -3.0, got %f", pos.x);
  cr_assert_float_eq(pos.y, 0.0, 1e-5);
  cr_assert_float_eq(
      pos.z, 0.0, 1e-5,
      "Eccentric orbit Z position at apoapsis should be 0.0, got %f", pos.z);
}

Test(orbit_suite, test_orbit_get_ellipse_vector) {
  CelestialBody_Orbit orbit = {0};
  orbit.semimajor_axis = 5.0;
  orbit.eccentricity = 0.6;
  orbit.inclination = 0.0;
  orbit.longitude_of_ascending_node = 0.0;
  orbit.argument_of_periapsis = 0.0;
  orbit.center_position = (Vector3){0.0, 0.0, 0.0};

  // b = a * sqrt(1 - e^2) = 5 * sqrt(1 - 0.36) = 5 * 0.8 = 4.0
  // For Omega = 0, vector is (a, 0, 0)
  Vector3 vec = orbit_get_ellipse_vector(&orbit);
  cr_assert_float_eq(vec.x, 5.0, 1e-5);
  cr_assert_float_eq(vec.y, 0.0, 1e-5);
  cr_assert_float_eq(vec.z, 0.0, 1e-5);

  orbit.longitude_of_ascending_node = M_PI / 2.0;
  vec = orbit_get_ellipse_vector(&orbit);
  // vector should be (a*cos(Omega), b*sin(Omega), 0) -> (0, 4.0, 0)
  cr_assert_float_eq(vec.x, 0.0, 1e-5);
  cr_assert_float_eq(vec.y, 4.0, 1e-5);
  cr_assert_float_eq(vec.z, 0.0, 1e-5);
}

Test(orbit_suite, test_inclination) {
  CelestialBody_Orbit orbit = {0};
  orbit.semimajor_axis = 1.0;
  orbit.eccentricity = 0.0;
  orbit.inclination = M_PI / 2.0; // 90 degrees
  orbit.longitude_of_ascending_node = 0.0;
  orbit.argument_of_periapsis = 0.0;
  orbit.mean_anomaly_at_epoch = 0.0;
  orbit.orbital_period_days = 365.25;
  orbit.center_position = (Vector3){0.0, 0.0, 0.0};

  // At t=period/4, true anomaly is PI/2
  // x_prime = 0, y_prime = 1.0
  // For i=90 degrees, sin_i=1, cos_i=0
  // x_astronomy = 0
  // y_astronomy = 0
  // z_astronomy = y_prime * sin_i = 1.0
  // Engine mapping: pos.x = x_astronomy, pos.y = z_astronomy, pos.z =
  // y_astronomy So pos.x = 0, pos.y = 1.0, pos.z = 0.0
  Vector3 pos = orbit_calculate_position(&orbit, 365.25 / 4.0);
  cr_assert_float_eq(pos.x, 0.0, 1e-5);
  cr_assert_float_eq(pos.y, 1.0, 1e-5);
  cr_assert_float_eq(pos.z, 0.0, 1e-5);
}
