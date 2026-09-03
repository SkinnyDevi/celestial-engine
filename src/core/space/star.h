#ifndef SPACE_STAR_H
#define SPACE_STAR_H

#include "location.h"
#include <stdint.h>

typedef enum {
  SPECTRAL_CLASS_O,
  SPECTRAL_CLASS_B,
  SPECTRAL_CLASS_A,
  SPECTRAL_CLASS_F,
  SPECTRAL_CLASS_G,
  SPECTRAL_CLASS_K,
  SPECTRAL_CLASS_M
} StarSpectralType;

typedef struct {
  char name[32];
  char body_id[32];

  StarSpectralType spectral_type;
  uint8_t spectral_subtype;

  Vector3 position; // Units to be determined (parsecs, km, au, ly)
  Quaternion rotation;
  double right_ascension_rad;
  double declination_rad;
  double distance_pc; // Distance from observer in parsecs

  double mass_kg;
  double radius_m;
  double surface_temperature_k;
  double core_temperature_k;
  double luminosity_w;
  double bolometric_luminosity_w;

  double rotation_period_days;
  double magnetic_field_gauss;
} CelestialBody_Star;

#endif