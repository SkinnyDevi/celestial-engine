#ifndef SPACE_ORBIT_H
#define SPACE_ORBIT_H

#include "location.h"

typedef struct {
  double semimajor_axis;
  double eccentricity;
  double inclination;
  double longitude_of_ascending_node;
  double argument_of_periapsis;
  double mean_anomaly_at_epoch;
  double orbital_period_days;

  double mean_anomaly;
  double true_anomaly;

  Vector3 center_position;
} CelestialBody_Orbit;

Vector3 orbit_calculate_position(CelestialBody_Orbit *orbit,
                                 double time_in_days);
Vector3 orbit_get_ellipse_vector(CelestialBody_Orbit *orbit);
Vector3 *orbit_get_all_positions(CelestialBody_Orbit *orbit);
#endif