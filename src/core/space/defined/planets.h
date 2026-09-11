#ifndef MACOS_RENDER_DEFINED_PLANETS_H
#define MACOS_RENDER_DEFINED_PLANETS_H

#include "core/space/planet.h"

CelestialBody_Planet EARTH = {
    .name = "Earth",
    .body_id = "EARTH",
    .host_star_id = "SUN",
    .planet_class = PLANET_CLASS_TERRESTRIAL,
    .position = {.x = 149597870700.0, .y = 0, .z = 0}, // 1 AU
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 6371000,
    .mass_kg = 5.972e24,
    .surface_temperature_k = 288,
    .atmosphere_type = ATMOSPHERE_STANDARD,
    .has_rings = 0,
};

CelestialBody_Planet MARS = {
    .name = "Mars",
    .body_id = "MARS",
    .host_star_id = "SUN",
    .planet_class = PLANET_CLASS_TERRESTRIAL,
    .position = {.x = 227940000000.0, .y = 0, .z = 0}, // 1.52 AU
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 3389500,
    .mass_kg = 6.39e23,
    .surface_temperature_k = 210,
    .atmosphere_type = ATMOSPHERE_THIN,
    .has_rings = 0,
};

CelestialBody_Planet JUPITER = {
    .name = "Jupiter",
    .body_id = "JUPITER",
    .host_star_id = "SUN",
    .planet_class = PLANET_CLASS_GAS_GIANT,
    .position = {.x = 778500000000.0, .y = 0, .z = 0}, // 5.2 AU
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 69911000,
    .atmosphere_type = ATMOSPHERE_THICK_ENVELOPE,
    .has_rings = 1,
};

#endif
