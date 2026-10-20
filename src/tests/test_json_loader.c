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

Test(json_loader_suite, test_load_all_planet_types) {
  const char *filename = "test_all_planets.json";
  FILE *f = fopen(filename, "w");
  cr_assert_not_null(f, "Failed to create temp test file");

  fputs("{\n"
        "  \"sim_date\": {\"year\": 2024, \"month\": 10, \"day\": 5, \"hour\": 12, \"minute\": 0, \"second\": 0},\n"
        "  \"stars\": [\n"
        "    {\"name\": \"Sun\", \"body_id\": \"SUN\", \"spectral_type\": 4, \"position\": {\"x\": 0, \"y\": 0, \"z\": 0}}\n"
        "  ],\n"
        "  \"orbits\": [\n"
        "    {\"semimajor_axis\": 149597870700.0, \"eccentricity\": 0.0167, \"orbital_period_days\": 365.25}\n"
        "  ],\n"
        "  \"planets\": [\n"
        "    {\n"
        "      \"name\": \"Earth\", \"body_id\": \"EARTH\", \"host_star_index\": 0, \"orbit_index\": 0,\n"
        "      \"planet_class\": 0, \"atmosphere_type\": 2, \"mass_kg\": 5.972e24, \"radius_m\": 6371000.0\n"
        "    },\n"
        "    {\n"
        "      \"name\": \"Jupiter\", \"body_id\": \"JUPITER\", \"host_star_index\": 0, \"orbit_index\": 0,\n"
        "      \"planet_class\": 1, \"atmosphere_type\": 4, \"mass_kg\": 1.898e27, \"radius_m\": 69911000.0, \"has_rings\": 1\n"
        "    },\n"
        "    {\n"
        "      \"name\": \"Neptune\", \"body_id\": \"NEPTUNE\", \"host_star_index\": 0, \"orbit_index\": 0,\n"
        "      \"planet_class\": 2, \"atmosphere_type\": 4, \"mass_kg\": 1.024e26, \"radius_m\": 24622000.0\n"
        "    },\n"
        "    {\n"
        "      \"name\": \"Pluto\", \"body_id\": \"PLUTO\", \"host_star_index\": 0, \"orbit_index\": 0,\n"
        "      \"planet_class\": 3, \"atmosphere_type\": 1, \"mass_kg\": 1.303e22, \"radius_m\": 1188300.0\n"
        "    },\n"
        "    {\n"
        "      \"name\": \"PSO J318.5-22\", \"body_id\": \"PSO_J318_5_22\", \"host_star_index\": -1, \"orbit_index\": -1,\n"
        "      \"planet_class\": 4, \"atmosphere_type\": 4, \"mass_kg\": 1.2e28, \"radius_m\": 1.07e8,\n"
        "      \"position\": {\"x\": 1e16, \"y\": 2e16, \"z\": -1e16}\n"
        "    }\n"
        "  ],\n"
        "  \"moons\": []\n"
        "}\n", f);
  fclose(f);

  LoadedSimulationBodies *bodies = json_load(filename);
  cr_assert_not_null(bodies, "Failed to parse JSON with all planet types");
  cr_assert_eq(DynamicArray_length(&bodies->planets), 5, "Expected 5 planets to be parsed");

  // 1. Earth (Terrestrial)
  CelestialBody_Planet *p_earth = NULL;
  DynamicArray_get(&bodies->planets, 0, &p_earth);
  cr_assert_not_null(p_earth);
  cr_assert_str_eq(p_earth->name, "Earth");
  cr_assert_str_eq(p_earth->host_star_id, "SUN");
  cr_assert_eq(p_earth->planet_class, PLANET_CLASS_TERRESTRIAL);
  cr_assert_eq(p_earth->atmosphere_type, ATMOSPHERE_STANDARD);
  cr_assert_not_null(p_earth->orbit);

  // 2. Jupiter (Gas Giant)
  CelestialBody_Planet *p_jup = NULL;
  DynamicArray_get(&bodies->planets, 1, &p_jup);
  cr_assert_not_null(p_jup);
  cr_assert_str_eq(p_jup->name, "Jupiter");
  cr_assert_eq(p_jup->planet_class, PLANET_CLASS_GAS_GIANT);
  cr_assert_eq(p_jup->has_rings, 1);

  // 3. Neptune (Ice Giant)
  CelestialBody_Planet *p_nep = NULL;
  DynamicArray_get(&bodies->planets, 2, &p_nep);
  cr_assert_not_null(p_nep);
  cr_assert_str_eq(p_nep->name, "Neptune");
  cr_assert_eq(p_nep->planet_class, PLANET_CLASS_ICE_GIANT);

  // 4. Pluto (Dwarf)
  CelestialBody_Planet *p_pluto = NULL;
  DynamicArray_get(&bodies->planets, 3, &p_pluto);
  cr_assert_not_null(p_pluto);
  cr_assert_str_eq(p_pluto->name, "Pluto");
  cr_assert_eq(p_pluto->planet_class, PLANET_CLASS_DWARF);

  // 5. Rogue Planet (No host, no orbit)
  CelestialBody_Planet *p_rogue = NULL;
  DynamicArray_get(&bodies->planets, 4, &p_rogue);
  cr_assert_not_null(p_rogue);
  cr_assert_str_eq(p_rogue->name, "PSO J318.5-22");
  cr_assert_eq(p_rogue->planet_class, PLANET_CLASS_ROGUE);
  cr_assert_str_empty(p_rogue->host_star_id, "Rogue planet should have empty host_star_id");
  cr_assert_null(p_rogue->orbit, "Rogue planet should not have an orbit");
  cr_assert_float_eq(p_rogue->position.x, 1e16, 1e10);

  loaded_simulation_bodies_free(bodies);
  free(bodies);
  remove(filename);
}
