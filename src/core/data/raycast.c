#include "raycast.h"
#include <math.h>

simd_float3 raycast_screen_to_world_dir(float screen_x, float screen_y,
                                        float view_width, float view_height,
                                        simd_float4x4 view_proj_inverse,
                                        simd_float3 camera_pos) {
  float ndc_x = (2.0f * screen_x) / view_width - 1.0f;
  float ndc_y = (2.0f * screen_y) / view_height - 1.0f;

  simd_float4 ndc_far = simd_make_float4(ndc_x, ndc_y, 1.0f, 1.0f);
  simd_float4 world_far = simd_mul(view_proj_inverse, ndc_far);

  if (world_far.w != 0.0f) {
    world_far /= world_far.w;
  }

  simd_float3 far_pt = simd_make_float3(world_far.x, world_far.y, world_far.z);
  return simd_normalize(far_pt - camera_pos);
}

bool raycast_intersects_sphere(simd_float3 ray_origin, simd_float3 ray_dir,
                               simd_float3 sphere_center, float sphere_radius,
                               float *out_distance) {
  simd_float3 m = ray_origin - sphere_center;
  float b = simd_dot(m, ray_dir);
  float c = simd_dot(m, m) - sphere_radius * sphere_radius;

  if (c > 0.0f && b > 0.0f)
    return false;

  float discr = b * b - c;
  if (discr < 0.0f)
    return false;

  float t = -b - sqrtf(discr);
  if (t < 0.0f)
    t = 0.0f;

  if (out_distance)
    *out_distance = t;

  return true;
}