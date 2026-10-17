#include "data_loader.h"

#include <stdlib.h>
#include <string.h>

static DynamicArray REGISTERED_LOADERS;
DynamicArray *data_loader_get_registered_loaders(void) {
  return &REGISTERED_LOADERS;
}

const char *get_file_ext(const char *filename) {
  return strrchr(filename, '.');
}

const DataLoader *data_loader_get_by_ext(const char *ext) {
  int num_loaders = DynamicArray_length(&REGISTERED_LOADERS);
  for (int i = 0; i < num_loaders; i++) {
    const DataLoader *loader;
    DynamicArray_get(&REGISTERED_LOADERS, i, &loader);
    if (!strcmp(loader->format_ext, ext))
      return loader;
  }

  return NULL;
}

void loaded_simulation_bodies_init(LoadedSimulationBodies *bodies) {
  if (!bodies)
    return;

  memset(bodies, 0, sizeof(LoadedSimulationBodies));
  DynamicArray_init(&bodies->orbits, sizeof(CelestialBody_Orbit *));
  DynamicArray_init(&bodies->stars, sizeof(CelestialBody_Star *));
  DynamicArray_init(&bodies->planets, sizeof(CelestialBody_Planet *));
  DynamicArray_init(&bodies->moons, sizeof(CelestialBody_Moon *));
}

void loaded_simulation_bodies_free(LoadedSimulationBodies *bodies) {
  if (!bodies)
    return;

  size_t count = DynamicArray_length(&bodies->orbits);
  for (size_t i = 0; i < count; i++) {
    CelestialBody_Orbit *o;
    DynamicArray_get(&bodies->orbits, i, &o);
    free(o);
  }
  DynamicArray_free(&bodies->orbits);

  count = DynamicArray_length(&bodies->stars);
  for (size_t i = 0; i < count; i++) {
    CelestialBody_Star *s;
    DynamicArray_get(&bodies->stars, i, &s);
    free(s);
  }
  DynamicArray_free(&bodies->stars);

  count = DynamicArray_length(&bodies->planets);
  for (size_t i = 0; i < count; i++) {
    CelestialBody_Planet *p;
    DynamicArray_get(&bodies->planets, i, &p);
    free(p);
  }
  DynamicArray_free(&bodies->planets);

  count = DynamicArray_length(&bodies->moons);
  for (size_t i = 0; i < count; i++) {
    CelestialBody_Moon *m;
    DynamicArray_get(&bodies->moons, i, &m);
    free(m);
  }
  DynamicArray_free(&bodies->moons);
}

void data_loader_register(const DataLoader *loader) {
  DynamicArray_push(&REGISTERED_LOADERS, (void *)&loader);
}

void data_loader_register_loaders(void) {
  DynamicArray_init(&REGISTERED_LOADERS, sizeof(const DataLoader *));

  data_loader_register(&DATA_LOADER_JSON);
}