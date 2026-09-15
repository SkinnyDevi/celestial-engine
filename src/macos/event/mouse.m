#import "mouse.h"
#import <QuartzCore/QuartzCore.h>

#import "core/data/raycast.h"
#import "core/space/units.h"

#import "macos/render/space/moon.h"
#import "macos/render/space/planet.h"
#import "macos/render/space/star.h"

void event_left_mouse_down(RenderState *state, MousePoint mouse) {
  RenderState_SetDragging(state, true);
  RenderState_SetLastMouse(state, mouse.x, mouse.y);
}

void event_left_mouse_drag(RenderState *state, MousePoint current,
                           bool shiftHeld) {
  double lastX = 0.0;
  double lastY = 0.0;
  RenderState_GetLastMouse(state, &lastX, &lastY);

  double dx = current.x - lastX;
  double dy = current.y - lastY;
  RenderState_SetLastMouse(state, current.x, current.y);

  Camera *camera = RenderState_GetCamera(state);
  if (shiftHeld) {
    camera_pan_from_input(camera, (float)dx, (float)dy);
  } else {
    camera_orbit_from_input(camera, (float)dx, (float)dy);
  }
}

void check_intersect_stars(RenderState *state, MousePoint mouse,
                           simd_float3 ray_origin,
                           void (^check_intersect)(simd_float3, float)) {
  DynamicArray *stars = RenderState_GetStars(state);
  for (size_t i = 0; i < DynamicArray_length(stars); i++) {
    MTLStarGraphicsClass *star;
    DynamicArray_get(stars, i, &star);
    simd_float3 pos =
        simd_make_float3(star->body->position.x * METERS_TO_RENDER_UNITS,
                         star->body->position.y * METERS_TO_RENDER_UNITS,
                         star->body->position.z * METERS_TO_RENDER_UNITS);
    float base_radius = star->body->radius_m * METERS_TO_RENDER_UNITS;
    float dist = simd_distance(ray_origin, pos);
    float click_radius = dist * 0.02f; // Enlarge hitbox for easier clicking
    check_intersect(pos, fmaxf(base_radius, click_radius));
  }
}

void check_intersect_planets(RenderState *state, MousePoint mouse,
                             simd_float3 ray_origin,
                             void (^check_intersect)(simd_float3, float)) {
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
    float dist = simd_distance(ray_origin, pos);
    float click_radius = dist * 0.02f;
    check_intersect(pos, fmaxf(base_radius, click_radius));
  }
}

void check_intersect_moons(RenderState *state, MousePoint mouse,
                           simd_float3 ray_origin,
                           void (^check_intersect)(simd_float3, float)) {
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
    float dist = simd_distance(ray_origin, pos);
    float click_radius = dist * 0.02f;
    check_intersect(pos, fmaxf(base_radius, click_radius));
  }
}

void event_mouse_double_click(RenderState *state, MousePoint mouse) {
  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  CGSize size = metal_layer.bounds.size;

  Camera *camera = RenderState_GetCamera(state);
  float aspect = size.width / MAX(size.height, 1.0f);
  simd_float4x4 view = camera_view_matrix(camera);
  simd_float4x4 proj = camera_perspective(70.0f * (float)M_PI / 180.0f, aspect,
                                          0.1f, CAMERA_FAR_CLIPPING_PLANE);
  simd_float4x4 vp = simd_mul(proj, view);
  simd_float4x4 vp_inv = simd_inverse(vp);

  simd_float3 ray_origin = camera_orbit_position(camera);
  simd_float3 ray_dir = raycast_screen_to_world_dir(
      mouse.x, mouse.y, size.width, size.height, vp_inv, ray_origin);

  // Block: check intersection with a body
  __block float best_t = -1.0f;
  __block simd_float3 best_center = {0};
  __block float best_radius = 0;
  void (^check_intersect)(simd_float3, float) =
      ^(simd_float3 pos, float radius) {
        float t;
        if (raycast_intersects_sphere(ray_origin, ray_dir, pos, radius, &t)) {
          if (best_t < 0.0f || t < best_t) {
            best_t = t;
            best_center = pos;
            best_radius = radius;
          }
        }
      };

  check_intersect_stars(state, mouse, ray_origin, check_intersect);
  check_intersect_planets(state, mouse, ray_origin, check_intersect);
  check_intersect_moons(state, mouse, ray_origin, check_intersect);

  if (best_t >= 0.0f) {
    float zoom = fmaxf(best_radius * 5.0f, 1.0f);
    camera_start_transition_to(camera, best_center, zoom);
  }
}