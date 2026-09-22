#ifndef CORE_SPACE_DEFINED_ORBITS_H
#define CORE_SPACE_DEFINED_ORBITS_H

#include "core/space/orbit.h"

static CelestialBody_Orbit ORBIT_EARTH_AROUND_SUN = {
    .semimajor_axis = 149597870700.0,
    .eccentricity = 0.01671,
    .inclination = 0.0,
    .longitude_of_ascending_node = 0.0,
    .argument_of_periapsis = 282.961 * 3.14159265358979323846 / 180.0,
    .mean_anomaly_at_epoch = 280.460 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = 365.256,
    .mean_anomaly = 280.460 * 3.14159265358979323846 / 180.0,
    .true_anomaly = 0.0,
    .center_position = {0, 0, 0},
};

static CelestialBody_Orbit ORBIT_LUNA_AROUND_EARTH = {
    .semimajor_axis = 384400000.0,
    .eccentricity = 0.0549,
    .inclination = 5.145 * 3.14159265358979323846 / 180.0,
    .longitude_of_ascending_node = 0.0,
    .argument_of_periapsis = 282.961 * 3.14159265358979323846 / 180.0,
    .mean_anomaly_at_epoch = 280.460 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = 27.321661,
    .mean_anomaly = 280.460 * 3.14159265358979323846 / 180.0,
    .true_anomaly = 0.0,
    .center_position = {0, 0, 0},
};

#endif