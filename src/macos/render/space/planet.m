#import "planet.h"
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <stdlib.h>

#import "core/log/log.h"
#import "core/space/defined/planets.h"
#import "core/space/units.h"
#import "macos/render/grid/displaced_mesh.h"
#import "macos/render/shape/orbit_ellipse.h"
#import "macos/render/shape/solid_sphere.h"
#import "macos/render/space/star.h"

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
  void *vbuf = NULL;
  void *ibuf = NULL;
  int idx_count = 0;
  get_shared_solid_sphere_buffers(render_state, &vbuf, &ibuf, &idx_count);

  planet->vertex_buffer = vbuf;
  planet->index_buffer = ibuf;
  planet->index_count = idx_count;

  planet->orbit_buffer = NULL;
  planet->orbit_vertex_count = 0;
  if (planet->body->orbit) {
    id<MTLBuffer> buf = nil;
    int count = 0;
    init_orbit_graphics(render_state, planet->body->orbit, &buf, &count);
    planet->orbit_buffer = (void *)CFBridgingRetain(buf);
    planet->orbit_vertex_count = count;
  }
}

void MTLPlanetGraphicsClass_draw(MTLPlanetGraphicsClass *planet,
                                 RenderState *render_state, void *encoder_ptr) {
  if (!planet)
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

  // 1. Orbit Rendering with Frustum & Sub-pixel Culling
  if (planet->orbit_buffer && planet->body->orbit) {
    simd_float3 host_pos = simd_make_float3(0.0f, 0.0f, 0.0f);
    if (planet->host_star) {
      double hx = planet->host_star->body->position.x * METERS_TO_RENDER_UNITS -
                  camera->center.x;
      double hy = planet->host_star->body->position.y * METERS_TO_RENDER_UNITS -
                  camera->center.y;
      double hz = planet->host_star->body->position.z * METERS_TO_RENDER_UNITS -
                  camera->center.z;
      host_pos = simd_make_float3((float)hx, (float)hy, (float)hz);
    }

    float dist_to_host = simd_distance(cam_pos, host_pos);
    float max_orbit_r = (float)(planet->body->orbit->semimajor_axis *
                                (1.0 + planet->body->orbit->eccentricity) *
                                METERS_TO_RENDER_UNITS);

    // Sub-pixel culling: if orbit spans < 0.0005 radians (< 1 pixel on screen),
    // skip 65k vertices
    bool is_subpixel = (max_orbit_r / fmaxf(dist_to_host, 1e-4f)) < 0.0005f;
    bool orbit_in_frustum =
        camera_frustum_test_sphere(&frustum, host_pos, max_orbit_r);

    if (orbit_in_frustum && !is_subpixel) {
      id<MTLBuffer> buf = (__bridge id<MTLBuffer>)planet->orbit_buffer;
      draw_orbit_ellipse(render_state, encoder, buf, planet->orbit_vertex_count,
                         host_pos);
    }
  }

  // 2. Planet Sphere Rendering with Frustum Culling
  double abs_x = planet->body->position.x;
  double abs_y = planet->body->position.y;
  double abs_z = planet->body->position.z;

  if (planet->host_star) {
    abs_x += planet->host_star->body->position.x;
    abs_y += planet->host_star->body->position.y;
    abs_z += planet->host_star->body->position.z;
  }

  double rel_x = abs_x * METERS_TO_RENDER_UNITS - camera->center.x;
  double rel_y = abs_y * METERS_TO_RENDER_UNITS - camera->center.y;
  double rel_z = abs_z * METERS_TO_RENDER_UNITS - camera->center.z;
  simd_float3 body_pos =
      simd_make_float3((float)rel_x, (float)rel_y, (float)rel_z);

  float dist = simd_distance(cam_pos, body_pos);
  float base_scale = (float)(planet->body->radius_m * METERS_TO_RENDER_UNITS);
  float min_visual_size = dist * 0.0018f;
  float render_scale =
      base_scale > min_visual_size ? base_scale : min_visual_size;

  // Frustum test on planet sphere
  if (!camera_frustum_test_sphere(&frustum, body_pos, render_scale))
    return; // Off-screen! Culled.

  simd_float4 color = get_planet_color(planet->body->planet_class);

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
      planet->pipeline_state
          ? (__bridge id<MTLRenderPipelineState>)planet->pipeline_state
          : (__bridge id<MTLRenderPipelineState>)RenderState_GetPipelineState(
                render_state);
  [encoder setRenderPipelineState:pipeline];

  id<MTLDepthStencilState> depth_state =
      (__bridge id<MTLDepthStencilState>)RenderState_GetDepthStencilState(
          render_state);
  if (depth_state)
    [encoder setDepthStencilState:depth_state];

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
  MTLPlanetGraphicsClass *planet = calloc(1, sizeof(MTLPlanetGraphicsClass));
  if (!planet) {
    LOG_ERROR(
        "Failed to allocate memory for planet graphics for planet: %s (%s)",
        body->name, body->body_id);
    return NULL;
  }

  planet->body = body;
  planet->vertex_buffer = NULL;
  planet->index_buffer = NULL;
  planet->index_count = 0;
  planet->pipeline_state = NULL;
  planet->orbit_buffer = NULL;
  planet->orbit_vertex_count = 0;

  return planet;
}

void MTLPlanetGraphics_Destroy(MTLPlanetGraphicsClass *planet_graphics) {
  if (!planet_graphics)
    return;

  if (planet_graphics->pipeline_state)
    CFRelease(planet_graphics->pipeline_state);

  if (planet_graphics->orbit_buffer)
    CFRelease(planet_graphics->orbit_buffer);

  free(planet_graphics);
}

void init_celestial_body_planets(RenderState *render_state) {
  DynamicArray *planets = RenderState_GetPlanets(render_state);

  MTLPlanetGraphicsClass *mtl_mercury = MTLPlanetGraphics_Create(&MERCURY);
  MTLPlanetGraphicsClass *mtl_venus = MTLPlanetGraphics_Create(&VENUS);
  MTLPlanetGraphicsClass *mtl_earth = MTLPlanetGraphics_Create(&EARTH);
  MTLPlanetGraphicsClass *mtl_mars = MTLPlanetGraphics_Create(&MARS);
  MTLPlanetGraphicsClass *mtl_jupiter = MTLPlanetGraphics_Create(&JUPITER);
  MTLPlanetGraphicsClass *mtl_saturn = MTLPlanetGraphics_Create(&SATURN);
  MTLPlanetGraphicsClass *mtl_uranus = MTLPlanetGraphics_Create(&URANUS);
  MTLPlanetGraphicsClass *mtl_neptune = MTLPlanetGraphics_Create(&NEPTUNE);

  DynamicArray_push(planets, &mtl_mercury);
  DynamicArray_push(planets, &mtl_venus);
  DynamicArray_push(planets, &mtl_earth);
  DynamicArray_push(planets, &mtl_mars);
  DynamicArray_push(planets, &mtl_jupiter);
  DynamicArray_push(planets, &mtl_saturn);
  DynamicArray_push(planets, &mtl_uranus);
  DynamicArray_push(planets, &mtl_neptune);

  size_t planet_count = DynamicArray_length(planets);
  for (size_t i = 0; i < planet_count; i++) {
    MTLPlanetGraphicsClass *planet;
    DynamicArray_get(planets, i, &planet);
    MTLPlanetGraphicsClass_init(planet, render_state);
    LOG_DEBUG("Registered planet (%lu): %s (%s)", i,
              ((CelestialBody_Planet *)planet->body)->name,
              ((CelestialBody_Planet *)planet->body)->body_id);
  }
}

void load_celestial_body_planets_from_file(RenderState *render_state,
                                           LoadedSimulationBodies *bodies) {
  DynamicArray *planets = RenderState_GetPlanets(render_state);
  size_t count = DynamicArray_length(&bodies->planets);

  for (size_t i = 0; i < count; i++) {
    CelestialBody_Planet *planet;
    DynamicArray_get(&bodies->planets, i, &planet);
    MTLPlanetGraphicsClass *mtl_planet = MTLPlanetGraphics_Create(planet);
    MTLPlanetGraphicsClass_init(mtl_planet, render_state);
    DynamicArray_push(planets, &mtl_planet);
    LOG_DEBUG("Registered planet (%lu): %s (%s)", i,
              ((CelestialBody_Planet *)mtl_planet->body)->name,
              ((CelestialBody_Planet *)mtl_planet->body)->body_id);
  }
}