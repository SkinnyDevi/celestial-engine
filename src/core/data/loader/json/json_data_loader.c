#include "json_data_loader.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// -----------------------------------------------------------------------------
// Helper Methods (Read)
// -----------------------------------------------------------------------------

static char *read_file_to_string(const char *filename) {
  FILE *file = fopen(filename, "r");
  if (!file)
    return NULL;

  fseek(file, 0, SEEK_END);
  long length = ftell(file);
  fseek(file, 0, SEEK_SET);

  char *data = malloc(length + 1);
  if (data) {
    size_t read_bytes = fread(data, 1, length, file);
    data[read_bytes] = '\0';
  }

  fclose(file);
  return data;
}

static double get_double(cJSON *parent, const char *key, double def) {
  cJSON *item = cJSON_GetObjectItemCaseSensitive(parent, key);
  return cJSON_IsNumber(item) ? item->valuedouble : def;
}

static int get_int(cJSON *parent, const char *key, int def) {
  cJSON *item = cJSON_GetObjectItemCaseSensitive(parent, key);
  return cJSON_IsNumber(item) ? item->valueint : def;
}

static void get_string(cJSON *parent, const char *key, char *out,
                       size_t max_len) {
  cJSON *item = cJSON_GetObjectItemCaseSensitive(parent, key);
  if (cJSON_IsString(item) && item->valuestring) {
    strncpy(out, item->valuestring, max_len - 1);
    out[max_len - 1] = '\0';
  } else {
    out[0] = '\0';
  }
}

static Vector3 parse_vector3(cJSON *parent, const char *key) {
  Vector3 v = {0};
  cJSON *item = cJSON_GetObjectItemCaseSensitive(parent, key);

  if (cJSON_IsObject(item)) {
    v.x = get_double(item, "x", 0.0);
    v.y = get_double(item, "y", 0.0);
    v.z = get_double(item, "z", 0.0);
  }

  return v;
}

static Quaternion parse_quaternion(cJSON *parent, const char *key) {
  Quaternion q = {0, 0, 0, 1};
  cJSON *item = cJSON_GetObjectItemCaseSensitive(parent, key);

  if (cJSON_IsObject(item)) {
    q.x = get_double(item, "x", 0.0);
    q.y = get_double(item, "y", 0.0);
    q.z = get_double(item, "z", 0.0);
    q.w = get_double(item, "w", 1.0);
  }

  return q;
}

// -----------------------------------------------------------------------------
// Parsing Entities
// -----------------------------------------------------------------------------

static void parse_orbits(cJSON *root, LoadedSimulationBodies *bodies) {
  cJSON *arr = cJSON_GetObjectItemCaseSensitive(root, "orbits");
  bodies->num_orbits = cJSON_GetArraySize(arr);
  if (bodies->num_orbits == 0)
    return;

  bodies->orbits = calloc(bodies->num_orbits, sizeof(CelestialBody_Orbit));

  cJSON *item;
  size_t i = 0;
  cJSON_ArrayForEach(item, arr) {
    CelestialBody_Orbit *cb_orbit = &bodies->orbits[i++];
    cb_orbit->semimajor_axis = get_double(item, "semimajor_axis", 0);
    cb_orbit->eccentricity = get_double(item, "eccentricity", 0);
    cb_orbit->inclination = get_double(item, "inclination", 0);
    cb_orbit->longitude_of_ascending_node =
        get_double(item, "longitude_of_ascending_node", 0);
    cb_orbit->argument_of_periapsis =
        get_double(item, "argument_of_periapsis", 0);
    cb_orbit->mean_anomaly_at_epoch =
        get_double(item, "mean_anomaly_at_epoch", 0);
    cb_orbit->orbital_period_days = get_double(item, "orbital_period_days", 0);
    cb_orbit->mean_anomaly = get_double(item, "mean_anomaly", 0);
    cb_orbit->true_anomaly = get_double(item, "true_anomaly", 0);
    cb_orbit->center_position = parse_vector3(item, "center_position");
  }
}

static void parse_stars(cJSON *root, LoadedSimulationBodies *bodies) {
  cJSON *arr = cJSON_GetObjectItemCaseSensitive(root, "stars");
  bodies->num_stars = cJSON_GetArraySize(arr);
  if (bodies->num_stars == 0)
    return;

  bodies->stars = calloc(bodies->num_stars, sizeof(CelestialBody_Star));

  cJSON *item;
  size_t i = 0;
  cJSON_ArrayForEach(item, arr) {
    CelestialBody_Star *cb_star = &bodies->stars[i++];
    get_string(item, "name", cb_star->name, sizeof(cb_star->name));
    get_string(item, "body_id", cb_star->body_id, sizeof(cb_star->body_id));

    cb_star->spectral_type = get_int(item, "spectral_type", 0);
    cb_star->spectral_subtype = get_int(item, "spectral_subtype", 0);
    cb_star->position = parse_vector3(item, "position");
    cb_star->rotation = parse_quaternion(item, "rotation");
    cb_star->right_ascension_rad = get_double(item, "right_ascension_rad", 0);
    cb_star->declination_rad = get_double(item, "declination_rad", 0);
    cb_star->distance_pc = get_double(item, "distance_pc", 0);
    cb_star->mass_kg = get_double(item, "mass_kg", 0);
    cb_star->radius_m = get_double(item, "radius_m", 0);
    cb_star->surface_temperature_k =
        get_double(item, "surface_temperature_k", 0);
    cb_star->core_temperature_k = get_double(item, "core_temperature_k", 0);
    cb_star->luminosity_w = get_double(item, "luminosity_w", 0);
    cb_star->bolometric_luminosity_w =
        get_double(item, "bolometric_luminosity_w", 0);
    cb_star->rotation_period_days = get_double(item, "rotation_period_days", 0);
    cb_star->magnetic_field_gauss = get_double(item, "magnetic_field_gauss", 0);
  }
}

static void parse_planets(cJSON *root, LoadedSimulationBodies *bodies) {
  cJSON *arr = cJSON_GetObjectItemCaseSensitive(root, "planets");
  bodies->num_planets = cJSON_GetArraySize(arr);
  if (bodies->num_planets == 0)
    return;

  bodies->planets = calloc(bodies->num_planets, sizeof(CelestialBody_Planet));

  cJSON *item;
  size_t i = 0;
  cJSON_ArrayForEach(item, arr) {
    CelestialBody_Planet *cb_planet = &bodies->planets[i++];
    get_string(item, "name", cb_planet->name, sizeof(cb_planet->name));
    get_string(item, "body_id", cb_planet->body_id, sizeof(cb_planet->body_id));

    // Resolve host star by index
    int host_star_idx = get_int(item, "host_star_index", -1);
    if (host_star_idx >= 0 && host_star_idx < (int)bodies->num_stars) {
      strncpy(cb_planet->host_star_id, bodies->stars[host_star_idx].body_id,
              sizeof(cb_planet->host_star_id) - 1);
      cb_planet->host_star_id[sizeof(cb_planet->host_star_id) - 1] = '\0';
    } else {
      cb_planet->host_star_id[0] = '\0';
    }

    // Resolve orbit by index
    int orbit_idx = get_int(item, "orbit_index", -1);
    if (orbit_idx >= 0 && orbit_idx < (int)bodies->num_orbits)
      cb_planet->orbit = &bodies->orbits[orbit_idx];
    else
      cb_planet->orbit = NULL;

    cb_planet->planet_class = get_int(item, "planet_class", 0);
    cb_planet->position = parse_vector3(item, "position");
    cb_planet->rotation = parse_quaternion(item, "rotation");
    cb_planet->right_ascension_rad = get_double(item, "right_ascension_rad", 0);
    cb_planet->declination_rad = get_double(item, "declination_rad", 0);
    cb_planet->distance_pc = get_double(item, "distance_pc", 0);
    cb_planet->semi_major_axis_au = get_double(item, "semi_major_axis_au", 0);
    cb_planet->eccentricity = get_double(item, "eccentricity", 0);
    cb_planet->inclination_rad = get_double(item, "inclination_rad", 0);
    cb_planet->longitude_ascending_node_rad =
        get_double(item, "longitude_ascending_node_rad", 0);
    cb_planet->argument_periapsis_rad =
        get_double(item, "argument_periapsis_rad", 0);
    cb_planet->mean_anomaly_rad = get_double(item, "mean_anomaly_rad", 0);
    cb_planet->orbital_period_days = get_double(item, "orbital_period_days", 0);
    cb_planet->mass_kg = get_double(item, "mass_kg", 0);
    cb_planet->radius_m = get_double(item, "radius_m", 0);
    cb_planet->density_kg_m3 = get_double(item, "density_kg_m3", 0);
    cb_planet->surface_gravity_m_s2 =
        get_double(item, "surface_gravity_m_s2", 0);
    cb_planet->albedo = get_double(item, "albedo", 0);
    cb_planet->surface_temperature_k =
        get_double(item, "surface_temperature_k", 0);
    cb_planet->axial_tilt_rad = get_double(item, "axial_tilt_rad", 0);
    cb_planet->rotation_period_days =
        get_double(item, "rotation_period_days", 0);
    cb_planet->magnetic_field_gauss =
        get_double(item, "magnetic_field_gauss", 0);
    cb_planet->atmosphere_type = get_int(item, "atmosphere_type", 0);
    cb_planet->surface_pressure_pa = get_double(item, "surface_pressure_pa", 0);
    cb_planet->has_rings = get_int(item, "has_rings", 0);
    cb_planet->ring_inner_radius_m = get_double(item, "ring_inner_radius_m", 0);
    cb_planet->ring_outer_radius_m = get_double(item, "ring_outer_radius_m", 0);
  }
}

static void parse_moons(cJSON *root, LoadedSimulationBodies *bodies) {
  cJSON *arr = cJSON_GetObjectItemCaseSensitive(root, "moons");
  bodies->num_moons = cJSON_GetArraySize(arr);
  if (bodies->num_moons == 0)
    return;

  bodies->moons = calloc(bodies->num_moons, sizeof(CelestialBody_Moon));

  cJSON *item;
  size_t i = 0;
  cJSON_ArrayForEach(item, arr) {
    CelestialBody_Moon *cb_moon = &bodies->moons[i++];
    get_string(item, "name", cb_moon->name, sizeof(cb_moon->name));
    get_string(item, "body_id", cb_moon->body_id, sizeof(cb_moon->body_id));

    // Resolve host planet by index
    int host_planet_idx = get_int(item, "host_planet_index", -1);
    if (host_planet_idx >= 0 && host_planet_idx < (int)bodies->num_planets) {
      strncpy(cb_moon->host_planet_id, bodies->planets[host_planet_idx].body_id,
              sizeof(cb_moon->host_planet_id) - 1);
      cb_moon->host_planet_id[sizeof(cb_moon->host_planet_id) - 1] = '\0';
    } else {
      cb_moon->host_planet_id[0] = '\0';
    }

    // Resolve orbit by index
    int orbit_idx = get_int(item, "orbit_index", -1);
    if (orbit_idx >= 0 && orbit_idx < (int)bodies->num_orbits)
      cb_moon->orbit = &bodies->orbits[orbit_idx];
    else
      cb_moon->orbit = NULL;

    cb_moon->moon_class = get_int(item, "moon_class", 0);
    cb_moon->position = parse_vector3(item, "position");
    cb_moon->rotation = parse_quaternion(item, "rotation");
    cb_moon->semi_major_axis_km = get_double(item, "semi_major_axis_km", 0);
    cb_moon->eccentricity = get_double(item, "eccentricity", 0);
    cb_moon->inclination_rad = get_double(item, "inclination_rad", 0);
    cb_moon->longitude_ascending_node_rad =
        get_double(item, "longitude_ascending_node_rad", 0);
    cb_moon->argument_periapsis_rad =
        get_double(item, "argument_periapsis_rad", 0);
    cb_moon->mean_anomaly_rad = get_double(item, "mean_anomaly_rad", 0);
    cb_moon->orbital_period_days = get_double(item, "orbital_period_days", 0);
    cb_moon->mass_kg = get_double(item, "mass_kg", 0);
    cb_moon->radius_m = get_double(item, "radius_m", 0);
    cb_moon->surface_gravity_m_s2 = get_double(item, "surface_gravity_m_s2", 0);
    cb_moon->is_tidally_locked = get_int(item, "is_tidally_locked", 0);
    cb_moon->axial_tilt_rad = get_double(item, "axial_tilt_rad", 0);
    cb_moon->rotation_period_days = get_double(item, "rotation_period_days", 0);
    cb_moon->albedo = get_double(item, "albedo", 0);
    cb_moon->surface_temperature_k =
        get_double(item, "surface_temperature_k", 0);
    cb_moon->atmosphere_type = get_int(item, "atmosphere_type", 0);
    cb_moon->surface_pressure_pa = get_double(item, "surface_pressure_pa", 0);
  }
}

static void parse_sim_date(cJSON *root, LoadedSimulationBodies *bodies) {
  cJSON *item = cJSON_GetObjectItemCaseSensitive(root, "sim_date");
  if (cJSON_IsObject(item)) {
    bodies->sim_date.time.tm_year = get_int(item, "year", 2000) - 1900;
    bodies->sim_date.time.tm_mon = get_int(item, "month", 1) - 1;
    bodies->sim_date.time.tm_mday = get_int(item, "day", 1);
    bodies->sim_date.time.tm_hour = get_int(item, "hour", 0);
    bodies->sim_date.time.tm_min = get_int(item, "minute", 0);
    bodies->sim_date.time.tm_sec = get_int(item, "second", 0);
    bodies->sim_date.has_set_date = true;
  } else {
    bodies->sim_date.has_set_date = false;
  }
}

LoadedSimulationBodies *json_load(const char *filename) {
  char *json_string = read_file_to_string(filename);
  if (!json_string)
    return NULL;

  cJSON *root = cJSON_Parse(json_string);
  free(json_string);
  if (!root)
    return NULL;

  LoadedSimulationBodies *bodies = calloc(1, sizeof(LoadedSimulationBodies));
  if (!bodies) {
    cJSON_Delete(root);
    return NULL;
  }

  // Parse in dependency order
  parse_sim_date(root, bodies);
  parse_orbits(root, bodies);
  parse_stars(root, bodies);
  parse_planets(root, bodies);
  parse_moons(root, bodies);

  cJSON_Delete(root);
  return bodies;
}

// -----------------------------------------------------------------------------
// Helper Methods (Write)
// -----------------------------------------------------------------------------

static void add_vector3(cJSON *parent, const char *key, Vector3 v) {
  cJSON *obj = cJSON_CreateObject();
  cJSON_AddNumberToObject(obj, "x", v.x);
  cJSON_AddNumberToObject(obj, "y", v.y);
  cJSON_AddNumberToObject(obj, "z", v.z);
  cJSON_AddItemToObject(parent, key, obj);
}

static void add_quaternion(cJSON *parent, const char *key, Quaternion q) {
  cJSON *obj = cJSON_CreateObject();
  cJSON_AddNumberToObject(obj, "x", q.x);
  cJSON_AddNumberToObject(obj, "y", q.y);
  cJSON_AddNumberToObject(obj, "z", q.z);
  cJSON_AddNumberToObject(obj, "w", q.w);
  cJSON_AddItemToObject(parent, key, obj);
}

static int find_star_index(const LoadedSimulationBodies *bodies,
                           const char *body_id) {
  for (size_t i = 0; i < bodies->num_stars; i++)
    if (strcmp(bodies->stars[i].body_id, body_id) == 0)
      return (int)i;

  return -1;
}

static int find_planet_index(const LoadedSimulationBodies *bodies,
                             const char *body_id) {
  for (size_t i = 0; i < bodies->num_planets; i++)
    if (strcmp(bodies->planets[i].body_id, body_id) == 0)
      return (int)i;

  return -1;
}

static int find_orbit_index(const LoadedSimulationBodies *bodies,
                            const CelestialBody_Orbit *orbit) {
  if (!orbit || !bodies->orbits)
    return -1;

  // Calculate index by pointer difference
  ptrdiff_t diff = orbit - bodies->orbits;
  if (diff >= 0 && diff < (ptrdiff_t)bodies->num_orbits)
    return (int)diff;

  return -1;
}

// -----------------------------------------------------------------------------
// Saving Entities
// -----------------------------------------------------------------------------

static void json_save_orbits(cJSON *root,
                             const LoadedSimulationBodies *bodies) {
  cJSON *orbits_arr = cJSON_CreateArray();
  for (size_t i = 0; i < bodies->num_orbits; i++) {
    cJSON *item = cJSON_CreateObject();
    CelestialBody_Orbit *cb_orbit = &bodies->orbits[i];
    cJSON_AddNumberToObject(item, "semimajor_axis", cb_orbit->semimajor_axis);
    cJSON_AddNumberToObject(item, "eccentricity", cb_orbit->eccentricity);
    cJSON_AddNumberToObject(item, "inclination", cb_orbit->inclination);
    cJSON_AddNumberToObject(item, "longitude_of_ascending_node",
                            cb_orbit->longitude_of_ascending_node);
    cJSON_AddNumberToObject(item, "argument_of_periapsis",
                            cb_orbit->argument_of_periapsis);
    cJSON_AddNumberToObject(item, "mean_anomaly_at_epoch",
                            cb_orbit->mean_anomaly_at_epoch);
    cJSON_AddNumberToObject(item, "orbital_period_days",
                            cb_orbit->orbital_period_days);
    cJSON_AddNumberToObject(item, "mean_anomaly", cb_orbit->mean_anomaly);
    cJSON_AddNumberToObject(item, "true_anomaly", cb_orbit->true_anomaly);
    add_vector3(item, "center_position", cb_orbit->center_position);

    cJSON_AddItemToArray(orbits_arr, item);
  }

  cJSON_AddItemToObject(root, "orbits", orbits_arr);
}

void json_save_stars(cJSON *root, const LoadedSimulationBodies *bodies) {
  cJSON *stars_arr = cJSON_CreateArray();
  for (size_t i = 0; i < bodies->num_stars; i++) {
    cJSON *item = cJSON_CreateObject();
    CelestialBody_Star *cb_star = &bodies->stars[i];
    cJSON_AddStringToObject(item, "name", cb_star->name);
    cJSON_AddStringToObject(item, "body_id", cb_star->body_id);
    cJSON_AddNumberToObject(item, "spectral_type", cb_star->spectral_type);
    cJSON_AddNumberToObject(item, "spectral_subtype",
                            cb_star->spectral_subtype);
    add_vector3(item, "position", cb_star->position);
    add_quaternion(item, "rotation", cb_star->rotation);
    cJSON_AddNumberToObject(item, "right_ascension_rad",
                            cb_star->right_ascension_rad);
    cJSON_AddNumberToObject(item, "declination_rad", cb_star->declination_rad);
    cJSON_AddNumberToObject(item, "distance_pc", cb_star->distance_pc);
    cJSON_AddNumberToObject(item, "mass_kg", cb_star->mass_kg);
    cJSON_AddNumberToObject(item, "radius_m", cb_star->radius_m);
    cJSON_AddNumberToObject(item, "surface_temperature_k",
                            cb_star->surface_temperature_k);
    cJSON_AddNumberToObject(item, "core_temperature_k",
                            cb_star->core_temperature_k);
    cJSON_AddNumberToObject(item, "luminosity_w", cb_star->luminosity_w);
    cJSON_AddNumberToObject(item, "bolometric_luminosity_w",
                            cb_star->bolometric_luminosity_w);
    cJSON_AddNumberToObject(item, "rotation_period_days",
                            cb_star->rotation_period_days);
    cJSON_AddNumberToObject(item, "magnetic_field_gauss",
                            cb_star->magnetic_field_gauss);

    cJSON_AddItemToArray(stars_arr, item);
  }
  cJSON_AddItemToObject(root, "stars", stars_arr);
}

void json_save_planets(cJSON *root, const LoadedSimulationBodies *bodies) {
  cJSON *planets_arr = cJSON_CreateArray();
  for (size_t i = 0; i < bodies->num_planets; i++) {
    cJSON *item = cJSON_CreateObject();
    CelestialBody_Planet *cb_planet = &bodies->planets[i];
    cJSON_AddStringToObject(item, "name", cb_planet->name);
    cJSON_AddStringToObject(item, "body_id", cb_planet->body_id);
    cJSON_AddNumberToObject(item, "host_star_index",
                            find_star_index(bodies, cb_planet->host_star_id));
    cJSON_AddNumberToObject(item, "orbit_index",
                            find_orbit_index(bodies, cb_planet->orbit));
    cJSON_AddNumberToObject(item, "planet_class", cb_planet->planet_class);
    add_vector3(item, "position", cb_planet->position);
    add_quaternion(item, "rotation", cb_planet->rotation);
    cJSON_AddNumberToObject(item, "right_ascension_rad",
                            cb_planet->right_ascension_rad);
    cJSON_AddNumberToObject(item, "declination_rad",
                            cb_planet->declination_rad);
    cJSON_AddNumberToObject(item, "distance_pc", cb_planet->distance_pc);
    cJSON_AddNumberToObject(item, "semi_major_axis_au",
                            cb_planet->semi_major_axis_au);
    cJSON_AddNumberToObject(item, "eccentricity", cb_planet->eccentricity);
    cJSON_AddNumberToObject(item, "inclination_rad",
                            cb_planet->inclination_rad);
    cJSON_AddNumberToObject(item, "longitude_ascending_node_rad",
                            cb_planet->longitude_ascending_node_rad);
    cJSON_AddNumberToObject(item, "argument_periapsis_rad",
                            cb_planet->argument_periapsis_rad);
    cJSON_AddNumberToObject(item, "mean_anomaly_rad",
                            cb_planet->mean_anomaly_rad);
    cJSON_AddNumberToObject(item, "orbital_period_days",
                            cb_planet->orbital_period_days);
    cJSON_AddNumberToObject(item, "mass_kg", cb_planet->mass_kg);
    cJSON_AddNumberToObject(item, "radius_m", cb_planet->radius_m);
    cJSON_AddNumberToObject(item, "density_kg_m3", cb_planet->density_kg_m3);
    cJSON_AddNumberToObject(item, "surface_gravity_m_s2",
                            cb_planet->surface_gravity_m_s2);
    cJSON_AddNumberToObject(item, "albedo", cb_planet->albedo);
    cJSON_AddNumberToObject(item, "surface_temperature_k",
                            cb_planet->surface_temperature_k);
    cJSON_AddNumberToObject(item, "axial_tilt_rad", cb_planet->axial_tilt_rad);
    cJSON_AddNumberToObject(item, "rotation_period_days",
                            cb_planet->rotation_period_days);
    cJSON_AddNumberToObject(item, "magnetic_field_gauss",
                            cb_planet->magnetic_field_gauss);
    cJSON_AddNumberToObject(item, "atmosphere_type",
                            cb_planet->atmosphere_type);
    cJSON_AddNumberToObject(item, "surface_pressure_pa",
                            cb_planet->surface_pressure_pa);
    cJSON_AddNumberToObject(item, "has_rings", cb_planet->has_rings);
    cJSON_AddNumberToObject(item, "ring_inner_radius_m",
                            cb_planet->ring_inner_radius_m);
    cJSON_AddNumberToObject(item, "ring_outer_radius_m",
                            cb_planet->ring_outer_radius_m);

    cJSON_AddItemToArray(planets_arr, item);
  }

  cJSON_AddItemToObject(root, "planets", planets_arr);
}

void json_save_moons(cJSON *root, const LoadedSimulationBodies *bodies) {
  cJSON *moons_arr = cJSON_CreateArray();
  for (size_t i = 0; i < bodies->num_moons; i++) {
    cJSON *item = cJSON_CreateObject();
    CelestialBody_Moon *cb_moon = &bodies->moons[i];
    cJSON_AddStringToObject(item, "name", cb_moon->name);
    cJSON_AddStringToObject(item, "body_id", cb_moon->body_id);
    cJSON_AddNumberToObject(item, "host_planet_index",
                            find_planet_index(bodies, cb_moon->host_planet_id));
    cJSON_AddNumberToObject(item, "orbit_index",
                            find_orbit_index(bodies, cb_moon->orbit));
    cJSON_AddNumberToObject(item, "moon_class", cb_moon->moon_class);
    add_vector3(item, "position", cb_moon->position);
    add_quaternion(item, "rotation", cb_moon->rotation);
    cJSON_AddNumberToObject(item, "semi_major_axis_km",
                            cb_moon->semi_major_axis_km);
    cJSON_AddNumberToObject(item, "eccentricity", cb_moon->eccentricity);
    cJSON_AddNumberToObject(item, "inclination_rad", cb_moon->inclination_rad);
    cJSON_AddNumberToObject(item, "longitude_ascending_node_rad",
                            cb_moon->longitude_ascending_node_rad);
    cJSON_AddNumberToObject(item, "argument_periapsis_rad",
                            cb_moon->argument_periapsis_rad);
    cJSON_AddNumberToObject(item, "mean_anomaly_rad",
                            cb_moon->mean_anomaly_rad);
    cJSON_AddNumberToObject(item, "orbital_period_days",
                            cb_moon->orbital_period_days);
    cJSON_AddNumberToObject(item, "mass_kg", cb_moon->mass_kg);
    cJSON_AddNumberToObject(item, "radius_m", cb_moon->radius_m);
    cJSON_AddNumberToObject(item, "surface_gravity_m_s2",
                            cb_moon->surface_gravity_m_s2);
    cJSON_AddNumberToObject(item, "is_tidally_locked",
                            cb_moon->is_tidally_locked);
    cJSON_AddNumberToObject(item, "axial_tilt_rad", cb_moon->axial_tilt_rad);
    cJSON_AddNumberToObject(item, "rotation_period_days",
                            cb_moon->rotation_period_days);
    cJSON_AddNumberToObject(item, "albedo", cb_moon->albedo);
    cJSON_AddNumberToObject(item, "surface_temperature_k",
                            cb_moon->surface_temperature_k);
    cJSON_AddNumberToObject(item, "atmosphere_type", cb_moon->atmosphere_type);
    cJSON_AddNumberToObject(item, "surface_pressure_pa",
                            cb_moon->surface_pressure_pa);

    cJSON_AddItemToArray(moons_arr, item);
  }
  cJSON_AddItemToObject(root, "moons", moons_arr);
}

void json_save_sim_date(cJSON *root, const LoadedSimulationBodies *bodies) {
  if (!bodies->sim_date.has_set_date)
    return;

  cJSON *sim_date_obj = cJSON_CreateObject();
  cJSON_AddNumberToObject(sim_date_obj, "year", bodies->sim_date.time.tm_year + 1900);
  cJSON_AddNumberToObject(sim_date_obj, "month", bodies->sim_date.time.tm_mon + 1);
  cJSON_AddNumberToObject(sim_date_obj, "day", bodies->sim_date.time.tm_mday);
  cJSON_AddNumberToObject(sim_date_obj, "hour", bodies->sim_date.time.tm_hour);
  cJSON_AddNumberToObject(sim_date_obj, "minute", bodies->sim_date.time.tm_min);
  cJSON_AddNumberToObject(sim_date_obj, "second", bodies->sim_date.time.tm_sec);

  cJSON_AddItemToObject(root, "sim_date", sim_date_obj);
}

bool json_save(const char *filename, const LoadedSimulationBodies *bodies) {
  if (!bodies)
    return false;

  cJSON *root = cJSON_CreateObject();
  json_save_sim_date(root, bodies);
  json_save_orbits(root, bodies);
  json_save_stars(root, bodies);
  json_save_planets(root, bodies);
  json_save_moons(root, bodies);

  char *json_string = cJSON_Print(root);
  cJSON_Delete(root);

  if (!json_string)
    return false;

  FILE *file = fopen(filename, "w");
  if (!file) {
    free(json_string);
    return false;
  }

  fputs(json_string, file);
  fclose(file);
  free(json_string);

  return true;
}
