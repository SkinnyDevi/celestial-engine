#import "orbit_ellipse.h"
#import "core/log/log.h"
#import "core/space/units.h"
#import "macos/render/grid/displaced_mesh.h"
#import "macos/render/shape/vertex.h"
#import <QuartzCore/QuartzCore.h>
#import <stdlib.h>

void init_orbit_graphics(RenderState *state, CelestialBody_Orbit *orbit,
                         id<MTLBuffer> *out_buffer, int *out_vertex_count) {
  if (!state || !orbit || !out_buffer || !out_vertex_count)
    return;

  Vector3 *positions = orbit_get_all_positions(orbit);
  if (!positions) {
    LOG_ERROR("Failed to get orbit positions.", NULL);
    return;
  }

  int days = (int)orbit->orbital_period_days;
  int vertex_count = days + 1; // +1 to close the loop

  Vertex *vertices = malloc(sizeof(Vertex) * vertex_count);
  if (!vertices) {
    free(positions);
    return;
  }

  for (int i = 0; i < days; i++) {
    // We subtract the orbit->center_position because we want the orbit points
    // relative to the host
    float x = (float)((positions[i].x - orbit->center_position.x) *
                      METERS_TO_RENDER_UNITS);
    float y = (float)((positions[i].y - orbit->center_position.y) *
                      METERS_TO_RENDER_UNITS);
    float z = (float)((positions[i].z - orbit->center_position.z) *
                      METERS_TO_RENDER_UNITS);

    vertices[i].position.x = x;
    vertices[i].position.y = y;
    vertices[i].position.z = z;
  }

  // Close the loop
  vertices[days] = vertices[0];

  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);

  *out_buffer =
      [metal_layer.device newBufferWithBytes:vertices
                                      length:(sizeof(Vertex) * vertex_count)
                                     options:MTLResourceStorageModeShared];
  *out_vertex_count = vertex_count;

  free(vertices);
  free(positions);
}

void draw_orbit_ellipse(RenderState *state, id<MTLRenderCommandEncoder> encoder,
                        id<MTLBuffer> buffer, int vertex_count,
                        simd_float3 host_pos) {
  if (!buffer || vertex_count == 0)
    return;

  id<MTLBuffer> uniform_buffer =
      (__bridge id<MTLBuffer>)RenderState_GetUniformBuffer(state);
  if (!uniform_buffer)
    return;

  DisplacedMeshUniforms uniforms;
  memcpy(&uniforms, [uniform_buffer contents], sizeof(uniforms));

  // Translate orbit to the host's actual visual position
  simd_float4x4 model = {0};
  model.columns[0] = simd_make_float4(1.0f, 0.0f, 0.0f, 0.0f);
  model.columns[1] = simd_make_float4(0.0f, 1.0f, 0.0f, 0.0f);
  model.columns[2] = simd_make_float4(0.0f, 0.0f, 1.0f, 0.0f);
  model.columns[3] = simd_make_float4(host_pos.x, host_pos.y, host_pos.z, 1.0f);

  uniforms.mvpMatrix = simd_mul(uniforms.mvpMatrix, model);
  uniforms.gridColor =
      (simd_float4){1.0f, 1.0f, 1.0f, 0.5f}; // Bright red opaque line

  [encoder setVertexBytes:&uniforms length:sizeof(uniforms) atIndex:1];
  [encoder setFragmentBytes:&uniforms length:sizeof(uniforms) atIndex:1];
  [encoder setVertexBuffer:buffer offset:0 atIndex:0];

  // Assuming the line rendering pipeline is currently bound
  [encoder drawPrimitives:MTLPrimitiveTypeLineStrip
              vertexStart:0
              vertexCount:vertex_count];
}
