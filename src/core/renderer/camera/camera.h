#ifndef RENDERER_CAMERA_H
#define RENDERER_CAMERA_H

#include <simd/simd.h>
#include <stdbool.h>

#define CAMERA_FAR_CLIPPING_PLANE 100000.0f
#define CAMERA_NEAR_CLIPPING_PLANE 0.01f

typedef struct {
  float azimuth, elevation, zoom;
  simd_float3 center;

  bool is_transitioning;
  simd_float3 start_center;
  simd_float3 target_center;
  float start_zoom;
  float target_zoom;
  float transition_progress;
} Camera;

void camera_init(Camera *camera);
simd_float3 camera_orbit_position(const Camera *camera);
simd_float4x4 camera_view_matrix(const Camera *camera);
simd_float4x4 camera_perspective(float fovRadians, float aspect, float nearZ,
                                 float farZ);
void camera_orbit_from_input(Camera *camera, float dx, float dy);
void camera_pan_from_input(Camera *camera, float dx, float dy);
void camera_zoom_from_input(Camera *camera, float scrollDelta);
void camera_focus_on(Camera *camera, simd_float3 target, float zoom);
void camera_set_position(Camera *camera, simd_float3 position);

void camera_start_transition_to(Camera *camera, simd_float3 target, float zoom);
void camera_update_transition(Camera *camera, float dt);

#endif