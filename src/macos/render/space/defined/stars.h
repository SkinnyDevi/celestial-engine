#ifndef MACOS_RENDER_DEFINED_STARS_H
#define MACOS_RENDER_DEFINED_STARS_H

#include "core/space/star.h"
#include "macos/render/space/star.h"

CelestialBody_Star SUN = {
    .name = "Sun",
    .body_id = "SUN",
    .spectral_type = SPECTRAL_CLASS_G,
    .spectral_subtype = 8,
    .position = {.x = 0, .y = 0, .z = 0},
    .rotation = {.x = 0, .y = 0, .z = 0, .w = 1},
    .right_ascension_rad = 0,
    .declination_rad = 0,
    .distance_pc = 0,
    .mass_kg = 1.98847e30,
    .radius_m = 696340000,
    .surface_temperature_k = 5772,
    .core_temperature_k = 15000000,
    .luminosity_w = 3.828e26,
    .bolometric_luminosity_w = 3.828e26,
    .rotation_period_days = 25.05,
    .magnetic_field_gauss = 2,
};

#endif