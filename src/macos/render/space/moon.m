#import "moon.h"
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <stdlib.h>

#import "core/log/log.h"

#import "core/cli/instance_data.h"
#import "core/space/defined/moons.h"
#import "core/space/units.h"

#import "macos/render/grid/displaced_mesh.h"
#import "macos/render/shape/orbit_ellipse.h"
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
  void *vbuf = NULL;
  void *ibuf = NULL;
  int idx_count = 0;
  get_shared_solid_sphere_buffers(render_state, &vbuf, &ibuf, &idx_count);

  moon->vertex_buffer = vbuf;
  moon->index_buffer = ibuf;
  moon->index_count = idx_count;

  moon->orbit_buffer = NULL;
  moon->orbit_vertex_count = 0;
  if (moon->body->orbit) {
    id<MTLBuffer> buf = nil;
    int count = 0;
    init_orbit_graphics(render_state, moon->body->orbit, &buf, &count);
    moon->orbit_buffer = (void *)CFBridgingRetain(buf);
    moon->orbit_vertex_count = count;
  }
}

void MTLMoonGraphicsClass_draw(MTLMoonGraphicsClass *moon,
                               RenderState *render_state, void *encoder_ptr) {
  if (!moon)
    return;

  Camera *camera = RenderState_GetCamera(render_state);
  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(render_state);
  float aspect = metal_layer.drawableSize.width /
                 MAX(metal_layer.drawableSize.height, 1.0f);
  simd_float3 cam_pos = camera_orbit_position(camera);

  // Extract camera frustum with 75° FOV margin
  CameraFrustum frustum =
      camera_extract_frustum(camera, aspect, 75.0f * (float)M_PI / 180.0f);

  id<MTLRenderCommandEncoder> encoder =
      (__bridge id<MTLRenderCommandEncoder>)encoder_ptr;

  // 1. Moon Orbit Rendering with Frustum & Sub-pixel Culling
  if (moon->orbit_buffer && moon->body->orbit) {
    simd_float3 host_pos = simd_make_float3(0.0f, 0.0f, 0.0f);
    if (moon->host_planet) {
      double hx = moon->host_planet->body->position.x;
      double hy = moon->host_planet->body->position.y;
      double hz = moon->host_planet->body->position.z;
      if (moon->host_planet->host_star) {
        hx += moon->host_planet->host_star->body->position.x;
        hy += moon->host_planet->host_star->body->position.y;
        hz += moon->host_planet->host_star->body->position.z;
      }
      double h_rel_x = hx * METERS_TO_RENDER_UNITS - camera->center.x;
      double h_rel_y = hy * METERS_TO_RENDER_UNITS - camera->center.y;
      double h_rel_z = hz * METERS_TO_RENDER_UNITS - camera->center.z;
      host_pos =
          simd_make_float3((float)h_rel_x, (float)h_rel_y, (float)h_rel_z);
    }

    float dist_to_host = simd_distance(cam_pos, host_pos);
    float max_orbit_r = (float)(moon->body->orbit->semimajor_axis *
                                (1.0 + moon->body->orbit->eccentricity) *
                                METERS_TO_RENDER_UNITS);

    // Sub-pixel culling: if orbit spans < 0.0005 radians (< 1 pixel on screen),
    // skip 65k vertices
    bool is_subpixel = (max_orbit_r / fmaxf(dist_to_host, 1e-4f)) < 0.0005f;
    bool orbit_in_frustum =
        camera_frustum_test_sphere(&frustum, host_pos, max_orbit_r);

    if (orbit_in_frustum && !is_subpixel) {
      id<MTLBuffer> buf = (__bridge id<MTLBuffer>)moon->orbit_buffer;
      draw_orbit_ellipse(render_state, encoder, buf, moon->orbit_vertex_count,
                         host_pos);
    }
  }

  // 2. Moon Sphere Rendering with Frustum Culling
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

  double rel_x = abs_x * METERS_TO_RENDER_UNITS - camera->center.x;
  double rel_y = abs_y * METERS_TO_RENDER_UNITS - camera->center.y;
  double rel_z = abs_z * METERS_TO_RENDER_UNITS - camera->center.z;
  simd_float3 body_pos =
      simd_make_float3((float)rel_x, (float)rel_y, (float)rel_z);

  float dist = simd_distance(cam_pos, body_pos);
  float base_scale = (float)(moon->body->radius_m * METERS_TO_RENDER_UNITS);
  float min_visual_size = dist * 0.0018f;
  float render_scale =
      base_scale > min_visual_size ? base_scale : min_visual_size;

  // Frustum test on moon sphere
  if (!camera_frustum_test_sphere(&frustum, body_pos, render_scale))
    return; // Off-screen! Culled.

  simd_float4 color = get_moon_color(moon->body->moon_class);

  DisplacedMeshUniforms uniforms;
  id<MTLBuffer> uniform_buffer =
      (__bridge id<MTLBuffer>)RenderState_GetUniformBuffer(render_state);
  if (uniform_buffer)
    memcpy(&uniforms, [uniform_buffer contents], sizeof(uniforms));
  else
    memset(&uniforms, 0, sizeof(uniforms));

  simd_float4x4 model = {0};
  model.columns[0] = simd_make_float4(render_scale, 0.0f, 0.0f, 0.0f);
  model.columns[1] = simd_make_float4(0.0f, render_scale, 0.0f, 0.0f);
  model.columns[2] = simd_make_float4(0.0f, 0.0f, render_scale, 0.0f);
  model.columns[3] = simd_make_float4(body_pos.x, body_pos.y, body_pos.z, 1.0f);

  uniforms.mvpMatrix = simd_mul(uniforms.mvpMatrix, model);
  uniforms.gridColor = color;

  [encoder setVertexBytes:&uniforms length:sizeof(uniforms) atIndex:1];
  [encoder setFragmentBytes:&uniforms length:sizeof(uniforms) atIndex:1];

  id<MTLRenderPipelineState> pipeline =
      moon->pipeline_state
          ? (__bridge id<MTLRenderPipelineState>)moon->pipeline_state
          : (__bridge id<MTLRenderPipelineState>)RenderState_GetPipelineState(
                render_state);
  [encoder setRenderPipelineState:pipeline];

  id<MTLDepthStencilState> depth_state =
      (__bridge id<MTLDepthStencilState>)RenderState_GetDepthStencilState(
          render_state);
  if (depth_state)
    [encoder setDepthStencilState:depth_state];

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
  MTLMoonGraphicsClass *moon = calloc(1, sizeof(MTLMoonGraphicsClass));
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
  moon->orbit_buffer = NULL;
  moon->orbit_vertex_count = 0;

  return moon;
}

void MTLMoonGraphics_Destroy(MTLMoonGraphicsClass *moon_graphics) {
  if (!moon_graphics)
    return;

  if (moon_graphics->pipeline_state)
    CFRelease(moon_graphics->pipeline_state);
  if (moon_graphics->orbit_buffer)
    CFRelease(moon_graphics->orbit_buffer);

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

void load_celestial_body_moons_from_file(RenderState *render_state,
                                         LoadedSimulationBodies *bodies) {
  DynamicArray *moons = RenderState_GetMoons(render_state);
  size_t count = DynamicArray_length(&bodies->moons);

  for (size_t i = 0; i < count; i++) {
    CelestialBody_Moon *moon;
    DynamicArray_get(&bodies->moons, i, &moon);
    MTLMoonGraphicsClass *mtl_moon = MTLMoonGraphics_Create(moon);
    MTLMoonGraphicsClass_init(mtl_moon, render_state);
    DynamicArray_push(moons, &mtl_moon);
    LOG_DEBUG("Registered moon (%lu): %s (%s)", i,
              ((CelestialBody_Moon *)mtl_moon->body)->name,
              ((CelestialBody_Moon *)mtl_moon->body)->body_id);
  }
}