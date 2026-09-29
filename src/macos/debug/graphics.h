#ifndef MACOS_DEBUG_RENDER_GRAPHICS_H
#define MACOS_DEBUG_RENDER_GRAPHICS_H

#include "macos/render/state/render_state.h"

void generate_debug_graphics(RenderState *state);
void draw_debug_graphics(RenderState *state, void *encoder);

#endif