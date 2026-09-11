#import "displaced_mesh.h"
#include "macos/debug/fps_counter.h"
#import <AppKit/AppKit.h>
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <stdlib.h>

#import "core/log/log.h"
#import "macos/render/state/render_handler.h"

Vertex *generate_grid_vertices(int grid_size, float spacing, int num_vertices) {
  Vertex *vertices = calloc(num_vertices, sizeof(Vertex));

  int index = 0;
  for (int i = -grid_size; i <= grid_size; i++) {
    // X-Axis Parallel lines
    vertices[index++].position =
        (PackedFloat3){i * spacing, 0.0f, -grid_size * spacing};
    vertices[index++].position =
        (PackedFloat3){i * spacing, 0.0f, grid_size * spacing};

    // Z-Axis Parallel lines
    vertices[index++].position =
        (PackedFloat3){-grid_size * spacing, 0.0f, i * spacing};
    vertices[index++].position =
        (PackedFloat3){grid_size * spacing, 0.0f, i * spacing};
  }

  return vertices;
}

// CPU side
static bool debug_msg_init = false;
void init_grid_mesh(RenderState *state, int grid_size, float spacing) {
  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);

  int num_vertices = (grid_size * 2 + 1) * 4;
  Vertex *vertices = generate_grid_vertices(grid_size, spacing, num_vertices);
  id<MTLBuffer> vertex_buffer =
      [metal_layer.device newBufferWithBytes:vertices
                                      length:(sizeof(Vertex) * num_vertices)
                                     options:MTLResourceStorageModeShared];
  RenderState_SetVec3Buffer(state, (__bridge void *)vertex_buffer);
  RenderState_SetVertexCount(state, num_vertices);
  free(vertices);

  if (!debug_msg_init) {
    LOG_DEBUG("Grid mesh: %d vertices, buffer size: %lu bytes", num_vertices,
              (unsigned long)(sizeof(Vertex) * num_vertices));
    debug_msg_init = true;
  }
}

float dynamic_grid_spacing(float zoom) {
  float spacing_factor;

  if (zoom < 5.0f)
    spacing_factor = 0.05f;
  else if (zoom < 10.0f)
    spacing_factor = 0.1f;
  else if (zoom < 30.0f)
    spacing_factor = 0.2f;
  else if (zoom < 60.0f)
    spacing_factor = 0.5f;
  else if (zoom < 100.0f)
    spacing_factor = 1.0f;
  else if (zoom < 150.0f)
    spacing_factor = 2.0f;
  else if (zoom < 500.0f)
    spacing_factor = 5.0f;
  else if (zoom < 1000.0f)
    spacing_factor = 10.0f;
  else
    spacing_factor = 20.0f;

  return powf(2.0f, floorf(log10f(zoom * 2.0f))) * spacing_factor;
}

void toggle_grid_visibility(RenderState *state) {
  if (!state)
    return;
  bool current = RenderState_IsGridVisible(state);
  RenderState_SetGridVisible(state, !current);
}

void update_grid_scale(RenderState *state) {
  Camera *camera = RenderState_GetCamera(state);

  float spacing = dynamic_grid_spacing(camera->zoom);
  int subdivisions = 20 + (int)((camera->zoom / spacing) * 3.0f);
  int num_vertices = (subdivisions * 2 + 1) * 4;
  init_grid_mesh(state, subdivisions, spacing);
}