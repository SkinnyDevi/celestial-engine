#include "../camera/camera.h"

#include <math.h>

// Blender turntable orbit sensitivity: ~0.4 degrees per pixel ≈ 0.007 rad/pixel
static const float kOrbitSensitivity = 0.007f;

// Elevation clamped to ±89° to prevent gimbal lock at the poles
static const float kMaxElevation = 1.5533f; // ~89°

// Zoom multiplier per scroll unit — exponential for zoom-independent feel
static const float kZoomFactor = 1.1f;

// Minimum orbit zoom
static const float kMinzoom = 0.5f;

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

  // Derived from the view matrix: camera world position is
  // center + R^T * (0, 0, zoom), where R = Rx(elev) * Ry(az).
  float ce = cosf(camera->elevation);
  float se = sinf(camera->elevation);
  float ca = cosf(camera->azimuth);
  float sa = sinf(camera->azimuth);

  simd_float3 offset = simd_make_float3(
      -ce * sa * camera->zoom, se * camera->zoom, ce * ca * camera->zoom);

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

  // Blender-style "rotate the world" view matrix construction:
  //   V = Translate(0, 0, -zoom) * RotateX(elevation) * RotateY(azimuth) *
  //   Translate(-center)
  //
  // Instead of positioning the camera on a sphere and using look_at (which
  // re-derives orientation from position + target + up, causing wobble and
  // axis inconsistencies), this directly applies the rotation to the entire
  // scene. The camera conceptually stays at the origin looking down -Z,
  // and the world rotates around the pivot point.
  //
  // R = Rx(elev) * Ry(az):
  //   row 0: ( ca,        0,       sa      )   ← camera right in world space
  //   row 1: ( se·sa,     ce,     -se·ca   )   ← camera up in world space
  //   row 2: (-ce·sa,     se,      ce·ca   )   ← camera backward (-forward) in
  //   world space

  float ca = cosf(camera->azimuth);
  float sa = sinf(camera->azimuth);
  float ce = cosf(camera->elevation);
  float se = sinf(camera->elevation);
  float d = camera->zoom;

  float cx = camera->center.x;
  float cy = camera->center.y;
  float cz = camera->center.z;

  // Translation = R * (-center) + (0, 0, -zoom)
  float tx = ca * (-cx) + sa * (-cz);
  float ty = se * sa * (-cx) + ce * (-cy) - se * ca * (-cz);
  float tz = -ce * sa * (-cx) + se * (-cy) + ce * ca * (-cz) - d;

  // Column-major: columns[i] = (row0_i, row1_i, row2_i, 0)
  simd_float4x4 view;
  view.columns[0] = simd_make_float4(ca, se * sa, -ce * sa, 0.0f);
  view.columns[1] = simd_make_float4(0.0f, ce, se, 0.0f);
  view.columns[2] = simd_make_float4(sa, -se * ca, ce * ca, 0.0f);
  view.columns[3] = simd_make_float4(tx, ty, tz, 1.0f);

  return view;
}

simd_float4x4 camera_perspective(float fovRadians, float aspect, float nearZ,
                                 float farZ) {
  float yScale = 1.0f / tanf(fovRadians * 0.5f);
  float xScale = yScale / aspect;
  float zRange = farZ / (farZ - nearZ);

  simd_float4x4 projection;
  projection.columns[0] = simd_make_float4(xScale, 0.0f, 0.0f, 0.0f);
  projection.columns[1] = simd_make_float4(0.0f, yScale, 0.0f, 0.0f);
  projection.columns[2] = simd_make_float4(0.0f, 0.0f, zRange, 1.0f);
  projection.columns[3] =
      simd_make_float4(0.0f, 0.0f, -(farZ * nearZ) / (farZ - nearZ), 0.0f);

  return projection;
}

void camera_orbit_from_input(Camera *camera, float dx, float dy) {
  if (!camera) {
    return;
  }

  // Blender turntable orbit:
  // - Drag RIGHT → azimuth decreases → world rotates CW from top → camera
  // orbits right
  // - Drag UP    → elevation increases → world tilts forward → camera orbits up
  camera->azimuth -= dx * kOrbitSensitivity;
  camera->elevation += dy * kOrbitSensitivity;
  camera->elevation =
      fminf(kMaxElevation, fmaxf(-kMaxElevation, camera->elevation));
}

void camera_pan_from_input(Camera *camera, float dx, float dy) {
  if (!camera) {
    return;
  }

  // Camera right and up in world space, derived from the view rotation matrix.
  // These are rows 0 and 1 of R = Rx(elev) * Ry(az).
  float ca = cosf(camera->azimuth);
  float sa = sinf(camera->azimuth);
  float ce = cosf(camera->elevation);
  float se = sinf(camera->elevation);

  simd_float3 right = simd_make_float3(ca, 0.0f, sa);
  simd_float3 up = simd_make_float3(se * sa, ce, -se * ca);

  // Scale pan speed relative to zoom for consistent feel at all zoom levels.
  // Subtract: dragging right moves center left → scene slides right on screen
  // (grab metaphor).
  float panSpeed = camera->zoom * 0.002f;
  camera->center =
      camera->center - right * (dx * panSpeed) - up * (dy * panSpeed);
}

void camera_zoom_from_input(Camera *camera, float scrollDelta) {
  if (!camera) {
    return;
  }

  // Exponential zoom: multiply/divide zoom by a factor per scroll unit.
  // This gives consistent zoom feel regardless of zoom, matching Blender's
  // scroll zoom.
  if (scrollDelta > 0.0f) {
    camera->zoom /= powf(kZoomFactor, scrollDelta);
  } else if (scrollDelta < 0.0f) {
    camera->zoom *= powf(kZoomFactor, -scrollDelta);
  }
  camera->zoom = fmaxf(kMinzoom, camera->zoom);
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
