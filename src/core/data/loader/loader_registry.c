#include "cache/cache_data_loader.h"
#include "json/json_data_loader.h"

const DataLoader DATA_LOADER_JSON = {
    .format_ext = ".json", .load = json_load, .save = json_save};

const DataLoader DATA_LOADER_CACHE = {.format_ext = ".cache",
                                      .load = cache_loader_load,
                                      .save = cache_save_sidecar};