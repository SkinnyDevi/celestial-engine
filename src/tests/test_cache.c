#include "core/data/loader/cache/cache_data_loader.h"
#include "core/data/loader/cache/cache_header.h"
#include "core/data/loader/data_loader.h"

#include "core/space/moon.h"
#include "core/space/orbit.h"
#include "core/space/planet.h"
#include "core/space/star.h"

#include <criterion/criterion.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

Test(cache_suite, test_roundtrip_data_integrity) {
  LoadedSimulationBodies original;
  loaded_simulation_bodies_init(&original);

  original.sim_date.has_set_date = true;
  original.sim_date.time.tm_year = 2026 - 1900;
  original.sim_date.time.tm_mon = 9;
  original.sim_date.time.tm_mday = 22;

  // 1. Create Orbit
  CelestialBody_Orbit *orig_orbit = calloc(1, sizeof(CelestialBody_Orbit));
  orig_orbit->semimajor_axis = 1.496e11;
  orig_orbit->eccentricity = 0.0167;
  orig_orbit->inclination = 0.00005;
  orig_orbit->center_position = (Vector3){10.0, 20.0, 30.0};
  DynamicArray_push(&original.orbits, &orig_orbit);

  // 2. Create Star
  CelestialBody_Star *orig_star = calloc(1, sizeof(CelestialBody_Star));
  strncpy(orig_star->name, "Sol", sizeof(orig_star->name) - 1);
  strncpy(orig_star->body_id, "SUN", sizeof(orig_star->body_id) - 1);
  orig_star->spectral_type = SPECTRAL_CLASS_G;
  orig_star->spectral_subtype = 2;
  orig_star->position = (Vector3){0.0, 0.0, 0.0};
  orig_star->mass_kg = 1.989e30;
  orig_star->radius_m = 6.9634e8;
  DynamicArray_push(&original.stars, &orig_star);

  // 3. Create Planet linking to Orbit
  CelestialBody_Planet *orig_planet = calloc(1, sizeof(CelestialBody_Planet));
  strncpy(orig_planet->name, "Earth", sizeof(orig_planet->name) - 1);
  strncpy(orig_planet->body_id, "EARTH", sizeof(orig_planet->body_id) - 1);
  strncpy(orig_planet->host_star_id, "SUN",
          sizeof(orig_planet->host_star_id) - 1);
  orig_planet->mass_kg = 5.972e24;
  orig_planet->radius_m = 6.371e6;
  orig_planet->orbit = orig_orbit;
  DynamicArray_push(&original.planets, &orig_planet);

  // 4. Create Moon linking to Orbit
  CelestialBody_Moon *orig_moon = calloc(1, sizeof(CelestialBody_Moon));
  strncpy(orig_moon->name, "Moon", sizeof(orig_moon->name) - 1);
  strncpy(orig_moon->body_id, "LUNA", sizeof(orig_moon->body_id) - 1);
  strncpy(orig_moon->host_planet_id, "EARTH",
          sizeof(orig_moon->host_planet_id) - 1);
  orig_moon->mass_kg = 7.342e22;
  orig_moon->radius_m = 1.7374e6;
  orig_moon->orbit = orig_orbit;
  DynamicArray_push(&original.moons, &orig_moon);

  const char *cache_file = "test_roundtrip.cache";
  bool saved = cache_save(cache_file, NULL, &original);
  cr_assert(saved, "Failed to save cache file");

  LoadedSimulationBodies *loaded = cache_load(cache_file);
  cr_assert_not_null(loaded, "Failed to load cache file");

  // Verify counts
  cr_assert_eq(DynamicArray_length(&loaded->orbits), 1);
  cr_assert_eq(DynamicArray_length(&loaded->stars), 1);
  cr_assert_eq(DynamicArray_length(&loaded->planets), 1);
  cr_assert_eq(DynamicArray_length(&loaded->moons), 1);

  // Verify Star fields
  CelestialBody_Star *loaded_star = NULL;
  DynamicArray_get(&loaded->stars, 0, &loaded_star);
  cr_assert_str_eq(loaded_star->name, "Sol");
  cr_assert_str_eq(loaded_star->body_id, "SUN");
  cr_assert_eq(loaded_star->spectral_type, SPECTRAL_CLASS_G);
  cr_assert_float_eq(loaded_star->mass_kg, 1.989e30, 1e20);

  // Verify Orbit fields
  CelestialBody_Orbit *loaded_orbit = NULL;
  DynamicArray_get(&loaded->orbits, 0, &loaded_orbit);
  cr_assert_float_eq(loaded_orbit->semimajor_axis, 1.496e11, 1e5);
  cr_assert_float_eq(loaded_orbit->center_position.x, 10.0, 1e-5);

  // Verify Planet fields & Pointer Re-linking
  CelestialBody_Planet *loaded_planet = NULL;
  DynamicArray_get(&loaded->planets, 0, &loaded_planet);
  cr_assert_str_eq(loaded_planet->name, "Earth");
  cr_assert_not_null(loaded_planet->orbit,
                     "Planet orbit pointer should be re-linked");
  cr_assert_eq(loaded_planet->orbit, loaded_orbit,
               "Planet orbit should point to loaded orbit");

  // Verify Moon fields & Pointer Re-linking
  CelestialBody_Moon *loaded_moon = NULL;
  DynamicArray_get(&loaded->moons, 0, &loaded_moon);
  cr_assert_str_eq(loaded_moon->name, "Moon");
  cr_assert_not_null(loaded_moon->orbit,
                     "Moon orbit pointer should be re-linked");
  cr_assert_eq(loaded_moon->orbit, loaded_orbit,
               "Moon orbit should point to loaded orbit");

  loaded_simulation_bodies_free(&original);
  loaded_simulation_bodies_free(loaded);
  free(loaded);
  remove(cache_file);
}

Test(cache_suite, test_invalidation_on_source_change) {
  const char *source_file = "dummy_source.json";
  FILE *f = fopen(source_file, "w");
  fputs("{}", f);
  fclose(f);

  LoadedSimulationBodies bodies;
  loaded_simulation_bodies_init(&bodies);

  char *cache_file = cache_get_sidecar_path(source_file);
  bool saved = cache_save(cache_file, source_file, &bodies);
  cr_assert(saved, "Cache save should succeed");

  // Should be valid right after saving
  cr_assert(cache_is_valid(source_file, cache_file),
            "Cache should be valid for unmodified source");

  // Modify source file content and size
  usleep(1100000); // Wait > 1 second so mtime increases
  f = fopen(source_file, "w");
  fputs("{\"modified\": true, \"extra\": 123456}", f);
  fclose(f);

  // Cache should now be detected as invalid
  cr_assert_not(cache_is_valid(source_file, cache_file),
                "Cache should be invalidated after source change");

  LoadedSimulationBodies *loaded = cache_load_sidecar_if_valid(source_file);
  cr_assert_null(
      loaded,
      "cache_load_sidecar_if_valid should return NULL when cache is invalid");

  loaded_simulation_bodies_free(&bodies);
  remove(source_file);
  remove(cache_file);
  free(cache_file);
}

Test(cache_suite, test_corruption_crc_rejection) {
  LoadedSimulationBodies bodies;
  loaded_simulation_bodies_init(&bodies);

  CelestialBody_Star *star = calloc(1, sizeof(CelestialBody_Star));
  strncpy(star->name, "Alpha Centauri", sizeof(star->name) - 1);
  DynamicArray_push(&bodies.stars, &star);

  const char *cache_file = "test_corrupt.cache";
  cr_assert(cache_save(cache_file, NULL, &bodies), "Failed to save test cache");

  // Corrupt a byte in the payload
  FILE *f = fopen(cache_file, "r+b");
  cr_assert_not_null(f);
  fseek(f, sizeof(CelestialCacheHeader) + 10, SEEK_SET);
  uint8_t byte = 0xFF;
  fwrite(&byte, 1, 1, f);
  fclose(f);

  // Loading should fail CRC32 verification and return NULL cleanly
  LoadedSimulationBodies *loaded = cache_load(cache_file);
  cr_assert_null(loaded,
                 "Corrupted cache payload must be rejected by CRC32 check");

  loaded_simulation_bodies_free(&bodies);
  remove(cache_file);
}
