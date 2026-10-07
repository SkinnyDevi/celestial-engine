#import "mouse.h"

#import "core/data/raycast.h"
#import "core/space/units.h"

#import "macos/render/space/moon.h"
#import "macos/render/space/planet.h"
#import "macos/render/space/star.h"

#import <QuartzCore/QuartzCore.h>

static inline float safe_distance(simd_float3 a, simd_float3 b) {
  double dx = (double)a.x - (double)b.x;
  double dy = (double)a.y - (double)b.y;
  double dz = (double)a.z - (double)b.z;
  return (float)sqrt(dx * dx + dy * dy + dz * dz);
}

void check_intersect_stars(RenderState *state, MousePoint mouse,
                           simd_float3 ray_origin,
                           void (^check_intersect)(simd_float3, float, float,
                                                   void *, FollowType)) {
  DynamicArray *stars = RenderState_GetStars(state);
  for (size_t i = 0; i < DynamicArray_length(stars); i++) {
    MTLStarGraphicsClass *star;
    DynamicArray_get(stars, i, &star);
    simd_float3 pos =
        simd_make_float3(star->body->position.x * METERS_TO_RENDER_UNITS,
                         star->body->position.y * METERS_TO_RENDER_UNITS,
                         star->body->position.z * METERS_TO_RENDER_UNITS);
    float base_radius = star->body->radius_m * METERS_TO_RENDER_UNITS;
    float dist = safe_distance(ray_origin, pos);
    float click_radius = dist * 0.02f; // Enlarge hitbox for easier clicking
    check_intersect(pos, base_radius, fmaxf(base_radius, click_radius), star,
                    FOLLOW_STAR);
  }
}

void check_intersect_planets(RenderState *state, MousePoint mouse,
                             simd_float3 ray_origin,
                             void (^check_intersect)(simd_float3, float, float,
                                                     void *, FollowType)) {
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
    float dist = safe_distance(ray_origin, pos);
    float click_radius = dist * 0.02f;
    check_intersect(pos, base_radius, fmaxf(base_radius, click_radius), planet,
                    FOLLOW_PLANET);
  }
}

void check_intersect_moons(RenderState *state, MousePoint mouse,
                           simd_float3 ray_origin,
                           void (^check_intersect)(simd_float3, float, float,
                                                   void *, FollowType)) {
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
    float dist = safe_distance(ray_origin, pos);
    float click_radius = dist * 0.02f;
    check_intersect(pos, base_radius, fmaxf(base_radius, click_radius), moon,
                    FOLLOW_MOON);
  }
}

bool raycast_find_body(RenderState *state, MousePoint mouse, void **out_obj,
                       FollowType *out_type, float *out_radius,
                       simd_float3 *out_center) {
  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  CGSize size = metal_layer.bounds.size;

  Camera *camera = RenderState_GetCamera(state);
  simd_float4x4 view = camera_view_matrix(camera);
  simd_float4x4 view_inv = simd_inverse(view);

  simd_float3 ray_origin = camera_orbit_position(camera);
  simd_float3 ray_dir =
      raycast_screen_to_world_dir(mouse.x, mouse.y, size.width, size.height,
                                  view_inv, 70.0f * (float)M_PI / 180.0f);

  // Block: check intersection with a body
  __block float best_score = INFINITY;
  __block float best_t = -1.0f;
  __block simd_float3 best_center = {0};
  __block float best_base_radius = 0;
  __block void *best_obj = NULL;
  __block FollowType best_type = FOLLOW_NONE;
  void (^check_intersect)(simd_float3, float, float, void *, FollowType) = ^(
      simd_float3 pos, float base_radius, float hit_radius, void *obj,
      FollowType type) {
    float t;
    if (!raycast_intersects_sphere(ray_origin, ray_dir, pos, hit_radius, &t))
      return;

    simd_float3 m = ray_origin - pos;
    double ox = ray_origin.x, oy = ray_origin.y, oz = ray_origin.z;
    double px = pos.x, py = pos.y, pz = pos.z;
    double dx = ray_dir.x, dy = ray_dir.y, dz = ray_dir.z;

    double mx = ox - px;
    double my = oy - py;
    double mz = oz - pz;

    double b = mx * dx + my * dy + mz * dz;
    double c = mx * mx + my * my + mz * mz;
    double perp_dist_sq = fmax(0.0, c - b * b);

    // Use normalized distances to enlarge the hitboxes
    float score =
        (float)(perp_dist_sq / ((double)hit_radius * (double)hit_radius));
    score += t * 1e-12f; // Evade objects behind the clicked object

    if (score < best_score) {
      best_score = score;
      best_t = t;
      best_center = pos;
      best_base_radius = base_radius;
      best_obj = obj;
      best_type = type;
    }
  };

  check_intersect_stars(state, mouse, ray_origin, check_intersect);
  check_intersect_planets(state, mouse, ray_origin, check_intersect);
  check_intersect_moons(state, mouse, ray_origin, check_intersect);

  if (best_t >= 0.0f) {
    if (out_obj)
      *out_obj = best_obj;
    if (out_type)
      *out_type = best_type;
    if (out_radius)
      *out_radius = best_base_radius;
    if (out_center)
      *out_center = best_center;
    return true;
  }
  return false;
}

void event_mouse_double_click(RenderState *state, MousePoint mouse) {
  void *best_obj = NULL;
  FollowType best_type = FOLLOW_NONE;
  float best_base_radius = 0;
  simd_float3 best_center = {0};

  if (raycast_find_body(state, mouse, &best_obj, &best_type, &best_base_radius,
                        &best_center)) {
    float zoom = fmaxf(best_base_radius * 5.0f, 1.0f);
    RenderState_SetFollowedBody(state, best_type, best_obj);
    Camera *camera = RenderState_GetCamera(state);
    camera_start_transition_to(camera, best_center, zoom);
  }
}

void event_left_mouse_down(RenderState *state, MousePoint mouse,
                           bool shiftHeld) {
  RenderState_SetDragging(state, true);
  RenderState_SetLastMouse(state, mouse.x, mouse.y);

  if (shiftHeld) {
    void *best_obj = NULL;
    FollowType best_type = FOLLOW_NONE;
    float best_base_radius = 0;
    simd_float3 best_center = {0};

    if (raycast_find_body(state, mouse, &best_obj, &best_type,
                          &best_base_radius, &best_center))
      RenderState_SetGridFollowedBody(state, best_type, best_obj);
    else
      RenderState_ClearGridFollowedBody(state);
  }
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
    RenderState_ClearFollowedBody(state);
    camera_pan_from_input(camera, (float)dx, (float)dy);
  } else {
    camera_orbit_from_input(camera, (float)dx, (float)dy);
  }
}