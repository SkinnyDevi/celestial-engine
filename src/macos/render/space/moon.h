#ifndef MACOS_RENDER_SPACE_MOON_H
#define MACOS_RENDER_SPACE_MOON_H

#include "core/space/moon.h"
#include "macos/render/state/render_handler.h"

typedef struct MTLPlanetGraphicsClass MTLPlanetGraphicsClass;

typedef struct MTLMoonGraphicsClass {
  CelestialBody_Moon *body;
  MTLPlanetGraphicsClass *host_planet;

  void *vertex_buffer;
  void *index_buffer;
  int index_count;

  void *pipeline_state;
} MTLMoonGraphicsClass;

MTLMoonGraphicsClass *MTLMoonGraphics_Create(CelestialBody_Moon *body);
void MTLMoonGraphicsClass_draw(MTLMoonGraphicsClass *moon,
                               RenderState *render_state, void *encoder_ptr);
void MTLMoonGraphicsClass_init(MTLMoonGraphicsClass *moon,
                               RenderState *render_state);
void MTLMoonGraphics_Destroy(MTLMoonGraphicsClass *moon_graphics);

void init_celestial_body_moons(RenderState *render_state);

#endif
