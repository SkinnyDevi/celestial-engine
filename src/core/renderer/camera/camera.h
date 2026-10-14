#ifndef RENDERER_CAMERA_H
#define RENDERER_CAMERA_H

#include <simd/simd.h>
#include <stdbool.h>

#define CAMERA_FAR_CLIPPING_PLANE 1e23f
#define CAMERA_NEAR_CLIPPING_PLANE 0.01f

typedef struct {
  float azimuth, elevation, zoom;
  simd_double3 center;

  bool is_transitioning;
  simd_double3 start_center;
  simd_double3 target_center;
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
void camera_focus_on(Camera *camera, simd_double3 target, float zoom);
void camera_set_position(Camera *camera, simd_double3 position);

void camera_start_transition_to(Camera *camera, simd_double3 target, float zoom);
void camera_update_transition(Camera *camera, float dt);
void camera_get_clipping_planes(const Camera *camera, float *near_out,
                                float *far_out);

typedef struct {
  simd_float4 planes[5]; // 0: Left, 1: Right, 2: Bottom, 3: Top, 4: Near
} CameraFrustum;

CameraFrustum camera_extract_frustum(const Camera *camera, float aspect,
                                     float fovRadians);
bool camera_frustum_test_sphere(const CameraFrustum *frustum,
                                simd_float3 center_rel, float radius);

#endif