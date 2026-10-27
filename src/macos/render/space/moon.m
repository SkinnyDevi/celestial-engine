#import "moon.h"
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <mach/mach_time.h>
#import <math.h>
#import <stdlib.h>
#import <string.h>
#import <strings.h>

#import "core/cli/instance_data.h"
#import "core/log/log.h"
#import "core/space/defined/moons.h"
#import "core/space/units.h"
#import "macos/render/grid/displaced_mesh.h"
#import "macos/render/shape/orbit_ellipse.h"
#import "macos/render/shape/solid_sphere.h"
#import "macos/render/space/planet.h"
#import "macos/render/space/star.h"

#import "macos/shaders/moons/moon_common.h"
#import "macos/shaders/shader_loader.h"

static inline float fclamp(float val, float min_val, float max_val) {
  return fmaxf(min_val, fminf(max_val, val));
}

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

static void apply_moon_specific_visuals(MTLMoonGraphicsClass *moon,
                                        MoonUniforms *muniforms) {
  if (!moon || !moon->body)
    return;

  get_moon_palette(moon->body->moon_class, &muniforms->baseColor,
                   &muniforms->secondaryColor, &muniforms->accentColor,
                   &muniforms->surfaceRoughness, &muniforms->albedo);

  const char *id = moon->body->body_id;
  const char *name = moon->body->name;

  if ((id && strcasecmp(id, "LUNA") == 0) ||
      (name && strcasecmp(name, "Moon") == 0)) {
    muniforms->baseColor =
        (simd_float4){0.68f, 0.67f, 0.65f, 1.0f}; // Anorthosite highlands
    muniforms->secondaryColor =
        (simd_float4){0.20f, 0.20f, 0.22f, 1.0f}; // Dark basalt maria
    muniforms->accentColor =
        (simd_float4){0.95f, 0.94f, 0.90f, 1.0f}; // Bright Tycho crater rays
    muniforms->surfaceRoughness = 0.92f;
    muniforms->albedo = 0.12f;
  } else if ((id && strcasecmp(id, "IO") == 0) ||
             (name && strcasecmp(name, "Io") == 0)) {
    muniforms->baseColor =
        (simd_float4){0.92f, 0.85f, 0.32f, 1.0f}; // Sulfur yellow & SO2 snow
    muniforms->secondaryColor =
        (simd_float4){0.78f, 0.40f, 0.10f, 1.0f}; // Patera sulfur rings
    muniforms->accentColor =
        (simd_float4){0.98f, 0.25f, 0.02f, 1.0f}; // Molten lava lakes
    muniforms->surfaceRoughness = 0.65f;
    muniforms->albedo = 0.63f;
  } else if ((id && strcasecmp(id, "EUROPA") == 0) ||
             (name && strcasecmp(name, "Europa") == 0)) {
    muniforms->baseColor =
        (simd_float4){0.90f, 0.94f, 0.98f, 1.0f}; // Pristine water ice
    muniforms->secondaryColor =
        (simd_float4){0.62f, 0.30f, 0.16f, 1.0f}; // Reddish-brown salt lineae
    muniforms->accentColor =
        (simd_float4){0.40f, 0.75f, 0.98f, 1.0f}; // Subsurface ocean glow
    muniforms->surfaceRoughness = 0.30f;
    muniforms->albedo = 0.68f;
  } else if ((id && (strcasecmp(id, "PHOBOS") == 0 ||
                     strcasecmp(id, "DEIMOS") == 0)) ||
             (name && (strcasecmp(name, "Phobos") == 0 ||
                       strcasecmp(name, "Deimos") == 0))) {
    muniforms->baseColor =
        (simd_float4){0.30f, 0.28f, 0.26f, 1.0f}; // Carbonaceous chondrite
    muniforms->secondaryColor =
        (simd_float4){0.16f, 0.15f, 0.14f, 1.0f}; // Regolith dust
    muniforms->accentColor =
        (simd_float4){0.46f, 0.42f, 0.38f, 1.0f}; // Stickney rim
    muniforms->surfaceRoughness = 0.98f;
    muniforms->albedo = 0.06f;
  } else if ((id && strcasecmp(id, "TITAN") == 0) ||
             (name && strcasecmp(name, "Titan") == 0)) {
    muniforms->baseColor = (simd_float4){0.85f, 0.65f, 0.30f,
                                         1.0f}; // Dense golden hydrocarbon haze
    muniforms->secondaryColor =
        (simd_float4){0.45f, 0.30f, 0.15f, 1.0f}; // Hydrocarbon lakes & dunes
    muniforms->accentColor =
        (simd_float4){0.92f, 0.78f, 0.45f, 1.0f}; // Upper haze rim
    muniforms->surfaceRoughness = 0.40f;
    muniforms->albedo = 0.22f;
  } else if ((id && strcasecmp(id, "TRITON") == 0) ||
             (name && strcasecmp(name, "Triton") == 0)) {
    muniforms->baseColor =
        (simd_float4){0.88f, 0.82f, 0.85f, 1.0f}; // Pinkish nitrogen ice
    muniforms->secondaryColor =
        (simd_float4){0.45f, 0.55f, 0.52f, 1.0f}; // Cantaloupe terrain
    muniforms->accentColor =
        (simd_float4){0.20f, 0.20f, 0.22f, 1.0f}; // Nitrogen geyser plumes
    muniforms->surfaceRoughness = 0.55f;
    muniforms->albedo = 0.76f;
  }
}

void create_moon_render_pipelines(RenderState *state) {
  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  if (!metal_layer)
    return;

  struct {
    MoonClass mclass;
    const char *shader_name;
    NSString *vertex_fn;
    NSString *fragment_fn;
  } moon_shaders[] = {
      {MOON_CLASS_ROCKY, "generic_moon_rocky", @"moon_rocky_vertex",
       @"moon_rocky_fragment"},
      {MOON_CLASS_ICY, "generic_moon_icy", @"moon_icy_vertex",
       @"moon_icy_fragment"},
      {MOON_CLASS_CAPTURED, "generic_moon_captured", @"moon_captured_vertex",
       @"moon_captured_fragment"},
      {MOON_CLASS_VOLCANIC, "generic_moon_volcanic", @"moon_volcanic_vertex",
       @"moon_volcanic_fragment"},
  };

  MTLCompileOptions *options = [MTLCompileOptions new];

  for (size_t i = 0; i < 4; i++) {
    const char *src = load_shader_file(moon_shaders[i].shader_name);
    if (!src) {
      LOG_ERROR("Failed to load moon shader source: %s",
                moon_shaders[i].shader_name);
      continue;
    }

    NSError *error = nil;
    NSString *source_str = [NSString stringWithUTF8String:src];
    free((void *)src);

    id<MTLLibrary> library = [metal_layer.device newLibraryWithSource:source_str
                                                              options:options
                                                                error:&error];
    if (error || !library) {
      LOG_ERROR("Error compiling moon shader library '%s': %s",
                moon_shaders[i].shader_name,
                [[error localizedDescription] UTF8String]);
      continue;
    }

    id<MTLFunction> vfn =
        [library newFunctionWithName:moon_shaders[i].vertex_fn];
    id<MTLFunction> ffn =
        [library newFunctionWithName:moon_shaders[i].fragment_fn];
    if (!vfn || !ffn) {
      LOG_ERROR("Could not find vertex/fragment functions in '%s'",
                moon_shaders[i].shader_name);
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
      LOG_ERROR("Error creating pipeline for moon '%s': %s",
                moon_shaders[i].shader_name,
                [[error localizedDescription] UTF8String]);
      continue;
    }

    RenderState_SetMoonPipeline(state, moon_shaders[i].mclass,
                                (__bridge void *)pipeline);
    LOG_INFO("Compiled moon pipeline: %s", moon_shaders[i].shader_name);
  }

  // Update any existing moons that need pipeline states
  DynamicArray *moons = RenderState_GetMoons(state);
  if (moons) {
    size_t count = DynamicArray_length(moons);
    for (size_t i = 0; i < count; i++) {
      MTLMoonGraphicsClass *moon;
      DynamicArray_get(moons, i, &moon);

      if (moon && !moon->pipeline_state) {
        void *pipe = RenderState_GetMoonPipeline(state, moon->body->moon_class);
        if (pipe)
          moon->pipeline_state = (void *)CFBridgingRetain((__bridge id)pipe);
      }
    }
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

  void *pipe =
      RenderState_GetMoonPipeline(render_state, moon->body->moon_class);
  if (pipe) {
    if (moon->pipeline_state)
      CFRelease(moon->pipeline_state);

    moon->pipeline_state = (void *)CFBridgingRetain((__bridge id)pipe);
  }

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

bool MTLMoonGraphicsClass_draw(MTLMoonGraphicsClass *moon,
                               RenderState *render_state, void *encoder_ptr) {
  if (!moon)
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

  // 1. Moon Orbit Rendering with Frustum & Sub-pixel Culling
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
    host_pos = simd_make_float3((float)h_rel_x, (float)h_rel_y, (float)h_rel_z);
  }

  if (moon->orbit_buffer && moon->body->orbit) {
    float dist_to_host = simd_distance(cam_pos, host_pos);
    float max_orbit_r = (float)(moon->body->orbit->semimajor_axis *
                                (1.0 + moon->body->orbit->eccentricity) *
                                METERS_TO_RENDER_UNITS);

    // Sub-pixel culling: if orbit spans < 0.0005 radians (< 1 pixel on screen),
    // skip vertices
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

  // Compute light direction towards host star (or host planet's star)
  simd_float3 light_dir = simd_make_float3(0.0f, 0.0f, 1.0f);
  float light_intensity = 1.0f;
  if (moon->host_planet && moon->host_planet->host_star) {
    double sx = moon->host_planet->host_star->body->position.x *
                    METERS_TO_RENDER_UNITS -
                camera->center.x;
    double sy = moon->host_planet->host_star->body->position.y *
                    METERS_TO_RENDER_UNITS -
                camera->center.y;
    double sz = moon->host_planet->host_star->body->position.z *
                    METERS_TO_RENDER_UNITS -
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

  // Planetshine: secondary illumination from host planet
  simd_float4 host_color = (simd_float4){0.6f, 0.6f, 0.8f, 1.0f};
  float planetshine_intensity = 0.0f;
  if (moon->host_planet) {
    host_color = get_planet_color(moon->host_planet->body->planet_class);
    float dist_to_planet = simd_distance(body_pos, host_pos);
    float host_radius_render =
        (float)(moon->host_planet->body->radius_m * METERS_TO_RENDER_UNITS);

    if (dist_to_planet > 1e-4f)
      planetshine_intensity =
          fclamp((host_radius_render / dist_to_planet) * 1.5f, 0.15f, 0.60f);
  }

  // Elapsed animation time
  static uint64_t moon_start_time = 0;
  if (moon_start_time == 0)
    moon_start_time = mach_absolute_time();

  uint64_t cur_time = mach_absolute_time();
  mach_timebase_info_data_t tb;
  mach_timebase_info(&tb);
  float elapsed_sec = (float)(cur_time - moon_start_time) * (float)tb.numer /
                      (float)tb.denom / 1e9f;

  // Rotation speed
  float rot_speed = 0.04f;
  if (moon->body->rotation_period_days != 0.0) {
    double period = fabs(moon->body->rotation_period_days);
    if (period > 0.001) {
      rot_speed = (float)(0.05 / period);
      if (rot_speed < 0.005f)
        rot_speed = 0.005f;

      if (rot_speed > 0.20f)
        rot_speed = 0.20f;
    }
  }

  // Procedural seed
  uint32_t seed_val = 0;
  if (moon->body->name[0] != '\0') {
    for (const char *p = moon->body->name; *p; p++)
      seed_val = seed_val * 31 + (uint32_t)(*p);
  } else if (moon->body->body_id[0] != '\0') {
    for (const char *p = moon->body->body_id; *p; p++)
      seed_val = seed_val * 31 + (uint32_t)(*p);
  } else {
    seed_val = (uint32_t)(uintptr_t)moon;
  }

  float seed = (float)(seed_val % 1000) * 0.137f + 2.45f;

  MoonUniforms muniforms;
  memset(&muniforms, 0, sizeof(muniforms));
  muniforms.mvpMatrix = simd_mul(view_proj, model);
  muniforms.modelMatrix = model;
  apply_moon_specific_visuals(moon, &muniforms);
  muniforms.cameraPos = (PackedFloat3){cam_pos.x, cam_pos.y, cam_pos.z};
  muniforms.time = elapsed_sec;
  muniforms.lightDirection =
      (PackedFloat3){light_dir.x, light_dir.y, light_dir.z};
  muniforms.lightIntensity = light_intensity;
  muniforms.seed = seed;
  muniforms.rotationSpeed = rot_speed;
  muniforms.hostPlanetPos = (PackedFloat3){host_pos.x, host_pos.y, host_pos.z};
  muniforms.planetshineIntensity = planetshine_intensity;
  muniforms.hostPlanetColor = host_color;

  id<MTLRenderPipelineState> pipeline =
      moon->pipeline_state
          ? (__bridge id<MTLRenderPipelineState>)moon->pipeline_state
          : (__bridge id<MTLRenderPipelineState>)RenderState_GetMoonPipeline(
                render_state, moon->body->moon_class);
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
    fallback_uniforms.mvpMatrix = muniforms.mvpMatrix;
    fallback_uniforms.gridColor = muniforms.baseColor;

    [encoder setVertexBytes:&fallback_uniforms
                     length:sizeof(fallback_uniforms)
                    atIndex:1];
    [encoder setFragmentBytes:&fallback_uniforms
                       length:sizeof(fallback_uniforms)
                      atIndex:1];
  } else {
    [encoder setVertexBytes:&muniforms length:sizeof(muniforms) atIndex:1];
    [encoder setFragmentBytes:&muniforms length:sizeof(muniforms) atIndex:1];
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

  return true;
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