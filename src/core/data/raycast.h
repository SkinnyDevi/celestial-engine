#ifndef CORE_DATA_RAYCAST_H
#define CORE_DATA_RAYCAST_H

#include <stdbool.h>
#include <simd/simd.h>

simd_float3 raycast_screen_to_world_dir(float screen_x, float screen_y, float view_width, float view_height, simd_float4x4 view_proj_inverse, simd_float3 camera_pos);
bool raycast_intersects_sphere(simd_float3 ray_origin, simd_float3 ray_dir, simd_float3 sphere_center, float sphere_radius, float *out_distance);

#endif