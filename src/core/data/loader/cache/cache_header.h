
#ifndef CORE_CACHE_CACHE_HEADER_H
#define CORE_CACHE_CACHE_HEADER_H

#include "core/cli/args/cli_flag.h"

#include <stdint.h>

#define CACHE_MAGIC 0x43454C43 // "CELC" (Celestial Engine Loaded Cache)
#define CACHE_VERSION 1

typedef struct {
  uint32_t magic;          // Must be CACHE_MAGIC
  uint32_t format_version; // Engine cache version

  uint64_t source_mtime; // Source file modified time (stat st_mtime)
  uint64_t source_size;  // Source file size in bytes (stat st_size)

  uint32_t sizeof_star;   // sizeof(CelestialBody_Star)
  uint32_t sizeof_planet; // sizeof(CelestialBody_Planet)
  uint32_t sizeof_moon;   // sizeof(CelestialBody_Moon)
  uint32_t sizeof_orbit;  // sizeof(CelestialBody_Orbit)

  CLIArgSimDate sim_date;

  uint64_t orbit_count;
  uint64_t orbit_offset;

  uint64_t star_count;
  uint64_t star_offset;

  uint64_t planet_count;
  uint64_t planet_offset;

  uint64_t moon_count;
  uint64_t moon_offset;

  uint32_t payload_crc32;
} CelestialCacheHeader;

#endif