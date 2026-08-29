#ifndef RENDERER_CAMERA_H
#define RENDERER_CAMERA_H

#include <simd/simd.h>
#include "spatial/spatial.h"

typedef struct
{
	float yaw, pitch, distance;
	simd_float3 center;
} Camera;

void camera_init(Camera *camera);
simd_float3 camera_orbit_position(const Camera *camera);
simd_float4x4 camera_look_at(simd_float3 eye, simd_float3 target, simd_float3 up);
simd_float4x4 camera_perspective(float fovRadians, float aspect, float nearZ, float farZ);
void camera_update_from_input(Camera *camera, float dx, float dy, float scrollDelta);

#endif