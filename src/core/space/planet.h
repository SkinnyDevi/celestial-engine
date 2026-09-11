#ifndef SPACE_PLANET_H
#define SPACE_PLANET_H

#include "location.h"
#include <stdint.h>

typedef enum {
  PLANET_CLASS_TERRESTRIAL,
  PLANET_CLASS_GAS_GIANT,
  PLANET_CLASS_ICE_GIANT,
  PLANET_CLASS_DWARF,
  PLANET_CLASS_ROGUE
} PlanetClass;

typedef enum {
  ATMOSPHERE_NONE,
  ATMOSPHERE_THIN,          // Mars
  ATMOSPHERE_STANDARD,      // Earth
  ATMOSPHERE_DENSE,         // Venus
  ATMOSPHERE_THICK_ENVELOPE // Gas giants
} AtmosphereType;

typedef struct {
  char name[32];
  char body_id[32];
  char host_star_id[32];

  PlanetClass planet_class;

  Vector3 position;
  Quaternion rotation;

  double right_ascension_rad;
  double declination_rad;
  double distance_pc;

  double semi_major_axis_au;
  double eccentricity;
  double inclination_rad;
  double longitude_ascending_node_rad;
  double argument_periapsis_rad;
  double mean_anomaly_rad;
  double orbital_period_days;

  double mass_kg;
  double radius_m;
  double density_kg_m3;
  double surface_gravity_m_s2;

  double albedo; // 0.0 to 1.0 (lighting for shaders)
  double surface_temperature_k;
  double axial_tilt_rad; // Obliquity (seasons/poles)
  double rotation_period_days;
  double magnetic_field_gauss; // Useful for rendering auroras/magnetospheres

  AtmosphereType atmosphere_type;
  double surface_pressure_pa;

  uint8_t has_rings;
  double ring_inner_radius_m;
  double ring_outer_radius_m;
} CelestialBody_Planet;

#endif