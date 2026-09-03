#ifndef MACOS_RENDER_SPACE_STAR_H
#define MACOS_RENDER_SPACE_STAR_H

#include "core/space/star.h"
#include "macos/render/space/celestial_object.h"

typedef struct {
  CelestialBody_Star *body;

  void *vertex_buffer;
  void *index_buffer;
  int index_count;

  void *pipeline_state;
} MTLStarGraphicsClass;

MTLStarGraphicsClass *MTLStarGraphics_Create(CelestialBody_Star *body);
void MTLStarGraphicsClass_draw(MTLStarGraphicsClass *star,
                               RenderState *render_state, void *encoder_ptr);
void MTLStarGraphicsClass_init(MTLStarGraphicsClass *star,
                               RenderState *render_state);
void MTLStarGraphics_Destroy(MTLStarGraphicsClass *star_graphics);

#endif