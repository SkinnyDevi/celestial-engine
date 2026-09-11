#ifndef MACOS_RENDER_DEFINED_MOONS_H
#define MACOS_RENDER_DEFINED_MOONS_H

#include "core/space/moon.h"

CelestialBody_Moon PHOBOS = {
    .name = "Phobos",
    .body_id = "PHOBOS",
    .host_planet_id = "MARS",
    .moon_class = MOON_CLASS_ROCKY,
    // ~9,377 km from Mars
    .position = {.x = 9.3772e6, .y = 0, .z = 0},
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 11262, // Average radius
    .mass_kg = 1.0659e16,
    .surface_temperature_k = 233, // Average surface temperature
    .atmosphere_type = ATMOSPHERE_NONE,
};

CelestialBody_Moon DEIMOS = {
    .name = "Deimos",
    .body_id = "DEIMOS",
    .host_planet_id = "MARS",
    .moon_class = MOON_CLASS_ROCKY,
    // ~23,460 km from Mars
    .position = {.x = 23.460e6, .y = 0, .z = 0},
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 6255, // Average radius
    .mass_kg = 1.4762e15,
    .surface_temperature_k = 233, // Average surface temperature
    .atmosphere_type = ATMOSPHERE_NONE,
};

CelestialBody_Moon LUNA = {
    .name = "Moon",
    .body_id = "LUNA",
    .host_planet_id = "EARTH",
    .moon_class = MOON_CLASS_ROCKY,
    // 384,400 km from Earth
    .position = {.x = 384400000.0, .y = 0, .z = 0},
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 1737400,
    .mass_kg = 7.342e22,
    .surface_temperature_k = 250,
    .atmosphere_type = ATMOSPHERE_NONE,
};

CelestialBody_Moon IO = {
    .name = "Io",
    .body_id = "IO",
    .host_planet_id = "JUPITER",
    .moon_class = MOON_CLASS_ROCKY,
    // 421,700 km from Jupiter
    .position = {.x = 421700000.0, .y = 0, .z = 0},
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 1821600,
    .mass_kg = 8.933e22,
    .surface_temperature_k = 130,
    .atmosphere_type = ATMOSPHERE_THIN,
};

CelestialBody_Moon EUROPA = {
    .name = "Europa",
    .body_id = "EUROPA",
    .host_planet_id = "JUPITER",
    .moon_class = MOON_CLASS_ROCKY,
    // 671,100 km from Jupiter
    .position = {.x = 671100000.0, .y = 0, .z = 0},
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 1560800,
    .mass_kg = 4.7999e22,
    .surface_temperature_k = 102,
    .atmosphere_type = ATMOSPHERE_THIN,
};

CelestialBody_Moon TITAN = {
    .name = "Titan",
    .body_id = "TITAN",
    .host_planet_id = "SATURN",
    .moon_class = MOON_CLASS_ROCKY,
    // ~1,222,000 km from Saturn
    .position = {.x = 1221870000.0, .y = 0, .z = 0},
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 2574700,
    .mass_kg = 1.3455e23,
    .surface_temperature_k = 94,
    .atmosphere_type = ATMOSPHERE_DENSE,
};

CelestialBody_Moon TRITON = {
    .name = "Triton",
    .body_id = "TRITON",
    .host_planet_id = "NEPTUNE",
    .moon_class = MOON_CLASS_ROCKY,
    // ~354,760 km from Neptune
    .position = {.x = 354760000.0, .y = 0, .z = 0},
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 1353600,
    .mass_kg = 2.1404e22,
    .surface_temperature_k = 38, // Very cold, nitrogen ice
    .atmosphere_type = ATMOSPHERE_THIN,
};

#endif
