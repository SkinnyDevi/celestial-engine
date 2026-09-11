#import "moon.h"
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <stdlib.h>

#import "core/log/log.h"
#import "core/space/defined/moons.h"
#import "core/space/units.h"
#import "macos/render/grid/displaced_mesh.h"
#import "macos/render/shape/solid_sphere.h"
#import "macos/render/space/planet.h"
#import "macos/render/space/star.h"

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

  float base_scale = (float)(moon->body->radius_m * METERS_TO_RENDER_UNITS);

  Camera *camera = RenderState_GetCamera(render_state);
  simd_float3 cam_pos = camera_orbit_position(camera);

  double abs_x = moon->body->position.x;
  double abs_y = moon->body->position.y;
  double abs_z = moon->body->position.z;

  if (moon->host_planet) {
    abs_x += moon->host_planet->body->position.x;
    abs_y += moon->host_planet->body->position.y;
    abs_z += moon->host_planet->body->position.z;

    if (moon->host_planet->host_star) {
      abs_x += moon->host_planet->host_star->body->position.x;
      abs_y += moon->host_planet->host_star->body->position.y;
      abs_z += moon->host_planet->host_star->body->position.z;
    }
  }

  simd_float3 body_pos = simd_make_float3(
      (float)(abs_x * METERS_TO_RENDER_UNITS),
      (float)(abs_y * METERS_TO_RENDER_UNITS),
      (float)(abs_z * METERS_TO_RENDER_UNITS));

  float dist = simd_distance(cam_pos, body_pos);
  float min_visual_size = dist * 0.003f; // 0.3% of distance ensures visibility
  float render_scale =
      base_scale > min_visual_size ? base_scale : min_visual_size;

  simd_float4x4 model = {0};
  model.columns[0] = simd_make_float4(render_scale, 0.0f, 0.0f, 0.0f);
  model.columns[1] = simd_make_float4(0.0f, render_scale, 0.0f, 0.0f);
  model.columns[2] = simd_make_float4(0.0f, 0.0f, render_scale, 0.0f);
  model.columns[3] = simd_make_float4(body_pos.x, body_pos.y, body_pos.z, 1.0f);

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

void init_celestial_body_moons(RenderState *render_state) {
  DynamicArray *moons = RenderState_GetMoons(render_state);

  MTLMoonGraphicsClass *mtl_luna = MTLMoonGraphics_Create(&LUNA);
  MTLMoonGraphicsClass *mtl_phobos = MTLMoonGraphics_Create(&PHOBOS);
  MTLMoonGraphicsClass *mtl_deimos = MTLMoonGraphics_Create(&DEIMOS);
  MTLMoonGraphicsClass *mtl_europa = MTLMoonGraphics_Create(&EUROPA);
  MTLMoonGraphicsClass *mtl_io = MTLMoonGraphics_Create(&IO);
  MTLMoonGraphicsClass *mtl_titan = MTLMoonGraphics_Create(&TITAN);
  MTLMoonGraphicsClass *mtl_triton = MTLMoonGraphics_Create(&TRITON);

  DynamicArray_push(moons, &mtl_luna);
  DynamicArray_push(moons, &mtl_phobos);
  DynamicArray_push(moons, &mtl_deimos);
  DynamicArray_push(moons, &mtl_europa);
  DynamicArray_push(moons, &mtl_io);
  DynamicArray_push(moons, &mtl_titan);
  DynamicArray_push(moons, &mtl_triton);

  size_t moon_count = DynamicArray_length(moons);
  for (size_t i = 0; i < moon_count; i++) {
    MTLMoonGraphicsClass *moon;
    DynamicArray_get(moons, i, &moon);
    MTLMoonGraphicsClass_init(moon, render_state);
    LOG_DEBUG("Registered moon (%lu): %s (%s)", i,
              ((CelestialBody_Moon *)moon->body)->name,
              ((CelestialBody_Moon *)moon->body)->body_id);
  }
}