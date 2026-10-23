#include "cli_flag.h"

#include "core/cli/instance_data.h"
#include "core/data/hash_table.h"
#include "core/data/loader/data_loader.h"
#include "core/log/log.h"

#include "core/space/moon.h"
#include "core/space/orbit.h"
#include "core/space/planet.h"
#include "core/space/star.h"

#include <stdlib.h>
#include <string.h>

static void merge_loaded_bodies(LoadedSimulationBodies *dest,
                                LoadedSimulationBodies *src) {
  if (!dest || !src)
    return;

  if (src->sim_date.has_set_date)
    dest->sim_date = src->sim_date;

  // Merge orbits
  size_t count = DynamicArray_length(&src->orbits);
  for (size_t i = 0; i < count; i++) {
    CelestialBody_Orbit *o;
    DynamicArray_get(&src->orbits, i, &o);
    DynamicArray_push(&dest->orbits, &o);
  }

  // Build hash tables for existing bodies in dest for O(1) deduplication
  HashTable *star_ids = HashTable_create();
  size_t dest_star_count = DynamicArray_length(&dest->stars);
  for (size_t i = 0; i < dest_star_count; i++) {
    CelestialBody_Star *star;
    DynamicArray_get(&dest->stars, i, &star);
    if (star && star->body_id[0] != '\0')
      HashTable_set(star_ids, star->body_id, star);
  }

  // Merge stars (with O(1) deduplication)
  count = DynamicArray_length(&src->stars);
  for (size_t i = 0; i < count; i++) {
    CelestialBody_Star *src_star;
    DynamicArray_get(&src->stars, i, &src_star);

    if (src_star && src_star->body_id[0] != '\0' &&
        HashTable_get(star_ids, src_star->body_id) != NULL) {
      free(src_star);
    } else {
      if (src_star && src_star->body_id[0] != '\0')
        HashTable_set(star_ids, src_star->body_id, src_star);
      DynamicArray_push(&dest->stars, &src_star);
    }
  }
  HashTable_destroy(star_ids);

  // Build hash table for planets in dest
  HashTable *planet_ids = HashTable_create();
  size_t dest_planet_count = DynamicArray_length(&dest->planets);
  for (size_t i = 0; i < dest_planet_count; i++) {
    CelestialBody_Planet *planet;
    DynamicArray_get(&dest->planets, i, &planet);
    if (planet && planet->body_id[0] != '\0')
      HashTable_set(planet_ids, planet->body_id, planet);
  }

  // Merge planets (with O(1) deduplication)
  count = DynamicArray_length(&src->planets);
  for (size_t i = 0; i < count; i++) {
    CelestialBody_Planet *src_planet;
    DynamicArray_get(&src->planets, i, &src_planet);

    if (src_planet && src_planet->body_id[0] != '\0' &&
        HashTable_get(planet_ids, src_planet->body_id) != NULL) {
      free(src_planet);
    } else {
      if (src_planet && src_planet->body_id[0] != '\0')
        HashTable_set(planet_ids, src_planet->body_id, src_planet);
      DynamicArray_push(&dest->planets, &src_planet);
    }
  }
  HashTable_destroy(planet_ids);

  // Build hash table for moons in dest
  HashTable *moon_ids = HashTable_create();
  size_t dest_moon_count = DynamicArray_length(&dest->moons);
  for (size_t i = 0; i < dest_moon_count; i++) {
    CelestialBody_Moon *moon;
    DynamicArray_get(&dest->moons, i, &moon);
    if (moon && moon->body_id[0] != '\0')
      HashTable_set(moon_ids, moon->body_id, moon);
  }

  // Merge moons (with O(1) deduplication)
  count = DynamicArray_length(&src->moons);
  for (size_t i = 0; i < count; i++) {
    CelestialBody_Moon *src_moon;
    DynamicArray_get(&src->moons, i, &src_moon);

    if (src_moon && src_moon->body_id[0] != '\0' &&
        HashTable_get(moon_ids, src_moon->body_id) != NULL) {
      free(src_moon);
    } else {
      if (src_moon && src_moon->body_id[0] != '\0')
        HashTable_set(moon_ids, src_moon->body_id, src_moon);
      DynamicArray_push(&dest->moons, &src_moon);
    }
  }
  HashTable_destroy(moon_ids);

  DynamicArray_free(&src->orbits);
  DynamicArray_free(&src->stars);
  DynamicArray_free(&src->planets);
  DynamicArray_free(&src->moons);
  free(src);
}

void cli_flag_load_data_file(int argc, char **argv) {
  LoadedSimulationBodies *global_bodies = cli_get_sim_bodies();

  // If this is the first data file processed
  // initialize the global bodies
  if (!cli_is_using_data_file()) {
    loaded_simulation_bodies_init(global_bodies);
    _cli_arg_set_using_data_file(true);
  }

  for (int i = 1; i < argc; i++) {
    if (strcmp(argv[i], CLI_DATA_FILE_FLAG.arg) != 0)
      continue;

    // Process all arguments following --data-file until next flag starting
    // with '-'
    for (int j = i + 1; j < argc && argv[j][0] != '-'; j++) {
      const char *file_path = argv[j];
      const char *ext = get_file_ext(file_path);
      LOG_INFO("Loading data from file %s", file_path);

      LoadedSimulationBodies *bodies = data_loader_load(file_path);
      if (bodies == NULL) {
        LOG_ERROR("Failed to load data from file %s", file_path);
        exit(EXIT_FAILURE);
      }

      _cli_arg_set_data_file_path(file_path);
      merge_loaded_bodies(global_bodies, bodies);

      if (global_bodies->sim_date.has_set_date) {
        CLIArgSimDate *sim_date = cli_get_sim_date();
        sim_date->time = global_bodies->sim_date.time;
        sim_date->has_set_date = true;
        _cli_arg_set_sim_date(sim_date);
      }
    }
  }
}