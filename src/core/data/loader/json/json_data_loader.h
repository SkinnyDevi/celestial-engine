#ifndef CORE_DATA_LOADER_JSON_JSON_DATA_LOADER_H
#define CORE_DATA_LOADER_JSON_JSON_DATA_LOADER_H

#include "core/data/loader/data_loader.h"
#include "core/space/location.h"

#include <cJSON.h>
#include <stdbool.h>
#include <stddef.h>

cJSON *vector3_to_json(Vector3 v);
cJSON *quaternion_to_json(Quaternion q);
Vector3 json_to_vector3(cJSON *obj);
Quaternion json_to_quaternion(cJSON *obj);

char *serialize_celestial_body(void *celestial_object);
bool deserialize_celestial_body(const char *json_string,
                                void *celestial_object);

LoadedSimulationBodies *json_load(const char *filename);
bool json_save(const char *filename, const LoadedSimulationBodies *bodies);

#endif
