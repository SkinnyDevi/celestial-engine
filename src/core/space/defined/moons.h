#ifndef MACOS_RENDER_DEFINED_MOONS_H
#define MACOS_RENDER_DEFINED_MOONS_H

#include "core/space/moon.h"

CelestialBody_Moon LUNA = {
    .name = "Moon",
    .body_id = "LUNA",
    .host_planet_id = "EARTH",
    .moon_class = MOON_CLASS_ROCKY,
    // Earth's position + 384,400 km
    .position = {.x = 149597870700.0 + 384400000.0, .y = 0, .z = 0},
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 1737400,
    .mass_kg = 7.342e22,
    .surface_temperature_k = 250,
    .atmosphere_type = ATMOSPHERE_NONE,
};

#endif
