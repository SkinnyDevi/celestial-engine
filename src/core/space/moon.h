#ifndef SPACE_MOON_H
#define SPACE_MOON_H

#include "planet.h"

typedef enum {
  MOON_CLASS_ROCKY,    // Like Luna
  MOON_CLASS_ICY,      // Like Europa
  MOON_CLASS_CAPTURED, // Like Phobos
  MOON_CLASS_VOLCANIC  // Like Io
} MoonClass;

typedef struct {
  char name[32];
  char body_id[32];
  char host_planet_id[32];

  MoonClass moon_class;

  Vector3 position;
  Quaternion rotation;

  double semi_major_axis_km;
  double eccentricity;
  double inclination_rad;
  double longitude_ascending_node_rad;
  double argument_periapsis_rad;
  double mean_anomaly_rad;
  double orbital_period_days;

  double mass_kg;
  double radius_m;
  double surface_gravity_m_s2;

  uint8_t is_tidally_locked;
  double axial_tilt_rad;
  double rotation_period_days;

  double albedo;
  double surface_temperature_k;

  AtmosphereType atmosphere_type;
  double surface_pressure_pa;
} CelestialBody_Moon;

#endif