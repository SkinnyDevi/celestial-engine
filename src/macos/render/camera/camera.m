#import "camera.h"
#import "core/space/units.h"

#import "macos/render/grid/displaced_mesh.h"
#import "macos/render/shape/vertex.h"
#import "macos/render/space/moon.h"
#import "macos/render/space/planet.h"
#import "macos/render/space/star.h"
#import "macos/render/state/render_state.h"

#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <math.h>

void camera_init(Camera *camera) {
  if (!camera) {
    return;
  }
  // Blender-style 3/4 elevated view: 45° azimuth, ~25° elevation
  camera->azimuth = 0.7854f;   // 45°
  camera->elevation = 0.4363f; // 25°
  camera->zoom = 12.0f;
  camera->center = simd_make_float3(0.0f, 0.0f, 0.0f);
  camera->is_transitioning = false;
  camera->transition_progress = 0.0f;
}

simd_float3 camera_orbit_position(const Camera *camera) {
  if (!camera) {
    return simd_make_float3(0.0f, 0.0f, 0.0f);
  }

  float ce = cosf(camera->elevation);
  float se = sinf(camera->elevation);
  float ca = cosf(camera->azimuth);
  float sa = sinf(camera->azimuth);

  // Position on sphere matches the Rx(elev) * Ry(-az) view rotation
  simd_float3 offset = simd_make_float3(
      sa * ce * camera->zoom, se * camera->zoom, ca * ce * camera->zoom);

  return camera->center + offset;
}

simd_float4x4 camera_view_matrix(const Camera *camera) {
  if (!camera) {
    simd_float4x4 identity = {0};
    identity.columns[0] = simd_make_float4(1, 0, 0, 0);
    identity.columns[1] = simd_make_float4(0, 1, 0, 0);
    identity.columns[2] = simd_make_float4(0, 0, 1, 0);
    identity.columns[3] = simd_make_float4(0, 0, 0, 1);
    return identity;
  }

  float ca = cosf(camera->azimuth);
  float sa = sinf(camera->azimuth);
  float ce = cosf(camera->elevation);
  float se = sinf(camera->elevation);
  float d = camera->zoom;

  float cx = camera->center.x;
  float cy = camera->center.y;
  float cz = camera->center.z;

  // View Matrix = Translate(0,0,-zoom) * Rx(elev) * Ry(-az) *
  // Translate(-center)
  float tx = ca * (-cx) - sa * (-cz);
  float ty = -se * sa * (-cx) + ce * (-cy) - se * ca * (-cz);
  float tz = ce * sa * (-cx) + se * (-cy) + ce * ca * (-cz) - d;

  simd_float4x4 view;
  view.columns[0] = simd_make_float4(ca, -se * sa, ce * sa, 0.0f);
  view.columns[1] = simd_make_float4(0.0f, ce, se, 0.0f);
  view.columns[2] = simd_make_float4(-sa, -se * ca, ce * ca, 0.0f);
  view.columns[3] = simd_make_float4(tx, ty, tz, 1.0f);

  return view;
}

simd_float4x4 camera_perspective(float fovRadians, float aspect, float nearZ,
                                 float farZ) {
  float yScale = 1.0f / tanf(fovRadians * 0.5f);
  float xScale = yScale / aspect;

  // Right-handed Metal projection (Z goes from 0 to 1 in NDC, clip_w = -z)
  float A = farZ / (nearZ - farZ);
  float B = (farZ * nearZ) / (nearZ - farZ);

  simd_float4x4 projection;
  projection.columns[0] = simd_make_float4(xScale, 0.0f, 0.0f, 0.0f);
  projection.columns[1] = simd_make_float4(0.0f, yScale, 0.0f, 0.0f);
  projection.columns[2] = simd_make_float4(0.0f, 0.0f, A, -1.0f);
  projection.columns[3] = simd_make_float4(0.0f, 0.0f, B, 0.0f);

  return projection;
}

void camera_orbit_from_input(Camera *camera, float dx, float dy) {
  if (!camera) {
    return;
  }
  camera->azimuth -= dx * kOrbitSensitivity;
  camera->elevation += dy * kOrbitSensitivity;
  camera->elevation =
      fminf(kMaxElevation, fmaxf(-kMaxElevation, camera->elevation));
}

void camera_pan_from_input(Camera *camera, float dx, float dy) {
  if (!camera) {
    return;
  }

  float ca = cosf(camera->azimuth);
  float sa = sinf(camera->azimuth);
  float ce = cosf(camera->elevation);
  float se = sinf(camera->elevation);

  // Camera Right (Row 0 of view rotation)
  simd_float3 right = simd_make_float3(ca, 0.0f, -sa);
  // Camera Up (Row 1 of view rotation)
  simd_float3 up = simd_make_float3(-se * sa, ce, -se * ca);

  float panSpeed = camera->zoom * 0.002f;
  camera->center =
      camera->center - right * (dx * panSpeed) - up * (dy * panSpeed);
}

void camera_zoom_from_input(Camera *camera, float scrollDelta) {
  if (!camera) {
    return;
  }
  if (scrollDelta > 0.0f) {
    camera->zoom /= powf(kZoomFactor, scrollDelta);
  } else if (scrollDelta < 0.0f) {
    camera->zoom *= powf(kZoomFactor, -scrollDelta);
  }
  camera->zoom = fmaxf(kMinzoom, fminf(kMaxzoom, camera->zoom));
}

void camera_focus_on(Camera *camera, simd_float3 target, float zoom) {
  if (!camera) {
    return;
  }
  camera->center = target;
  if (zoom > 0.0f) {
    camera->zoom = fmaxf(kMinzoom, zoom);
  }
}

void camera_set_position(Camera *camera, simd_float3 position) {
  if (!camera) {
    return;
  }

  simd_float3 offset = position - camera->center;
  float dist = simd_length(offset);

  if (dist < 1e-6f) {
    camera->zoom = fmaxf(kMinzoom, dist);
    return;
  }

  camera->zoom = fmaxf(kMinzoom, dist);
  camera->elevation = asinf(offset.y / dist);
  camera->elevation =
      fminf(kMaxElevation, fmaxf(-kMaxElevation, camera->elevation));
  camera->azimuth = atan2f(offset.x, offset.z);
}

void camera_start_transition_to(Camera *camera, simd_float3 target,
                                float zoom) {
  if (!camera)
    return;
  camera->start_center = camera->center;
  camera->target_center = target;
  camera->start_zoom = camera->zoom;
  camera->target_zoom = fmaxf(kMinzoom, zoom);
  camera->is_transitioning = true;
  camera->transition_progress = 0.0f;
}

static inline float ease_in_out_cubic(float t) {
  return t < 0.5f ? 4.0f * t * t * t
                  : 1.0f - powf(-2.0f * t + 2.0f, 3.0f) / 2.0f;
}

void camera_update_transition(Camera *camera, float dt) {
  if (!camera || !camera->is_transitioning)
    return;

  float speed = 2.0f; // 0.5 seconds for a full transition
  camera->transition_progress += dt * speed;

  if (camera->transition_progress >= 1.0f) {
    camera->transition_progress = 1.0f;
    camera->is_transitioning = false;
  }

  float t = ease_in_out_cubic(camera->transition_progress);
  camera->center = simd_mix(camera->start_center, camera->target_center, t);
  camera->zoom =
      camera->start_zoom + (camera->target_zoom - camera->start_zoom) * t;
}

void camera_get_clipping_planes(const Camera *camera, float *near_out,
                                float *far_out) {
  if (camera) {
    *near_out = fmaxf(CAMERA_NEAR_CLIPPING_PLANE, camera->zoom * 0.001f);
    *far_out = fmaxf(CAMERA_FAR_CLIPPING_PLANE, camera->zoom * 1000.0f);
  } else {
    *near_out = CAMERA_NEAR_CLIPPING_PLANE;
    *far_out = CAMERA_FAR_CLIPPING_PLANE;
  }
}

void update_camera_uniforms(RenderState *state) {
  if (!state || !RenderState_GetUniformBuffer(state))
    return;

  Camera *camera = RenderState_GetCamera(state);

  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  float aspect = metal_layer.drawableSize.width /
                 MAX(metal_layer.drawableSize.height, 1.0f);

  simd_float4x4 view = camera_view_matrix(camera);
  float near_plane, far_plane;
  camera_get_clipping_planes(camera, &near_plane, &far_plane);
  simd_float4x4 projection = camera_perspective(70.0f * (float)M_PI / 180.0f,
                                                aspect, near_plane, far_plane);

  DisplacedMeshUniforms uniforms;
  uniforms.mvpMatrix = simd_mul(projection, view);
  uniforms.gridColor =
      (simd_float4){1.0f, 1.0f, 1.0f, DISPLACED_MESH_GRID_OPACITY};

  id<MTLBuffer> uniform_buffer =
      (__bridge id<MTLBuffer>)RenderState_GetUniformBuffer(state);
  memcpy([uniform_buffer contents], &uniforms, sizeof(uniforms));
}

void camera_follow_star(void *fobj, simd_float3 *body_pos_out) {
  MTLStarGraphicsClass *star = fobj;
  *body_pos_out =
      simd_make_float3(star->body->position.x * METERS_TO_RENDER_UNITS,
                       star->body->position.y * METERS_TO_RENDER_UNITS,
                       star->body->position.z * METERS_TO_RENDER_UNITS);
}

void camera_follow_planet(void *fobj, simd_float3 *body_pos_out) {
  MTLPlanetGraphicsClass *planet = fobj;
  double ax = planet->body->position.x;
  double ay = planet->body->position.y;
  double az = planet->body->position.z;
  if (planet->host_star) {
    ax += planet->host_star->body->position.x;
    ay += planet->host_star->body->position.y;
    az += planet->host_star->body->position.z;
  }
  *body_pos_out =
      simd_make_float3(ax * METERS_TO_RENDER_UNITS, ay * METERS_TO_RENDER_UNITS,
                       az * METERS_TO_RENDER_UNITS);
}

void camera_follow_moon(void *fobj, simd_float3 *body_pos_out) {
  MTLMoonGraphicsClass *moon = fobj;
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
  *body_pos_out =
      simd_make_float3(ax * METERS_TO_RENDER_UNITS, ay * METERS_TO_RENDER_UNITS,
                       az * METERS_TO_RENDER_UNITS);
}

void camera_follow_body(RenderState *state) {
  FollowType ftype = RenderState_GetFollowedType(state);
  void *fobj = RenderState_GetFollowedBody(state);
  simd_float3 body_pos = {0};

  switch (ftype) {
  case FOLLOW_STAR:
    camera_follow_star(fobj, &body_pos);
    break;
  case FOLLOW_PLANET:
    camera_follow_planet(fobj, &body_pos);
    break;
  case FOLLOW_MOON:
    camera_follow_moon(fobj, &body_pos);
    break;
  default: // FOLLOW_NONE
    break;
  }

  Camera *cam = RenderState_GetCamera(state);
  if (cam->is_transitioning) {
    cam->target_center = body_pos;
  } else {
    cam->center = body_pos;
  }
}