#ifndef MACOS_RENDER_SHAPE_ORBIT_ELLIPSE_H
#define MACOS_RENDER_SHAPE_ORBIT_ELLIPSE_H

#include "core/space/orbit.h"
#include "macos/render/state/render_handler.h"
#import <Metal/Metal.h>

void init_orbit_graphics(RenderState *state, CelestialBody_Orbit *orbit,
                         id<MTLBuffer> *out_buffer, int *out_vertex_count);
void draw_orbit_ellipse(RenderState *state, id<MTLRenderCommandEncoder> encoder,
                        id<MTLBuffer> buffer, int vertex_count,
                        simd_float3 host_pos);

#endif
