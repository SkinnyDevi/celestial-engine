#import "graphics.h"
#import "core/data/dyn_array.h"
#include "core/log/log.h"

#import "core/cli/instance_data.h"

#import "macos/render/space/moon.h"
#import "macos/render/space/planet.h"
#import "macos/render/space/star.h"

#import <string.h>

void resolve_celestial_body_hierarchy(RenderState *render_state) {
  DynamicArray *stars = RenderState_GetStars(render_state);
  DynamicArray *planets = RenderState_GetPlanets(render_state);
  DynamicArray *moons = RenderState_GetMoons(render_state);

  size_t star_count = DynamicArray_length(stars);
  size_t planet_count = DynamicArray_length(planets);
  size_t moon_count = DynamicArray_length(moons);

  // Link planets to host stars
  for (size_t i = 0; i < planet_count; i++) {
    MTLPlanetGraphicsClass *planet;
    DynamicArray_get(planets, i, &planet);
    planet->host_star = NULL;

    for (size_t j = 0; j < star_count; j++) {
      MTLStarGraphicsClass *star;
      DynamicArray_get(stars, j, &star);
      if (strcmp(planet->body->host_star_id, star->body->body_id) == 0) {
        planet->host_star = star;
        break;
      }
    }
  }

  // Link moons to host planets
  for (size_t i = 0; i < moon_count; i++) {
    MTLMoonGraphicsClass *moon;
    DynamicArray_get(moons, i, &moon);
    moon->host_planet = NULL;

    for (size_t j = 0; j < planet_count; j++) {
      MTLPlanetGraphicsClass *planet;
      DynamicArray_get(planets, j, &planet);
      if (strcmp(moon->body->host_planet_id, planet->body->body_id) == 0) {
        moon->host_planet = planet;
        break;
      }
    }
  }
}

void init_celestial_bodies(RenderState *render_state) {
  if (!cli_is_using_data_file()) {
    LOG_WARN("No data file provided, using hardcoded celestial bodies", NULL);
    init_celestial_body_stars(render_state);
    init_celestial_body_planets(render_state);
    init_celestial_body_moons(render_state);
  } else {
    LOG_INFO("Loading celestial bodies from data file %s",
             cli_get_data_file_path());

    LoadedSimulationBodies *bodies = cli_get_sim_bodies();
    load_celestial_body_stars_from_file(render_state, bodies);
    load_celestial_body_planets_from_file(render_state, bodies);
    load_celestial_body_moons_from_file(render_state, bodies);
  }

  resolve_celestial_body_hierarchy(render_state);
}