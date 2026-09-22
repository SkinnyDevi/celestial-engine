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
static CelestialBody_Orbit ORBIT_MERCURY_AROUND_SUN = {
    .semimajor_axis = 57909050000.0,
    .eccentricity = 0.2056,
    .inclination = 7.005 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = 87.969,
    .center_position = {0, 0, 0},
};

static CelestialBody_Orbit ORBIT_VENUS_AROUND_SUN = {
    .semimajor_axis = 108208000000.0,
    .eccentricity = 0.0067,
    .inclination = 3.394 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = 224.701,
    .center_position = {0, 0, 0},
};

static CelestialBody_Orbit ORBIT_MARS_AROUND_SUN = {
    .semimajor_axis = 227939200000.0,
    .eccentricity = 0.0934,
    .inclination = 1.850 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = 686.980,
    .center_position = {0, 0, 0},
};

static CelestialBody_Orbit ORBIT_JUPITER_AROUND_SUN = {
    .semimajor_axis = 778547200000.0,
    .eccentricity = 0.0489,
    .inclination = 1.303 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = 4332.589,
    .center_position = {0, 0, 0},
};

static CelestialBody_Orbit ORBIT_SATURN_AROUND_SUN = {
    .semimajor_axis = 1433449370000.0,
    .eccentricity = 0.0565,
    .inclination = 2.485 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = 10759.22,
    .center_position = {0, 0, 0},
};

static CelestialBody_Orbit ORBIT_URANUS_AROUND_SUN = {
    .semimajor_axis = 2872463710000.0,
    .eccentricity = 0.0463,
    .inclination = 0.772 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = 30688.5,
    .center_position = {0, 0, 0},
};

static CelestialBody_Orbit ORBIT_NEPTUNE_AROUND_SUN = {
    .semimajor_axis = 4495060000000.0,
    .eccentricity = 0.0086,
    .inclination = 1.769 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = 60182.0,
    .center_position = {0, 0, 0},
};

static CelestialBody_Orbit ORBIT_PHOBOS_AROUND_MARS = {
    .semimajor_axis = 9376000.0,
    .eccentricity = 0.0151,
    .inclination = 1.093 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = 0.3189,
    .center_position = {0, 0, 0},
};

static CelestialBody_Orbit ORBIT_DEIMOS_AROUND_MARS = {
    .semimajor_axis = 23463000.0,
    .eccentricity = 0.0002,
    .inclination = 0.93 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = 1.263,
    .center_position = {0, 0, 0},
};

static CelestialBody_Orbit ORBIT_IO_AROUND_JUPITER = {
    .semimajor_axis = 421700000.0,
    .eccentricity = 0.0041,
    .inclination = 0.05 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = 1.769,
    .center_position = {0, 0, 0},
};

static CelestialBody_Orbit ORBIT_EUROPA_AROUND_JUPITER = {
    .semimajor_axis = 671034000.0,
    .eccentricity = 0.0094,
    .inclination = 0.47 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = 3.551,
    .center_position = {0, 0, 0},
};

static CelestialBody_Orbit ORBIT_TITAN_AROUND_SATURN = {
    .semimajor_axis = 1221870000.0,
    .eccentricity = 0.0288,
    .inclination = 0.348 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = 15.945,
    .center_position = {0, 0, 0},
};

static CelestialBody_Orbit ORBIT_TRITON_AROUND_NEPTUNE = {
    .semimajor_axis = 354759000.0,
    .eccentricity = 0.000016,
    .inclination = 156.885 * 3.14159265358979323846 / 180.0,
    .orbital_period_days = -5.877, // Retrograde
    .center_position = {0, 0, 0},
};

#endif