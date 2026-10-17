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
  cr_assert_eq(DynamicArray_length(&bodies->planets), 1, "Should parse 1 planet");

  CelestialBody_Planet *planet = NULL;
  DynamicArray_get(&bodies->planets, 0, &planet);
  cr_assert_not_null(planet);

  // Assert fallback logic kicks in
  cr_assert_str_empty(
      planet->name,
      "Name should fallback to empty string if it's not a string in JSON");
  cr_assert_float_eq(
      planet->eccentricity, 0.0, 1e-5,
      "Eccentricity should fallback to 0.0 if not a number in JSON");

  loaded_simulation_bodies_free(bodies);
  free(bodies);
  remove(filename);
}

Test(json_loader_suite, test_save_and_load_state) {
  const char *filename = "test_save_load.json";

  LoadedSimulationBodies original;
  loaded_simulation_bodies_init(&original);

  CelestialBody_Planet *p = calloc(1, sizeof(CelestialBody_Planet));
  strcpy(p->name, "Mars");
  strcpy(p->body_id, "mars_1");
  p->mass_kg = 6.39e23;
  p->position.x = 1.5;
  p->position.y = 0.0;
  p->position.z = -0.5;
  DynamicArray_push(&original.planets, &p);

  bool saved = json_save(filename, &original);
  cr_assert(saved, "Failed to serialize and save valid simulation state");

  LoadedSimulationBodies *loaded = json_load(filename);
  cr_assert_not_null(loaded, "Failed to load saved state");
  cr_assert_eq(DynamicArray_length(&loaded->planets), 1);

  CelestialBody_Planet *loaded_planet = NULL;
  DynamicArray_get(&loaded->planets, 0, &loaded_planet);
  cr_assert_not_null(loaded_planet);

  cr_assert_str_eq(loaded_planet->name, "Mars");
  cr_assert_str_eq(loaded_planet->body_id, "mars_1");
  // Using a large epsilon for mass because of floating point imprecision at
  // such large exponents
  cr_assert_float_eq(loaded_planet->mass_kg, 6.39e23, 1e18);
  cr_assert_float_eq(loaded_planet->position.x, 1.5, 1e-5);
  cr_assert_float_eq(loaded_planet->position.z, -0.5, 1e-5);

  loaded_simulation_bodies_free(&original);
  loaded_simulation_bodies_free(loaded);
  free(loaded);
  remove(filename);
}
