#import "displaced_mesh.h"
#import "core/data/math.h"
#import "core/log/log.h"

#import "macos/debug/fps_counter.h"
#import "macos/render/camera/camera.h"
#import "macos/render/state/render_state.h"

#import <AppKit/AppKit.h>
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <stdlib.h>

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
  if (zoom <= 0.0f)
    return 1.0f;

  float exponent = floorf(log10f(zoom));
  float power_of_ten = powf(10.0f, exponent);

  float fraction = zoom / power_of_ten; // [1.0, 10.0)

  // Adjusts square density in the grid
  float base_spacing;
  if (fraction < 2.0f)
    base_spacing = 0.1f;
  else if (fraction < 5.0f)
    base_spacing = 0.2f;
  else
    base_spacing = 0.5f;

  return base_spacing * power_of_ten;
}

void toggle_grid_visibility(RenderState *state) {
  if (!state)
    return;
  bool current = RenderState_IsGridVisible(state);
  RenderState_SetGridVisible(state, !current);
}

static bool grid_initialized = false;
void update_grid_scale(RenderState *state) {
  if (!grid_initialized) {
    init_grid_mesh(state, 100, 1.0f);
    grid_initialized = true;
  }
}

void draw_grid(RenderState *state, void *encoder_ptr) {
  if (!RenderState_IsGridVisible(state))
    return;

  id<MTLRenderCommandEncoder> encoder =
      (__bridge id<MTLRenderCommandEncoder>)encoder_ptr;

  id<MTLBuffer> vertex_buffer =
      (__bridge id<MTLBuffer>)RenderState_GetVec3Buffer(state);
  id<MTLBuffer> uniform_buffer =
      (__bridge id<MTLBuffer>)RenderState_GetUniformBuffer(state);

  Camera *camera = RenderState_GetCamera(state);
  float spacing = dynamic_grid_spacing(camera->zoom);

  float snapped_x = floorf(camera->center.x / spacing) * spacing;
  float snapped_z = floorf(camera->center.z / spacing) * spacing;

  Camera temp_cam = *camera;
  temp_cam.center.x = camera->center.x - snapped_x;
  temp_cam.center.y = camera->center.y;
  temp_cam.center.z = camera->center.z - snapped_z;

  simd_float4x4 relative_view = camera_view_matrix(&temp_cam);

  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  float aspect = metal_layer.drawableSize.width /
                 MAX(metal_layer.drawableSize.height, 1.0f);
  float near_plane, far_plane;
  camera_get_clipping_planes(camera, &near_plane, &far_plane);
  simd_float4x4 projection = camera_perspective(70.0f * (float)M_PI / 180.0f,
                                                aspect, near_plane, far_plane);

  DisplacedMeshUniforms uniforms;
  memcpy(&uniforms, [uniform_buffer contents], sizeof(uniforms));

  simd_float4x4 scale = make_scale_matrix(spacing);
  uniforms.mvpMatrix = simd_mul(projection, simd_mul(relative_view, scale));

  [encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
  [encoder setVertexBytes:&uniforms length:sizeof(uniforms) atIndex:1];
  [encoder setFragmentBytes:&uniforms length:sizeof(uniforms) atIndex:1];
  [encoder drawPrimitives:MTLPrimitiveTypeLine
              vertexStart:0
              vertexCount:RenderState_GetVertexCount(state)];
}