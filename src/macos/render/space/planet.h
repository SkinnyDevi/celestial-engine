#ifndef MACOS_RENDER_SPACE_PLANET_H
#define MACOS_RENDER_SPACE_PLANET_H

#include "core/space/planet.h"
#include "macos/render/state/render_handler.h"

typedef struct {
  CelestialBody_Planet *body;

  void *vertex_buffer;
  void *index_buffer;
  int index_count;

  void *pipeline_state;
} MTLPlanetGraphicsClass;

MTLPlanetGraphicsClass *MTLPlanetGraphics_Create(CelestialBody_Planet *body);
void MTLPlanetGraphicsClass_draw(MTLPlanetGraphicsClass *planet,
                                 RenderState *render_state, void *encoder_ptr);
void MTLPlanetGraphicsClass_init(MTLPlanetGraphicsClass *planet,
                                 RenderState *render_state);
void MTLPlanetGraphics_Destroy(MTLPlanetGraphicsClass *planet_graphics);

#endif
