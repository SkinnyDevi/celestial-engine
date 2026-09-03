#ifndef MACOS_RENDER_CELESTIAL_OBJECT_H
#define MACOS_RENDER_CELESTIAL_OBJECT_H

#include "macos/render/state/render_handler.h"

typedef struct MTLCelestialBodyGraphicsClass {
  void (*init)(struct MTLCelestialBodyGraphicsClass *self, RenderState *render_state);
  void (*draw)(struct MTLCelestialBodyGraphicsClass *self, RenderState *render_state, void *encoder);
} MTLCelestialBodyGraphicsClass;

#endif // MACOS_RENDER_CELESTIAL_OBJECT_H
