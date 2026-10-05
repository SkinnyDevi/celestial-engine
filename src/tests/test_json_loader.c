#include "core/data/loader/json/json_data_loader.h"
#include <criterion/criterion.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

Test(json_loader_suite, test_missing_file) {
  LoadedSimulationBodies *bodies = json_load("non_existent_file_12345.json");
  cr_assert_null(bodies,
                 "Loading a non-existent file should return NULL gracefully");
}

Test(json_loader_suite, test_malformed_json) {
  const char *filename = "test_malformed.json";
  FILE *f = fopen(filename, "w");
  // Malformed JSON (missing closing braces/brackets)
  fputs("{ \"planets\": [ { \"name\": \"Earth\" ", f);
  fclose(f);

  LoadedSimulationBodies *bodies = json_load(filename);
  cr_assert_null(
      bodies,
      "Loading malformed JSON should return NULL gracefully without crashing");
  remove(filename);
}

Test(json_loader_suite, test_invalid_types) {
  const char *filename = "test_invalid_types.json";
  FILE *f = fopen(filename, "w");
  // JSON is syntactically valid, but schema types are wrong: name is int,
  // eccentricity is string
  fputs("{ \"planets\": [ { \"name\": 123, \"eccentricity\": "
        "\"very_eccentric\" } ] }",
        f);
  fclose(f);

  LoadedSimulationBodies *bodies = json_load(filename);
  cr_assert_not_null(bodies,
                     "Syntactically valid JSON should parse successfully");
  cr_assert_eq(bodies->num_planets, 1, "Should parse 1 planet");

  // Assert fallback logic kicks in
  cr_assert_str_empty(
      bodies->planets[0].name,
      "Name should fallback to empty string if it's not a string in JSON");
  cr_assert_float_eq(
      bodies->planets[0].eccentricity, 0.0, 1e-5,
      "Eccentricity should fallback to 0.0 if not a number in JSON");

  free(bodies->planets);
  free(bodies);
  remove(filename);
}

Test(json_loader_suite, test_save_and_load_state) {
  const char *filename = "test_save_load.json";

  LoadedSimulationBodies original = {0};
  original.num_planets = 1;
  original.planets = calloc(1, sizeof(CelestialBody_Planet));
  strcpy(original.planets[0].name, "Mars");
  strcpy(original.planets[0].body_id, "mars_1");
  original.planets[0].mass_kg = 6.39e23;
  original.planets[0].position.x = 1.5;
  original.planets[0].position.y = 0.0;
  original.planets[0].position.z = -0.5;

  bool saved = json_save(filename, &original);
  cr_assert(saved, "Failed to serialize and save valid simulation state");

  LoadedSimulationBodies *loaded = json_load(filename);
  cr_assert_not_null(loaded, "Failed to load saved state");
  cr_assert_eq(loaded->num_planets, 1);
  cr_assert_str_eq(loaded->planets[0].name, "Mars");
  cr_assert_str_eq(loaded->planets[0].body_id, "mars_1");
  // Using a large epsilon for mass because of floating point imprecision at
  // such large exponents
  cr_assert_float_eq(loaded->planets[0].mass_kg, 6.39e23, 1e18);
  cr_assert_float_eq(loaded->planets[0].position.x, 1.5, 1e-5);
  cr_assert_float_eq(loaded->planets[0].position.z, -0.5, 1e-5);

  free(original.planets);
  free(loaded->planets);
  free(loaded);
  remove(filename);
}
