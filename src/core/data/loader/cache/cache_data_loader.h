#ifndef CORE_CACHE_CACHE_H
#define CORE_CACHE_CACHE_H

#include "core/data/loader/data_loader.h"
#include <stdbool.h>

/**
 * Returns a dynamically allocated string representing the sidecar cache file
 * path for a given source path (e.g. "path/to/foo.json.cache" for
 * "path/to/foo.json"). The caller is responsible for freeing the returned
 * string with free().
 */
char *cache_get_sidecar_path(const char *source_path);

/**
 * Checks if a cache file at cache_path exists and is valid for the given
 * source_path. Validates file presence, modification time, file size, magic
 * number, format version, and struct sizes (ABI safety).
 */
bool cache_is_valid(const char *source_path, const char *cache_path);

/**
 * Loads simulation bodies directly from a binary cache file.
 * Verifies magic number, format version, ABI sizes, and computes CRC32 payload
 * checksum. Returns a newly allocated LoadedSimulationBodies pointer, or NULL
 * on failure.
 */
LoadedSimulationBodies *cache_load(const char *cache_path);

/**
 * Saves simulation bodies into a binary cache file corresponding to
 * source_path. Writes atomically via a temporary file to prevent corrupted
 * cache files upon failure. Returns true on success, false on failure.
 */
bool cache_save(const char *cache_path, const char *source_path,
                const LoadedSimulationBodies *bodies);

/**
 * Convenience helper: Checks if sidecar cache exists and is valid for
 * source_path. If valid, loads and returns bodies; if not, returns NULL.
 */
LoadedSimulationBodies *cache_load_sidecar_if_valid(const char *source_path);

/**
 * Convenience helper: Saves bodies to sidecar cache for source_path
 * (<source_path>.cache). Returns true on success, false on failure.
 */
bool cache_save_sidecar(const char *source_path,
                        const LoadedSimulationBodies *bodies);

/**
 * Cache loader implementation used by data_loader.
 */
LoadedSimulationBodies *cache_loader_load(const char *filename);

#endif
