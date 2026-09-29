#import "graphics.h"

#import "core/cli/instance_data.h"
#import "core/data/math.h"
#import "core/log/log.h"
#import "core/space/units.h"

#import "macos/debug/camera_properties.h"
#import "macos/debug/flags.h"
#import "macos/debug/fps_counter.h"
#import "macos/debug/sphere_wireframe.h"
#import "macos/debug/time_overlay.h"

#import "macos/render/space/moon.h"
#import "macos/render/space/planet.h"
#import "macos/render/space/star.h"

#import "macos/render/shape/vertex.h"
#import "macos/render/state/render_state.h"

#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <simd/simd.h>

#if DEBUG_CAMERA_PATH_WIREFRAME_VISIBLE
id<MTLBuffer> debug_camera_orbit_sphere_buffer = nil;
int debug_camera_orbit_sphere_vertices = 0;
#endif

#if DEBUG_CAMERA_FIXATION_POINT_VISIBLE
id<MTLBuffer> debug_camera_fixation_sphere_buffer = nil;
int debug_camera_fixation_sphere_vertices = 0;
#endif

#if DEBUG_HITBOX_WIREFRAME_VISIBLE
id<MTLBuffer> debug_hitbox_sphere_buffer = nil;
int debug_hitbox_sphere_vertices = 0;
#endif

FPSData fps_data;

void generate_debug_graphics(RenderState *state) {
  if (cli_should_show_fps() || cli_is_debug_mode())
    debug_create_fps_counter_overlay(state);

  if (!cli_is_debug_mode())
    return;

#if DEBUG_CAMERA_PROPERTIES_VISIBLE
  debug_create_camera_properties_overlay(state);
#endif

  debug_create_time_overlay(state);

  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);

#if DEBUG_CAMERA_PATH_WIREFRAME_VISIBLE
  int orbit_count = 0;
  Vertex *orbit_vertices =
      debug_generate_quality_sphere_wireframe(4, MEDIUM_QUALITY, &orbit_count);
  debug_camera_orbit_sphere_buffer =
      [metal_layer.device newBufferWithBytes:orbit_vertices
                                      length:(sizeof(Vertex) * orbit_count)
                                     options:MTLResourceStorageModeShared];
  debug_camera_orbit_sphere_vertices = orbit_count;
  free(orbit_vertices);
  LOG_DEBUG("Orbit sphere buffer: %d vertices, buffer=%p", orbit_count,
            (__bridge void *)debug_camera_orbit_sphere_buffer);
#endif

#if DEBUG_CAMERA_FIXATION_POINT_VISIBLE
  int fixation_count = 0;
  Vertex *fixation_vertices = debug_generate_quality_sphere_wireframe(
      4, MEDIUM_QUALITY, &fixation_count);
  debug_camera_fixation_sphere_buffer =
      [metal_layer.device newBufferWithBytes:fixation_vertices
                                      length:(sizeof(Vertex) * fixation_count)
                                     options:MTLResourceStorageModeShared];
  debug_camera_fixation_sphere_vertices = fixation_count;
  free(fixation_vertices);
  LOG_DEBUG("Fixation sphere buffer: %d vertices, buffer=%p", fixation_count,
            (__bridge void *)debug_camera_fixation_sphere_buffer);
#endif

#if DEBUG_HITBOX_WIREFRAME_VISIBLE
  int hitbox_count = 0;
  Vertex *hitbox_vertices =
      debug_generate_quality_sphere_wireframe(4, MEDIUM_QUALITY, &hitbox_count);
  debug_hitbox_sphere_buffer =
      [metal_layer.device newBufferWithBytes:hitbox_vertices
                                      length:(sizeof(Vertex) * hitbox_count)
                                     options:MTLResourceStorageModeShared];
  debug_hitbox_sphere_vertices = hitbox_count;
  free(hitbox_vertices);
  LOG_DEBUG("Hitbox sphere buffer: %d vertices", hitbox_count);
#endif
}

void draw_debug_fps(RenderState *state, bool use_extended_data,
                    FPSData *out_data) {
  if (!cli_is_debug_mode() && !cli_should_show_fps())
    return;

  DebugOverlay *overlay = RenderState_GetFPSCounterOverlay(state);
  if (!overlay)
    return;

  debug_overlay_clear(overlay);
  debug_overlay_update_fps(overlay, use_extended_data, out_data);
}

void update_camera_debug_properties(Camera *cam) {
#if DEBUG_CAMERA_PROPERTIES_VISIBLE
  unsigned long long debug_frame_counter = fps_data.frame_count;
  if (debug_frame_counter % 120 == 0) {
    simd_float3 cam_pos = camera_orbit_position(cam);
    LOG_DEBUG(
        "[Frame %llu | FPS %.2f] Camera: zoom=%.3f center=(%.2f, %.2f, %.2f) "
        "pos=(%.2f, %.2f, %.2f)",
        debug_frame_counter, fps_data.fps_avg, cam->zoom, cam->center.x,
        cam->center.y, cam->center.z, cam_pos.x, cam_pos.y, cam_pos.z);
  }
#endif
}

void update_debug_time_overlay(RenderState *state) {
  DebugOverlay *time_overlay = RenderState_GetTimeOverlay(state);
  if (time_overlay) {
    debug_overlay_clear(time_overlay);
    debug_overlay_update_time(time_overlay, RenderState_GetSimTime(state));
  }
}

void update_camera_path_wireframe(Camera *cam, simd_float4x4 vp,
                                  id<MTLRenderCommandEncoder> encoder) {
#if DEBUG_CAMERA_PATH_WIREFRAME_VISIBLE
  {
    simd_float4x4 model = simd_mul(make_translation_matrix(cam->center),
                                   make_scale_matrix(cam->zoom));
    DisplacedMeshUniforms mesh_uniforms;
    mesh_uniforms.mvpMatrix = simd_mul(vp, model);
    mesh_uniforms.gridColor = (simd_float4){1.0f, 0.41f, 0.71f, 0.7f}; // Pink

    [encoder setVertexBuffer:debug_camera_orbit_sphere_buffer
                      offset:0
                     atIndex:0];
    [encoder setVertexBytes:&mesh_uniforms
                     length:sizeof(mesh_uniforms)
                    atIndex:1];
    [encoder setFragmentBytes:&mesh_uniforms
                       length:sizeof(mesh_uniforms)
                      atIndex:1];
    [encoder drawPrimitives:MTLPrimitiveTypeLine
                vertexStart:0
                vertexCount:debug_camera_orbit_sphere_vertices];
  }
#endif
}

void update_debug_camera_fixation_point(Camera *cam, simd_float4x4 vp,
                                        id<MTLRenderCommandEncoder> encoder) {
#if DEBUG_CAMERA_FIXATION_POINT_VISIBLE
  {
    float fixation_radius = 0.15f;
    simd_float4x4 model = simd_mul(make_translation_matrix(cam->center),
                                   make_scale_matrix(fixation_radius));
    DisplacedMeshUniforms mesh_uniforms;
    mesh_uniforms.mvpMatrix = simd_mul(vp, model);
    mesh_uniforms.gridColor = (simd_float4){1.0f, 0.15f, 0.15f, 1.0f}; // Red

    [encoder setVertexBuffer:debug_camera_fixation_sphere_buffer
                      offset:0
                     atIndex:0];
    [encoder setVertexBytes:&mesh_uniforms
                     length:sizeof(mesh_uniforms)
                    atIndex:1];
    [encoder setFragmentBytes:&mesh_uniforms
                       length:sizeof(mesh_uniforms)
                      atIndex:1];
    [encoder drawPrimitives:MTLPrimitiveTypeLine
                vertexStart:0
                vertexCount:debug_camera_fixation_sphere_vertices];
  }
#endif
}

void draw_debug_hitbox_wireframe_for_stars(
    RenderState *state, Camera *cam, simd_float4x4 vp,
    id<MTLRenderCommandEncoder> encoder,
    void (^draw_hitbox)(simd_float3, float, simd_float4),
    simd_float3 ray_origin) {
#if DEBUG_HITBOX_WIREFRAME_VISIBLE
  {
    DynamicArray *stars = RenderState_GetStars(state);
    for (size_t i = 0; i < DynamicArray_length(stars); i++) {
      MTLStarGraphicsClass *star;
      DynamicArray_get(stars, i, &star);
      simd_float3 pos =
          simd_make_float3(star->body->position.x * METERS_TO_RENDER_UNITS,
                           star->body->position.y * METERS_TO_RENDER_UNITS,
                           star->body->position.z * METERS_TO_RENDER_UNITS);
      float base_radius = star->body->radius_m * METERS_TO_RENDER_UNITS;
      draw_hitbox(pos,
                  fmaxf(base_radius, simd_distance(ray_origin, pos) * 0.02f),
                  (simd_float4){0.0f, 1.0f, 0.0f, 1.0f});
    }
  }
#endif
}

void draw_debug_hitbox_wireframe_for_planets(
    RenderState *state, Camera *cam, simd_float4x4 vp,
    id<MTLRenderCommandEncoder> encoder,
    void (^draw_hitbox)(simd_float3, float, simd_float4),
    simd_float3 ray_origin) {
#if DEBUG_HITBOX_WIREFRAME_VISIBLE
  {
    DynamicArray *planets = RenderState_GetPlanets(state);
    for (size_t i = 0; i < DynamicArray_length(planets); i++) {
      MTLPlanetGraphicsClass *planet;
      DynamicArray_get(planets, i, &planet);
      double ax = planet->body->position.x;
      double ay = planet->body->position.y;
      double az = planet->body->position.z;
      if (planet->host_star) {
        ax += planet->host_star->body->position.x;
        ay += planet->host_star->body->position.y;
        az += planet->host_star->body->position.z;
      }
      simd_float3 pos = simd_make_float3(ax * METERS_TO_RENDER_UNITS,
                                         ay * METERS_TO_RENDER_UNITS,
                                         az * METERS_TO_RENDER_UNITS);
      float base_radius = planet->body->radius_m * METERS_TO_RENDER_UNITS;
      draw_hitbox(pos,
                  fmaxf(base_radius, simd_distance(ray_origin, pos) * 0.02f),
                  (simd_float4){0.0f, 1.0f, 0.0f, 1.0f});
    }
  }
#endif
}

void draw_debug_hitbox_wireframe_for_moons(
    RenderState *state, Camera *cam, simd_float4x4 vp,
    id<MTLRenderCommandEncoder> encoder,
    void (^draw_hitbox)(simd_float3, float, simd_float4),
    simd_float3 ray_origin) {
#if DEBUG_HITBOX_WIREFRAME_VISIBLE
  {
    DynamicArray *moons = RenderState_GetMoons(state);
    for (size_t i = 0; i < DynamicArray_length(moons); i++) {
      MTLMoonGraphicsClass *moon;
      DynamicArray_get(moons, i, &moon);
      double ax = moon->body->position.x;
      double ay = moon->body->position.y;
      double az = moon->body->position.z;
      if (moon->host_planet) {
        ax += moon->host_planet->body->position.x;
        ay += moon->host_planet->body->position.y;
        az += moon->host_planet->body->position.z;
        if (moon->host_planet->host_star) {
          ax += moon->host_planet->host_star->body->position.x;
          ay += moon->host_planet->host_star->body->position.y;
          az += moon->host_planet->host_star->body->position.z;
        }
      }
      simd_float3 pos = simd_make_float3(ax * METERS_TO_RENDER_UNITS,
                                         ay * METERS_TO_RENDER_UNITS,
                                         az * METERS_TO_RENDER_UNITS);
      float base_radius = moon->body->radius_m * METERS_TO_RENDER_UNITS;
      draw_hitbox(pos,
                  fmaxf(base_radius, simd_distance(ray_origin, pos) * 0.02f),
                  (simd_float4){0.0f, 1.0f, 0.0f, 1.0f});
    }
  }
#endif
}

void draw_debug_hitbox_wireframe(RenderState *state, Camera *cam,
                                 id<MTLRenderCommandEncoder> encoder,
                                 simd_float4x4 vp) {
#if DEBUG_HITBOX_WIREFRAME_VISIBLE
  simd_float3 ray_origin = camera_orbit_position(cam);
  [encoder setVertexBuffer:debug_hitbox_sphere_buffer offset:0 atIndex:0];

  void (^draw_hitbox)(simd_float3, float, simd_float4) =
      ^(simd_float3 pos, float radius, simd_float4 color) {
        simd_float4x4 model =
            simd_mul(make_translation_matrix(pos), make_scale_matrix(radius));
        DisplacedMeshUniforms mesh_uniforms;
        mesh_uniforms.mvpMatrix = simd_mul(vp, model);
        mesh_uniforms.gridColor = color;
        [encoder setVertexBytes:&mesh_uniforms
                         length:sizeof(mesh_uniforms)
                        atIndex:1];
        [encoder setFragmentBytes:&mesh_uniforms
                           length:sizeof(mesh_uniforms)
                          atIndex:1];
        [encoder drawPrimitives:MTLPrimitiveTypeLine
                    vertexStart:0
                    vertexCount:debug_hitbox_sphere_vertices];
      };

  draw_debug_hitbox_wireframe_for_stars(state, cam, vp, encoder, draw_hitbox,
                                        ray_origin);
  draw_debug_hitbox_wireframe_for_planets(state, cam, vp, encoder, draw_hitbox,
                                          ray_origin);
  draw_debug_hitbox_wireframe_for_moons(state, cam, vp, encoder, draw_hitbox,
                                        ray_origin);
#endif
}

void draw_debug_graphics(RenderState *state, void *encoder_void) {
  id<MTLRenderCommandEncoder> encoder =
      (__bridge id<MTLRenderCommandEncoder>)encoder_void;

  draw_debug_fps(state,
                 DEBUG_FPS_COUNTER_ADVANCED_VISIBLE &&
                     cli_should_show_advanced_fps(),
                 &fps_data);

  if (!cli_is_debug_mode())
    return;

  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);

  Camera *cam = RenderState_GetCamera(state);
  float aspect = metal_layer.drawableSize.width /
                 MAX(metal_layer.drawableSize.height, 1.0f);
  simd_float4x4 view = camera_view_matrix(cam);
  simd_float4x4 proj =
      camera_perspective(70.0f * (float)M_PI / 180.0f, aspect, 0.1f, 10000.0f);
  simd_float4x4 vp = simd_mul(proj, view);

  update_camera_debug_properties(cam);
  update_debug_time_overlay(state);
  update_camera_path_wireframe(cam, vp, encoder);
  update_debug_camera_fixation_point(cam, vp, encoder);
  draw_debug_hitbox_wireframe(state, cam, encoder, vp);
}