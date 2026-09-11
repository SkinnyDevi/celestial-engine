#import "planet.h"
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <stdlib.h>

#import "core/log/log.h"
#import "core/space/planet.h"
#import "core/space/units.h"
#import "macos/render/grid/displaced_mesh.h"
#import "macos/render/shape/solid_sphere.h"

simd_float4 get_planet_color(PlanetClass planet_class) {
  switch (planet_class) {
  case PLANET_CLASS_TERRESTRIAL:
    return (simd_float4){0.2f, 0.6f, 0.2f, 1.0f};
  case PLANET_CLASS_GAS_GIANT:
    return (simd_float4){0.8f, 0.7f, 0.5f, 1.0f};
  case PLANET_CLASS_ICE_GIANT:
    return (simd_float4){0.4f, 0.6f, 1.0f, 1.0f};
  case PLANET_CLASS_DWARF:
    return (simd_float4){0.6f, 0.6f, 0.6f, 1.0f};
  case PLANET_CLASS_ROGUE:
    return (simd_float4){0.3f, 0.1f, 0.3f, 1.0f};
  default:
    return (simd_float4){1.0f, 1.0f, 1.0f, 1.0f};
  }
}

void MTLPlanetGraphicsClass_init(MTLPlanetGraphicsClass *planet,
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

  planet->vertex_buffer = (void *)CFBridgingRetain(vertex_buffer);
  planet->index_buffer = (void *)CFBridgingRetain(index_buffer);
  planet->index_count = mesh.index_count;

  free(mesh.vertices);
  free(mesh.indices);
}

void MTLPlanetGraphicsClass_draw(MTLPlanetGraphicsClass *planet,
                                 RenderState *render_state, void *encoder_ptr) {
  id<MTLRenderCommandEncoder> encoder =
      (__bridge id<MTLRenderCommandEncoder>)encoder_ptr;

  simd_float4 color = get_planet_color(planet->body->planet_class);

  DisplacedMeshUniforms uniforms;
  id<MTLBuffer> uniform_buffer =
      (__bridge id<MTLBuffer>)RenderState_GetUniformBuffer(render_state);
  if (uniform_buffer) {
    memcpy(&uniforms, [uniform_buffer contents], sizeof(uniforms));
  } else {
    memset(&uniforms, 0, sizeof(uniforms));
  }

  float render_scale = (float)(planet->body->radius_m * METERS_TO_RENDER_UNITS);

  simd_float4x4 model = {0};
  model.columns[0] = simd_make_float4(render_scale, 0.0f, 0.0f, 0.0f);
  model.columns[1] = simd_make_float4(0.0f, render_scale, 0.0f, 0.0f);
  model.columns[2] = simd_make_float4(0.0f, 0.0f, render_scale, 0.0f);
  model.columns[3] = simd_make_float4(
      (float)(planet->body->position.x * METERS_TO_RENDER_UNITS),
      (float)(planet->body->position.y * METERS_TO_RENDER_UNITS),
      (float)(planet->body->position.z * METERS_TO_RENDER_UNITS), 1.0f);

  uniforms.mvpMatrix = simd_mul(uniforms.mvpMatrix, model);
  uniforms.gridColor = color;

  [encoder setVertexBytes:&uniforms length:sizeof(uniforms) atIndex:1];
  [encoder setFragmentBytes:&uniforms length:sizeof(uniforms) atIndex:1];

  if (planet->pipeline_state) {
    id<MTLRenderPipelineState> pipeline =
        (__bridge id<MTLRenderPipelineState>)planet->pipeline_state;
    [encoder setRenderPipelineState:pipeline];
  }

  if (planet->vertex_buffer) {
    id<MTLBuffer> vbuf = (__bridge id<MTLBuffer>)planet->vertex_buffer;
    [encoder setVertexBuffer:vbuf offset:0 atIndex:0];
  }

  if (planet->index_buffer) {
    id<MTLBuffer> ibuf = (__bridge id<MTLBuffer>)planet->index_buffer;
    [encoder drawIndexedPrimitives:MTLPrimitiveTypeTriangle
                        indexCount:planet->index_count
                         indexType:MTLIndexTypeUInt16
                       indexBuffer:ibuf
                 indexBufferOffset:0];
  }
}

MTLPlanetGraphicsClass *MTLPlanetGraphics_Create(CelestialBody_Planet *body) {
  MTLPlanetGraphicsClass *planet = malloc(sizeof(MTLPlanetGraphicsClass));
  if (!planet) {
    LOG_ERROR("Failed to allocate memory for planet graphics for planet: %s (%s)",
              body->name, body->body_id);
    return NULL;
  }

  planet->body = body;
  planet->vertex_buffer = NULL;
  planet->index_buffer = NULL;
  planet->index_count = 0;
  planet->pipeline_state = NULL;

  return planet;
}

void MTLPlanetGraphics_Destroy(MTLPlanetGraphicsClass *planet_graphics) {
  if (!planet_graphics)
    return;

  if (planet_graphics->vertex_buffer)
    CFRelease(planet_graphics->vertex_buffer);
  if (planet_graphics->index_buffer)
    CFRelease(planet_graphics->index_buffer);
  if (planet_graphics->pipeline_state)
    CFRelease(planet_graphics->pipeline_state);

  free(planet_graphics);
}
