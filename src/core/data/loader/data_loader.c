#include "data_loader.h"

#include <string.h>

static DynamicArray REGISTERED_LOADERS;
DynamicArray *data_loader_get_registered_loaders(void) {
  return &REGISTERED_LOADERS;
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

void data_loader_register(const DataLoader *loader) {
  DynamicArray_push(&REGISTERED_LOADERS, (void *)&loader);
}

void data_loader_register_loaders(void) {
  DynamicArray_init(&REGISTERED_LOADERS, sizeof(const DataLoader *));

  data_loader_register(&DATA_LOADER_JSON);
}