#ifndef SPACE_MANMADE_SATELLITE_H
#define SPACE_MANMADE_SATELLITE_H

#include "core/space/orbit.h"
#include "core/space/planet.h"

typedef enum {
  MM_SATELLITE_CLASS_COMMUNICATIONS,
  MM_SATELLITE_CLASS_NAVIGATION,
  MM_SATELLITE_CLASS_EARTH_OBSERVATION,
  MM_SATELLITE_CLASS_SCIENTIFIC,
  MM_SATELLITE_CLASS_MILITARY
} MM_SatelliteClass;

typedef enum {
  MM_SATELLITE_MISSION_TYPE_GEOSTATIONARY,
  MM_SATELLITE_MISSION_TYPE_LOW_EARTH,
  MM_SATELLITE_MISSION_TYPE_POLAR,
  MM_SATELLITE_MISSION_TYPE_HEO
} MM_SatelliteMissionType;

typedef struct {
  char name[64];
  char body_id[32];
  char host_planet_id[32];

  MM_SatelliteClass mm_satellite_class;
  MM_SatelliteMissionType mission_type;

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

  CelestialBody_Orbit *orbit;
} CelestialBody_MM_Satellite;

#endif