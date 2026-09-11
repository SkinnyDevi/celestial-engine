#import "moon.h"
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <stdlib.h>

#import "core/log/log.h"
#import "core/space/moon.h"
#import "core/space/units.h"
#import "macos/render/grid/displaced_mesh.h"
#import "macos/render/shape/solid_sphere.h"

simd_float4 get_moon_color(MoonClass moon_class) {
  switch (moon_class) {
  case MOON_CLASS_ROCKY:
    return (simd_float4){0.7f, 0.7f, 0.7f, 1.0f};
  case MOON_CLASS_ICY:
    return (simd_float4){0.8f, 0.9f, 1.0f, 1.0f};
  case MOON_CLASS_CAPTURED:
    return (simd_float4){0.5f, 0.4f, 0.3f, 1.0f};
  case MOON_CLASS_VOLCANIC:
    return (simd_float4){0.8f, 0.8f, 0.2f, 1.0f};
  default:
    return (simd_float4){0.8f, 0.8f, 0.8f, 1.0f};
  }
}

void MTLMoonGraphicsClass_init(MTLMoonGraphicsClass *moon,
                               RenderState *render_state) {
  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(render_state);
  if (!metal_layer)
    return;

  SolidSphereMesh mesh = generate_solid_sphere(32, 32);

  id<MTLBuffer> vertex_buffer = [metal_layer.device
      newBufferWithBytes:mesh.vertices
                  length:(sizeof(Vertex) * mesh.vertex_count)
                 options:MTLResourceStorageModeShared];

  id<MTLBuffer> index_buffer = [metal_layer.device
      newBufferWithBytes:mesh.indices
                  length:(sizeof(uint16_t) * mesh.index_count)
                 options:MTLResourceStorageModeShared];

  moon->vertex_buffer = (void *)CFBridgingRetain(vertex_buffer);
  moon->index_buffer = (void *)CFBridgingRetain(index_buffer);
  moon->index_count = mesh.index_count;

  free(mesh.vertices);
  free(mesh.indices);
}

void MTLMoonGraphicsClass_draw(MTLMoonGraphicsClass *moon,
                               RenderState *render_state, void *encoder_ptr) {
  id<MTLRenderCommandEncoder> encoder =
      (__bridge id<MTLRenderCommandEncoder>)encoder_ptr;

  simd_float4 color = get_moon_color(moon->body->moon_class);

  DisplacedMeshUniforms uniforms;
  id<MTLBuffer> uniform_buffer =
      (__bridge id<MTLBuffer>)RenderState_GetUniformBuffer(render_state);
  if (uniform_buffer) {
    memcpy(&uniforms, [uniform_buffer contents], sizeof(uniforms));
  } else {
    memset(&uniforms, 0, sizeof(uniforms));
  }

  float render_scale = (float)(moon->body->radius_m * METERS_TO_RENDER_UNITS);

  simd_float4x4 model = {0};
  model.columns[0] = simd_make_float4(render_scale, 0.0f, 0.0f, 0.0f);
  model.columns[1] = simd_make_float4(0.0f, render_scale, 0.0f, 0.0f);
  model.columns[2] = simd_make_float4(0.0f, 0.0f, render_scale, 0.0f);
  model.columns[3] = simd_make_float4(
      (float)(moon->body->position.x * METERS_TO_RENDER_UNITS),
      (float)(moon->body->position.y * METERS_TO_RENDER_UNITS),
      (float)(moon->body->position.z * METERS_TO_RENDER_UNITS), 1.0f);

  uniforms.mvpMatrix = simd_mul(uniforms.mvpMatrix, model);
  uniforms.gridColor = color;

  [encoder setVertexBytes:&uniforms length:sizeof(uniforms) atIndex:1];
  [encoder setFragmentBytes:&uniforms length:sizeof(uniforms) atIndex:1];

  if (moon->pipeline_state) {
    id<MTLRenderPipelineState> pipeline =
        (__bridge id<MTLRenderPipelineState>)moon->pipeline_state;
    [encoder setRenderPipelineState:pipeline];
  }

  if (moon->vertex_buffer) {
    id<MTLBuffer> vbuf = (__bridge id<MTLBuffer>)moon->vertex_buffer;
    [encoder setVertexBuffer:vbuf offset:0 atIndex:0];
  }

  if (moon->index_buffer) {
    id<MTLBuffer> ibuf = (__bridge id<MTLBuffer>)moon->index_buffer;
    [encoder drawIndexedPrimitives:MTLPrimitiveTypeTriangle
                        indexCount:moon->index_count
                         indexType:MTLIndexTypeUInt16
                       indexBuffer:ibuf
                 indexBufferOffset:0];
  }
}

MTLMoonGraphicsClass *MTLMoonGraphics_Create(CelestialBody_Moon *body) {
  MTLMoonGraphicsClass *moon = malloc(sizeof(MTLMoonGraphicsClass));
  if (!moon) {
    LOG_ERROR("Failed to allocate memory for moon graphics for moon: %s (%s)",
              body->name, body->body_id);
    return NULL;
  }

  moon->body = body;
  moon->vertex_buffer = NULL;
  moon->index_buffer = NULL;
  moon->index_count = 0;
  moon->pipeline_state = NULL;

  return moon;
}

void MTLMoonGraphics_Destroy(MTLMoonGraphicsClass *moon_graphics) {
  if (!moon_graphics)
    return;

  if (moon_graphics->vertex_buffer)
    CFRelease(moon_graphics->vertex_buffer);
  if (moon_graphics->index_buffer)
    CFRelease(moon_graphics->index_buffer);
  if (moon_graphics->pipeline_state)
    CFRelease(moon_graphics->pipeline_state);

  free(moon_graphics);
}
