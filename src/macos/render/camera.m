#include <math.h>

#include "core/renderer/camera/camera.h"

static const float kOrbitSensitivity = 0.007f;
static const float kMaxElevation = M_PI / 2.0f; // 90 degree clamp
static const float kZoomFactor = 1.05f;
static const float kMinzoom = 0.5f;
static const float kMaxzoom = 1000.0f;

void camera_init(Camera *camera) {
  if (!camera) {
    return;
  }
  // Blender-style 3/4 elevated view: 45° azimuth, ~25° elevation
  camera->azimuth = 0.7854f;   // 45°
  camera->elevation = 0.4363f; // 25°
  camera->zoom = 12.0f;
  camera->center = simd_make_float3(0.0f, 0.0f, 0.0f);
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
