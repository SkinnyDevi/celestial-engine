#ifndef MACOS_RENDER_DEFINED_PLANETS_H
#define MACOS_RENDER_DEFINED_PLANETS_H

#include "core/space/planet.h"

CelestialBody_Planet VENUS = {
    .name = "Venus",
    .body_id = "VENUS",
    .host_star_id = "SUN",
    .planet_class = PLANET_CLASS_TERRESTRIAL,
    .position = {.x = 108200000000.0, .y = 0, .z = 0},
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 6051000,
    .mass_kg = 4.867e24,
    .surface_temperature_k = 737,
    .atmosphere_type = ATMOSPHERE_DENSE,
    .has_rings = 0,
};

CelestialBody_Planet MERCURY = {
    .name = "Mercury",
    .body_id = "MERCURY",
    .host_star_id = "SUN",
    .planet_class = PLANET_CLASS_TERRESTRIAL,
    .position = {.x = 57900000000.0, .y = 0, .z = 0},
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 2439700,
    .mass_kg = 3.301e23,
    .surface_temperature_k = 440,
    .atmosphere_type = ATMOSPHERE_THIN,
    .has_rings = 0,
};

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

CelestialBody_Planet SATURN = {
    .name = "Saturn",
    .body_id = "SATURN",
    .host_star_id = "SUN",
    .planet_class = PLANET_CLASS_GAS_GIANT,
    .position = {.x = 1433500000000.0, .y = 0, .z = 0}, // 9.58 AU
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 58232000,
    .atmosphere_type = ATMOSPHERE_THICK_ENVELOPE,
    .has_rings = 1,
};

CelestialBody_Planet URANUS = {
    .name = "Uranus",
    .body_id = "URANUS",
    .host_star_id = "SUN",
    .planet_class = PLANET_CLASS_ICE_GIANT,
    .position = {.x = 2872500000000.0, .y = 0, .z = 0}, // 19.2 AU
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 25362000,
    .atmosphere_type = ATMOSPHERE_THICK_ENVELOPE,
    .has_rings = 1,
};

CelestialBody_Planet NEPTUNE = {
    .name = "Neptune",
    .body_id = "NEPTUNE",
    .host_star_id = "SUN",
    .planet_class = PLANET_CLASS_ICE_GIANT,
    .position = {.x = 4495100000000.0, .y = 0, .z = 0}, // 30.1 AU
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .radius_m = 24622000,
    .atmosphere_type = ATMOSPHERE_THICK_ENVELOPE,
    .has_rings = 1,
};

#endif
