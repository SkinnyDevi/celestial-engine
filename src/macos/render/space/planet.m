#import "planet.h"
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <mach/mach_time.h>
#import <math.h>
#import <stdlib.h>
#import <string.h>
#import <strings.h>

#import "core/log/log.h"
#import "core/space/defined/planets.h"
#import "core/space/units.h"

#import "macos/render/grid/displaced_mesh.h"
#import "macos/render/shape/orbit_ellipse.h"
#import "macos/render/shape/solid_sphere.h"
#import "macos/render/space/star.h"

#import "macos/shaders/planets/planet_common.h"
#import "macos/shaders/shader_loader.h"

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

static void apply_planet_specific_visuals(MTLPlanetGraphicsClass *planet,
                                          PlanetUniforms *puniforms) {
  if (!planet || !planet->body)
    return;

  get_planet_palette(planet->body->planet_class, planet->body->atmosphere_type,
                     &puniforms->baseColor, &puniforms->secondaryColor,
                     &puniforms->atmosphereColor, &puniforms->surfaceRoughness,
                     &puniforms->atmosphereDensity);

  const char *id = planet->body->body_id;
  const char *name = planet->body->name;

  if ((id && strcasecmp(id, "EARTH") == 0) ||
      (name && strcasecmp(name, "Earth") == 0)) {
    puniforms->baseColor = (simd_float4){0.03f, 0.18f, 0.55f, 1.0f};
    puniforms->secondaryColor = (simd_float4){0.20f, 0.48f, 0.18f, 1.0f};
    puniforms->atmosphereColor = (simd_float4){0.35f, 0.65f, 1.00f, 1.0f};
    puniforms->surfaceRoughness = 0.45f;
    puniforms->atmosphereDensity = 0.90f;
  } else if ((id && strcasecmp(id, "MARS") == 0) ||
             (name && strcasecmp(name, "Mars") == 0)) {
    puniforms->baseColor = (simd_float4){0.68f, 0.28f, 0.12f, 1.0f};
    puniforms->secondaryColor = (simd_float4){0.32f, 0.16f, 0.08f, 1.0f};
    puniforms->atmosphereColor = (simd_float4){0.82f, 0.58f, 0.40f, 0.35f};
    puniforms->surfaceRoughness = 0.88f;
    puniforms->atmosphereDensity = 0.22f;
  } else if ((id && strcasecmp(id, "VENUS") == 0) ||
             (name && strcasecmp(name, "Venus") == 0)) {
    puniforms->baseColor = (simd_float4){0.88f, 0.82f, 0.62f, 1.0f};
    puniforms->secondaryColor = (simd_float4){0.78f, 0.66f, 0.42f, 1.0f};
    puniforms->atmosphereColor = (simd_float4){0.96f, 0.88f, 0.62f, 1.6f};
    puniforms->surfaceRoughness = 0.20f;
    puniforms->atmosphereDensity = 1.80f;
  } else if ((id && strcasecmp(id, "MERCURY") == 0) ||
             (name && strcasecmp(name, "Mercury") == 0)) {
    puniforms->baseColor = (simd_float4){0.52f, 0.50f, 0.48f, 1.0f};
    puniforms->secondaryColor = (simd_float4){0.32f, 0.30f, 0.28f, 1.0f};
    puniforms->atmosphereColor = (simd_float4){0.0f, 0.0f, 0.0f, 0.0f};
    puniforms->surfaceRoughness = 0.98f;
    puniforms->atmosphereDensity = 0.0f;
  } else if ((id && strcasecmp(id, "JUPITER") == 0) ||
             (name && strcasecmp(name, "Jupiter") == 0)) {
    puniforms->baseColor = (simd_float4){0.86f, 0.74f, 0.56f, 1.0f};
    puniforms->secondaryColor = (simd_float4){0.68f, 0.36f, 0.18f, 1.0f};
    puniforms->atmosphereColor = (simd_float4){0.95f, 0.85f, 0.70f, 0.6f};
    puniforms->surfaceRoughness = 0.85f;
    puniforms->atmosphereDensity = 1.0f;
  } else if ((id && strcasecmp(id, "SATURN") == 0) ||
             (name && strcasecmp(name, "Saturn") == 0)) {
    puniforms->baseColor = (simd_float4){0.88f, 0.80f, 0.58f, 1.0f};
    puniforms->secondaryColor = (simd_float4){0.72f, 0.60f, 0.42f, 1.0f};
    puniforms->atmosphereColor = (simd_float4){0.90f, 0.82f, 0.64f, 0.5f};
    puniforms->surfaceRoughness = 0.75f;
    puniforms->atmosphereDensity = 1.1f;
  } else if ((id && strcasecmp(id, "URANUS") == 0) ||
             (name && strcasecmp(name, "Uranus") == 0)) {
    puniforms->baseColor = (simd_float4){0.42f, 0.78f, 0.82f, 1.0f};
    puniforms->secondaryColor = (simd_float4){0.58f, 0.88f, 0.90f, 1.0f};
    puniforms->atmosphereColor = (simd_float4){0.48f, 0.85f, 0.95f, 0.85f};
    puniforms->surfaceRoughness = 0.60f;
    puniforms->atmosphereDensity = 1.25f;
  } else if ((id && strcasecmp(id, "NEPTUNE") == 0) ||
             (name && strcasecmp(name, "Neptune") == 0)) {
    puniforms->baseColor = (simd_float4){0.14f, 0.32f, 0.88f, 1.0f};
    puniforms->secondaryColor = (simd_float4){0.36f, 0.72f, 0.98f, 1.0f};
    puniforms->atmosphereColor = (simd_float4){0.25f, 0.60f, 1.00f, 0.90f};
    puniforms->surfaceRoughness = 0.65f;
    puniforms->atmosphereDensity = 1.30f;
  } else if ((id && strcasecmp(id, "PLUTO") == 0) ||
             (name && strcasecmp(name, "Pluto") == 0)) {
    puniforms->baseColor = (simd_float4){0.60f, 0.52f, 0.44f, 1.0f};
    puniforms->secondaryColor = (simd_float4){0.88f, 0.82f, 0.75f, 1.0f};
    puniforms->atmosphereColor = (simd_float4){0.45f, 0.65f, 0.85f, 0.15f};
    puniforms->surfaceRoughness = 0.92f;
    puniforms->atmosphereDensity = 0.08f;
  }
}

void create_planet_render_pipelines(RenderState *state) {
  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  if (!metal_layer)
    return;

  struct {
    PlanetClass pclass;
    const char *shader_name;
    NSString *vertex_fn;
    NSString *fragment_fn;
  } planet_shaders[] = {
      {PLANET_CLASS_TERRESTRIAL, "generic_planet_terrestrial",
       @"planet_terrestrial_vertex", @"planet_terrestrial_fragment"},
      {PLANET_CLASS_GAS_GIANT, "generic_planet_gas_giant",
       @"planet_gas_giant_vertex", @"planet_gas_giant_fragment"},
      {PLANET_CLASS_ICE_GIANT, "generic_planet_ice_giant",
       @"planet_ice_giant_vertex", @"planet_ice_giant_fragment"},
      {PLANET_CLASS_DWARF, "generic_planet_dwarf", @"planet_dwarf_vertex",
       @"planet_dwarf_fragment"},
      {PLANET_CLASS_ROGUE, "generic_planet_rogue", @"planet_rogue_vertex",
       @"planet_rogue_fragment"},
  };

  MTLCompileOptions *options = [MTLCompileOptions new];

  for (size_t i = 0; i < 5; i++) {
    const char *src = load_shader_file(planet_shaders[i].shader_name);
    if (!src) {
      LOG_ERROR("Failed to load planet shader source: %s",
                planet_shaders[i].shader_name);
      continue;
    }

    NSError *error = nil;
    NSString *source_str = [NSString stringWithUTF8String:src];
    free((void *)src);

    id<MTLLibrary> library = [metal_layer.device newLibraryWithSource:source_str
                                                              options:options
                                                                error:&error];
    if (error || !library) {
      LOG_ERROR("Error compiling planet shader library '%s': %s",
                planet_shaders[i].shader_name,
                [[error localizedDescription] UTF8String]);
      continue;
    }

    id<MTLFunction> vfn =
        [library newFunctionWithName:planet_shaders[i].vertex_fn];
    id<MTLFunction> ffn =
        [library newFunctionWithName:planet_shaders[i].fragment_fn];
    if (!vfn || !ffn) {
      LOG_ERROR("Could not find vertex/fragment functions in '%s'",
                planet_shaders[i].shader_name);
      continue;
    }

    MTLRenderPipelineDescriptor *desc =
        [[MTLRenderPipelineDescriptor alloc] init];
    desc.vertexFunction = vfn;
    desc.fragmentFunction = ffn;
    desc.colorAttachments[0].pixelFormat = metal_layer.pixelFormat;
    desc.depthAttachmentPixelFormat = MTLPixelFormatDepth32Float;

    id<MTLRenderPipelineState> pipeline =
        [metal_layer.device newRenderPipelineStateWithDescriptor:desc
                                                           error:&error];
    if (error || !pipeline) {
      LOG_ERROR("Error creating pipeline for planet '%s': %s",
                planet_shaders[i].shader_name,
                [[error localizedDescription] UTF8String]);
      continue;
    }

    RenderState_SetPlanetPipeline(state, planet_shaders[i].pclass,
                                  (__bridge void *)pipeline);
    LOG_INFO("Compiled planet pipeline: %s", planet_shaders[i].shader_name);
  }

  // Update any existing planets that need pipeline states
  DynamicArray *planets = RenderState_GetPlanets(state);
  if (planets) {
    size_t count = DynamicArray_length(planets);
    for (size_t i = 0; i < count; i++) {
      MTLPlanetGraphicsClass *planet;
      DynamicArray_get(planets, i, &planet);

      if (planet && !planet->pipeline_state) {
        void *pipe =
            RenderState_GetPlanetPipeline(state, planet->body->planet_class);

        if (pipe)
          planet->pipeline_state = (void *)CFBridgingRetain((__bridge id)pipe);
      }
    }
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

  void *pipe =
      RenderState_GetPlanetPipeline(render_state, planet->body->planet_class);
  if (pipe) {
    if (planet->pipeline_state)
      CFRelease(planet->pipeline_state);

    planet->pipeline_state = (void *)CFBridgingRetain((__bridge id)pipe);
  }

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

bool MTLPlanetGraphicsClass_draw(MTLPlanetGraphicsClass *planet,
                                 RenderState *render_state, void *encoder_ptr) {
  if (!planet)
    return false;

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
    // skip vertices
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

  // planet sphere
  if (!camera_frustum_test_sphere(&frustum, body_pos, render_scale))
    return false; // Off-screen

  simd_float4x4 model = {0};
  model.columns[0] = simd_make_float4(render_scale, 0.0f, 0.0f, 0.0f);
  model.columns[1] = simd_make_float4(0.0f, render_scale, 0.0f, 0.0f);
  model.columns[2] = simd_make_float4(0.0f, 0.0f, render_scale, 0.0f);
  model.columns[3] = simd_make_float4(body_pos.x, body_pos.y, body_pos.z, 1.0f);

  float near_plane, far_plane;
  camera_get_clipping_planes(camera, &near_plane, &far_plane);
  simd_float4x4 view_proj =
      simd_mul(camera_perspective(70.0f * (float)M_PI / 180.0f, aspect,
                                  near_plane, far_plane),
               camera_view_matrix(camera));

  // Compute light direction towards host star (or system center)
  simd_float3 light_dir = simd_make_float3(0.0f, 0.0f, 1.0f);
  float light_intensity = 1.0f;
  if (planet->body->planet_class == PLANET_CLASS_ROGUE) {
    light_intensity = 0.0f;
    light_dir = simd_make_float3(0.0f, 1.0f, 0.0f);
  } else if (planet->host_star) {
    double sx = planet->host_star->body->position.x * METERS_TO_RENDER_UNITS -
                camera->center.x;
    double sy = planet->host_star->body->position.y * METERS_TO_RENDER_UNITS -
                camera->center.y;
    double sz = planet->host_star->body->position.z * METERS_TO_RENDER_UNITS -
                camera->center.z;

    simd_float3 star_pos = simd_make_float3((float)sx, (float)sy, (float)sz);
    simd_float3 diff = star_pos - body_pos;
    float len = simd_length(diff);
    if (len > 1e-4f)
      light_dir = diff / len;

  } else {
    simd_float3 diff = -body_pos;
    float len = simd_length(diff);

    if (len > 1e-4f)
      light_dir = diff / len;
  }

  // Elapsed animation time
  static uint64_t planet_start_time = 0;
  if (planet_start_time == 0)
    planet_start_time = mach_absolute_time();

  uint64_t cur_time = mach_absolute_time();
  mach_timebase_info_data_t tb;
  mach_timebase_info(&tb);
  float elapsed_sec = (float)(cur_time - planet_start_time) * (float)tb.numer /
                      (float)tb.denom / 1e9f;

  // Rotation speed
  float rot_speed = 0.05f;
  if (planet->body->rotation_period_days != 0.0) {
    double period = fabs(planet->body->rotation_period_days);
    if (period > 0.001) {
      rot_speed = (float)(0.05 / period);
      if (rot_speed < 0.008f)
        rot_speed = 0.008f;
      if (rot_speed > 0.25f)
        rot_speed = 0.25f;
    }
  }

  // Procedural seed
  uint32_t seed_val = 0;
  if (planet->body->name[0] != '\0') {
    for (const char *p = planet->body->name; *p; p++)
      seed_val = seed_val * 31 + (uint32_t)(*p);
  } else if (planet->body->body_id[0] != '\0') {
    for (const char *p = planet->body->body_id; *p; p++)
      seed_val = seed_val * 31 + (uint32_t)(*p);
  } else {
    seed_val = (uint32_t)(uintptr_t)planet;
  }
  float seed = (float)(seed_val % 1000) * 0.137f + 1.23f;

  PlanetUniforms puniforms;
  memset(&puniforms, 0, sizeof(puniforms));
  puniforms.mvpMatrix = simd_mul(view_proj, model);
  puniforms.modelMatrix = model;
  apply_planet_specific_visuals(planet, &puniforms);
  puniforms.cameraPos = (PackedFloat3){cam_pos.x, cam_pos.y, cam_pos.z};
  puniforms.time = elapsed_sec;
  puniforms.lightDirection =
      (PackedFloat3){light_dir.x, light_dir.y, light_dir.z};
  puniforms.lightIntensity = light_intensity;
  puniforms.seed = seed;
  puniforms.rotationSpeed = rot_speed;

  id<MTLRenderPipelineState> pipeline =
      planet->pipeline_state
          ? (__bridge id<MTLRenderPipelineState>)planet->pipeline_state
          : (__bridge id<MTLRenderPipelineState>)RenderState_GetPlanetPipeline(
                render_state, planet->body->planet_class);
  if (!pipeline)
    pipeline =
        (__bridge id<MTLRenderPipelineState>)RenderState_GetPipelineState(
            render_state);

  [encoder setRenderPipelineState:pipeline];

  id<MTLDepthStencilState> depth_state =
      (__bridge id<MTLDepthStencilState>)RenderState_GetDepthStencilState(
          render_state);
  if (depth_state)
    [encoder setDepthStencilState:depth_state];

  if (pipeline == (__bridge id<MTLRenderPipelineState>)
                      RenderState_GetPipelineState(render_state)) {
    DisplacedMeshUniforms fallback_uniforms;
    fallback_uniforms.mvpMatrix = puniforms.mvpMatrix;
    fallback_uniforms.gridColor = puniforms.baseColor;

    [encoder setVertexBytes:&fallback_uniforms
                     length:sizeof(fallback_uniforms)
                    atIndex:1];
    [encoder setFragmentBytes:&fallback_uniforms
                       length:sizeof(fallback_uniforms)
                      atIndex:1];
  } else {
    [encoder setVertexBytes:&puniforms length:sizeof(puniforms) atIndex:1];
    [encoder setFragmentBytes:&puniforms length:sizeof(puniforms) atIndex:1];
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

  return true;
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