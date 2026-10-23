#include "cache_data_loader.h"
#include "cache_header.h"
#include "core/log/log.h"

#include "core/space/moon.h"
#include "core/space/orbit.h"
#include "core/space/planet.h"
#include "core/space/star.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define STAR_CHUNK_SIZE 1024

static uint32_t crc32_update(uint32_t crc, const void *buf, size_t len) {
  static uint32_t table[256];
  static bool table_init = false;
  if (!table_init) {
    for (uint32_t i = 0; i < 256; i++) {
      uint32_t c = i;
      for (int j = 0; j < 8; j++)
        c = (c & 1) ? (0xEDB88320L ^ (c >> 1)) : (c >> 1);

      table[i] = c;
    }

    table_init = true;
  }

  const uint8_t *p = (const uint8_t *)buf;
  crc = ~crc;
  for (size_t i = 0; i < len; i++)
    crc = table[(crc ^ p[i]) & 0xFF] ^ (crc >> 8);

  return ~crc;
}

static bool get_file_stat(const char *path, uint64_t *out_mtime,
                          uint64_t *out_size) {
  if (!path)
    return false;

  struct stat st;
  if (stat(path, &st) != 0)
    return false;

  if (out_mtime)
    *out_mtime = (uint64_t)st.st_mtime;

  if (out_size)
    *out_size = (uint64_t)st.st_size;

  return true;
}

static int32_t find_orbit_index(const DynamicArray *orbits,
                                const CelestialBody_Orbit *target) {
  if (!target || !orbits)
    return -1;

  size_t count = DynamicArray_length((DynamicArray *)orbits);
  for (size_t i = 0; i < count; i++) {
    CelestialBody_Orbit *o = NULL;
    DynamicArray_get((DynamicArray *)orbits, i, &o);
    if (o == target)
      return (int32_t)i;
  }

  return -1;
}

char *cache_get_sidecar_path(const char *source_path) {
  if (!source_path)
    return NULL;

  const char *suffix = ".cache";
  size_t len = strlen(source_path) + strlen(suffix) + 1;
  char *res = malloc(len);
  if (!res)
    return NULL;

  snprintf(res, len, "%s%s", source_path, suffix);
  return res;
}

bool cache_is_valid(const char *source_path, const char *cache_path) {
  if (!source_path || !cache_path)
    return false;

  uint64_t src_mtime = 0, src_size = 0;
  if (!get_file_stat(source_path, &src_mtime, &src_size))
    return false;

  FILE *f = fopen(cache_path, "rb");
  if (!f)
    return false;

  CelestialCacheHeader header;
  size_t read_bytes = fread(&header, 1, sizeof(CelestialCacheHeader), f);
  fclose(f);

  if (read_bytes != sizeof(CelestialCacheHeader))
    return false;

  if (header.magic != CACHE_MAGIC || header.format_version != CACHE_VERSION)
    return false;

  if (header.source_mtime != src_mtime || header.source_size != src_size)
    return false;

  if (header.sizeof_star != sizeof(CelestialBody_Star) ||
      header.sizeof_planet != sizeof(CelestialBody_Planet) ||
      header.sizeof_moon != sizeof(CelestialBody_Moon) ||
      header.sizeof_orbit != sizeof(CelestialBody_Orbit))
    return false;

  return true;
}

bool cache_save(const char *cache_path, const char *source_path,
                const LoadedSimulationBodies *bodies) {
  if (!cache_path || !bodies)
    return false;

  uint64_t src_mtime = 0, src_size = 0;
  if (source_path)
    get_file_stat(source_path, &src_mtime, &src_size);

  size_t orbit_count = DynamicArray_length((DynamicArray *)&bodies->orbits);
  size_t star_count = DynamicArray_length((DynamicArray *)&bodies->stars);
  size_t planet_count = DynamicArray_length((DynamicArray *)&bodies->planets);
  size_t moon_count = DynamicArray_length((DynamicArray *)&bodies->moons);

  size_t tmp_path_len = strlen(cache_path) + 8;
  char *tmp_path = malloc(tmp_path_len);
  if (!tmp_path)
    return false;

  snprintf(tmp_path, tmp_path_len, "%s.tmp", cache_path);

  FILE *f = fopen(tmp_path, "wb");
  if (!f) {
    LOG_WARN("Failed to open temp cache file for writing: %s", tmp_path);
    free(tmp_path);
    return false;
  }

  CelestialCacheHeader header;
  memset(&header, 0, sizeof(CelestialCacheHeader));
  header.magic = CACHE_MAGIC;
  header.format_version = CACHE_VERSION;
  header.source_mtime = src_mtime;
  header.source_size = src_size;
  header.sizeof_star = sizeof(CelestialBody_Star);
  header.sizeof_planet = sizeof(CelestialBody_Planet);
  header.sizeof_moon = sizeof(CelestialBody_Moon);
  header.sizeof_orbit = sizeof(CelestialBody_Orbit);
  header.sim_date = bodies->sim_date;

  header.orbit_count = orbit_count;
  header.orbit_offset = sizeof(CelestialCacheHeader);

  header.star_count = star_count;
  header.star_offset =
      header.orbit_offset + orbit_count * sizeof(CelestialBody_Orbit);

  header.planet_count = planet_count;
  header.planet_offset =
      header.star_offset + star_count * sizeof(CelestialBody_Star);

  size_t planet_payload_size = planet_count * sizeof(CelestialBody_Planet) +
                               planet_count * sizeof(int32_t);
  header.moon_count = moon_count;
  header.moon_offset = header.planet_offset + planet_payload_size;

  // Write placeholder header (will be overwritten with correct payload_crc32)
  if (fwrite(&header, sizeof(CelestialCacheHeader), 1, f) != 1) {
    fclose(f);
    remove(tmp_path);
    free(tmp_path);
    return false;
  }

  uint32_t crc = 0;

  for (size_t i = 0; i < orbit_count; i++) {
    CelestialBody_Orbit *o = NULL;
    DynamicArray_get((DynamicArray *)&bodies->orbits, i, &o);
    CelestialBody_Orbit val = o ? *o : (CelestialBody_Orbit){0};
    crc = crc32_update(crc, &val, sizeof(CelestialBody_Orbit));

    if (fwrite(&val, sizeof(CelestialBody_Orbit), 1, f) != 1)
      goto write_err;
  }

  CelestialBody_Star star_chunk[STAR_CHUNK_SIZE];
  size_t star_idx = 0;
  while (star_idx < star_count) {
    size_t batch = (star_count - star_idx > STAR_CHUNK_SIZE)
                       ? STAR_CHUNK_SIZE
                       : (star_count - star_idx);

    for (size_t j = 0; j < batch; j++) {
      CelestialBody_Star *s = NULL;
      DynamicArray_get((DynamicArray *)&bodies->stars, star_idx + j, &s);
      star_chunk[j] = s ? *s : (CelestialBody_Star){0};
    }

    crc = crc32_update(crc, star_chunk, batch * sizeof(CelestialBody_Star));
    if (fwrite(star_chunk, sizeof(CelestialBody_Star), batch, f) != batch)
      goto write_err;

    star_idx += batch;
  }

  int32_t *planet_orbit_indices =
      planet_count > 0 ? malloc(planet_count * sizeof(int32_t)) : NULL;
  for (size_t i = 0; i < planet_count; i++) {
    CelestialBody_Planet *p = NULL;
    DynamicArray_get((DynamicArray *)&bodies->planets, i, &p);
    CelestialBody_Planet val = p ? *p : (CelestialBody_Planet){0};
    planet_orbit_indices[i] = find_orbit_index(&bodies->orbits, val.orbit);
    val.orbit = NULL; // Zero out pointer before disk serialization
    crc = crc32_update(crc, &val, sizeof(CelestialBody_Planet));

    if (fwrite(&val, sizeof(CelestialBody_Planet), 1, f) != 1) {
      free(planet_orbit_indices);
      goto write_err;
    }
  }

  if (planet_count > 0) {
    crc =
        crc32_update(crc, planet_orbit_indices, planet_count * sizeof(int32_t));
    if (fwrite(planet_orbit_indices, sizeof(int32_t), planet_count, f) !=
        planet_count) {
      free(planet_orbit_indices);
      goto write_err;
    }

    free(planet_orbit_indices);
  }

  int32_t *moon_orbit_indices =
      moon_count > 0 ? malloc(moon_count * sizeof(int32_t)) : NULL;
  for (size_t i = 0; i < moon_count; i++) {
    CelestialBody_Moon *m = NULL;
    DynamicArray_get((DynamicArray *)&bodies->moons, i, &m);
    CelestialBody_Moon val = m ? *m : (CelestialBody_Moon){0};
    moon_orbit_indices[i] = find_orbit_index(&bodies->orbits, val.orbit);
    val.orbit = NULL; // Zero out pointer before disk serialization
    crc = crc32_update(crc, &val, sizeof(CelestialBody_Moon));

    if (fwrite(&val, sizeof(CelestialBody_Moon), 1, f) != 1) {
      free(moon_orbit_indices);
      goto write_err;
    }
  }

  if (moon_count > 0) {
    crc = crc32_update(crc, moon_orbit_indices, moon_count * sizeof(int32_t));
    if (fwrite(moon_orbit_indices, sizeof(int32_t), moon_count, f) !=
        moon_count) {
      free(moon_orbit_indices);
      goto write_err;
    }

    free(moon_orbit_indices);
  }

  header.payload_crc32 = crc;
  if (fseek(f, 0, SEEK_SET) != 0)
    goto write_err;

  if (fwrite(&header, sizeof(CelestialCacheHeader), 1, f) != 1)
    goto write_err;

  fflush(f);
  fclose(f);

  // Atomically replace target cache file
  if (rename(tmp_path, cache_path) != 0) {
    LOG_WARN("Failed to rename temp cache file %s to %s", tmp_path, cache_path);
    remove(tmp_path);
    free(tmp_path);
    return false;
  }

  free(tmp_path);
  return true;

write_err:
  fclose(f);
  remove(tmp_path);
  free(tmp_path);
  return false;
}

LoadedSimulationBodies *cache_load(const char *cache_path) {
  if (!cache_path)
    return NULL;

  FILE *f = fopen(cache_path, "rb");
  if (!f)
    return NULL;

  CelestialCacheHeader header;
  if (fread(&header, sizeof(CelestialCacheHeader), 1, f) != 1) {
    fclose(f);
    return NULL;
  }

  if (header.magic != CACHE_MAGIC || header.format_version != CACHE_VERSION) {
    fclose(f);
    return NULL;
  }

  if (header.sizeof_star != sizeof(CelestialBody_Star) ||
      header.sizeof_planet != sizeof(CelestialBody_Planet) ||
      header.sizeof_moon != sizeof(CelestialBody_Moon) ||
      header.sizeof_orbit != sizeof(CelestialBody_Orbit)) {
    fclose(f);
    return NULL;
  }

  LoadedSimulationBodies *bodies = calloc(1, sizeof(LoadedSimulationBodies));
  if (!bodies) {
    fclose(f);
    return NULL;
  }

  loaded_simulation_bodies_init(bodies);
  bodies->sim_date = header.sim_date;

  uint32_t crc = 0;

  CelestialBody_Orbit **orbit_ptrs =
      header.orbit_count > 0
          ? malloc(header.orbit_count * sizeof(CelestialBody_Orbit *))
          : NULL;

  for (size_t i = 0; i < header.orbit_count; i++) {
    CelestialBody_Orbit *o = malloc(sizeof(CelestialBody_Orbit));
    if (!o || fread(o, sizeof(CelestialBody_Orbit), 1, f) != 1) {
      free(o);
      goto read_err;
    }

    crc = crc32_update(crc, o, sizeof(CelestialBody_Orbit));
    orbit_ptrs[i] = o;
    DynamicArray_push(&bodies->orbits, &o);
  }

  CelestialBody_Star star_chunk[STAR_CHUNK_SIZE];
  size_t star_read = 0;
  while (star_read < header.star_count) {
    size_t batch = (header.star_count - star_read > STAR_CHUNK_SIZE)
                       ? STAR_CHUNK_SIZE
                       : (header.star_count - star_read);

    if (fread(star_chunk, sizeof(CelestialBody_Star), batch, f) != batch)
      goto read_err;

    crc = crc32_update(crc, star_chunk, batch * sizeof(CelestialBody_Star));
    for (size_t j = 0; j < batch; j++) {
      CelestialBody_Star *s = malloc(sizeof(CelestialBody_Star));
      if (!s)
        goto read_err;

      *s = star_chunk[j];
      DynamicArray_push(&bodies->stars, &s);
    }

    star_read += batch;
  }

  if (header.planet_count > 0) {
    CelestialBody_Planet *disk_planets =
        malloc(header.planet_count * sizeof(CelestialBody_Planet));
    int32_t *planet_orbit_indices =
        malloc(header.planet_count * sizeof(int32_t));

    if (!disk_planets || !planet_orbit_indices) {
      free(disk_planets);
      free(planet_orbit_indices);
      goto read_err;
    }

    if (fread(disk_planets, sizeof(CelestialBody_Planet), header.planet_count,
              f) != header.planet_count) {
      free(disk_planets);
      free(planet_orbit_indices);
      goto read_err;
    }

    crc = crc32_update(crc, disk_planets,
                       header.planet_count * sizeof(CelestialBody_Planet));

    if (fread(planet_orbit_indices, sizeof(int32_t), header.planet_count, f) !=
        header.planet_count) {
      free(disk_planets);
      free(planet_orbit_indices);
      goto read_err;
    }

    crc = crc32_update(crc, planet_orbit_indices,
                       header.planet_count * sizeof(int32_t));

    for (size_t i = 0; i < header.planet_count; i++) {
      CelestialBody_Planet *p = malloc(sizeof(CelestialBody_Planet));
      if (!p) {
        free(disk_planets);
        free(planet_orbit_indices);
        goto read_err;
      }

      *p = disk_planets[i];
      int32_t o_idx = planet_orbit_indices[i];
      p->orbit = (o_idx >= 0 && (size_t)o_idx < header.orbit_count)
                     ? orbit_ptrs[o_idx]
                     : NULL;
      DynamicArray_push(&bodies->planets, &p);
    }

    free(disk_planets);
    free(planet_orbit_indices);
  }

  if (header.moon_count > 0) {
    CelestialBody_Moon *disk_moons =
        malloc(header.moon_count * sizeof(CelestialBody_Moon));
    int32_t *moon_orbit_indices = malloc(header.moon_count * sizeof(int32_t));

    if (!disk_moons || !moon_orbit_indices) {
      free(disk_moons);
      free(moon_orbit_indices);
      goto read_err;
    }

    if (fread(disk_moons, sizeof(CelestialBody_Moon), header.moon_count, f) !=
        header.moon_count) {
      free(disk_moons);
      free(moon_orbit_indices);
      goto read_err;
    }

    crc = crc32_update(crc, disk_moons,
                       header.moon_count * sizeof(CelestialBody_Moon));

    if (fread(moon_orbit_indices, sizeof(int32_t), header.moon_count, f) !=
        header.moon_count) {
      free(disk_moons);
      free(moon_orbit_indices);
      goto read_err;
    }

    crc = crc32_update(crc, moon_orbit_indices,
                       header.moon_count * sizeof(int32_t));

    for (size_t i = 0; i < header.moon_count; i++) {
      CelestialBody_Moon *m = malloc(sizeof(CelestialBody_Moon));
      if (!m) {
        free(disk_moons);
        free(moon_orbit_indices);
        goto read_err;
      }

      *m = disk_moons[i];
      int32_t o_idx = moon_orbit_indices[i];
      m->orbit = (o_idx >= 0 && (size_t)o_idx < header.orbit_count)
                     ? orbit_ptrs[o_idx]
                     : NULL;
      DynamicArray_push(&bodies->moons, &m);
    }

    free(disk_moons);
    free(moon_orbit_indices);
  }

  free(orbit_ptrs);
  fclose(f);

  if (crc != header.payload_crc32) {
    LOG_WARN("Cache file checksum mismatch for %s (calculated: 0x%08X, "
             "expected: 0x%08X)",
             cache_path, crc, header.payload_crc32);
    loaded_simulation_bodies_free(bodies);
    free(bodies);
    return NULL;
  }

  return bodies;

read_err:
  if (orbit_ptrs)
    free(orbit_ptrs);

  fclose(f);
  loaded_simulation_bodies_free(bodies);
  free(bodies);
  return NULL;
}

// -----------------------------------------------------------------------------
// Sidecar Wrappers
// -----------------------------------------------------------------------------

LoadedSimulationBodies *cache_load_sidecar_if_valid(const char *source_path) {
  if (!source_path)
    return NULL;

  char *cache_path = cache_get_sidecar_path(source_path);
  if (!cache_path)
    return NULL;

  LoadedSimulationBodies *bodies = NULL;
  if (cache_is_valid(source_path, cache_path))
    bodies = cache_load(cache_path);
  // else
  // invalidate cache (remove cache file)

  free(cache_path);
  return bodies;
}

bool cache_save_sidecar(const char *source_path,
                        const LoadedSimulationBodies *bodies) {
  if (!source_path || !bodies)
    return false;

  char *cache_path = cache_get_sidecar_path(source_path);
  if (!cache_path)
    return false;

  bool ok = cache_save(cache_path, source_path, bodies);
  free(cache_path);
  return ok;
}

LoadedSimulationBodies *cache_loader_load(const char *filename) {
  LoadedSimulationBodies *cached_bodies = cache_load_sidecar_if_valid(filename);
  if (!cached_bodies) {
    LOG_WARN("No valid cache found for %s", filename);
    return NULL;
  }

  return cached_bodies;
}