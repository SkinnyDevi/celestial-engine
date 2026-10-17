#ifndef CORE_DATA_LOADER_H
#define CORE_DATA_LOADER_H

#include "core/data/dyn_array.h"

#include "core/cli/args/cli_flag.h"

#include "core/space/moon.h"
#include "core/space/orbit.h"
#include "core/space/planet.h"
#include "core/space/star.h"

#include <stdbool.h>
#include <stddef.h>

typedef struct {
  CLIArgSimDate sim_date;
  DynamicArray orbits;
  DynamicArray planets;
  DynamicArray moons;
  DynamicArray stars;
} LoadedSimulationBodies;

void loaded_simulation_bodies_init(LoadedSimulationBodies *bodies);
void loaded_simulation_bodies_free(LoadedSimulationBodies *bodies);

typedef struct {
  const char *format_ext;
  LoadedSimulationBodies *(*load)(const char *filename);
  bool (*save)(const char *filename, const LoadedSimulationBodies *bodies);
} DataLoader;

const char *get_file_ext(const char *filename);
DynamicArray *data_loader_get_registered_loaders(void);
const DataLoader *data_loader_get_by_ext(const char *ext);
void data_loader_register_loaders(void);

#ifndef DATA_LOADER_REGISTRY
#define DATA_LOADER_REGISTRY
extern const DataLoader DATA_LOADER_JSON;

#endif

#endif