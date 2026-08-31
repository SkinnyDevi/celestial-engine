#ifndef RENDERER_CAMERA_H
#define RENDERER_CAMERA_H

#include "spatial/spatial.h"
#include <simd/simd.h>

typedef struct {
  float azimuth, elevation, zoom;
  simd_float3 center;
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

#endif