#include "raycast.h"
#include <math.h>

simd_float3 raycast_screen_to_world_dir(float screen_x, float screen_y,
                                        float view_width, float view_height,
                                        simd_float4x4 view_inverse,
                                        float fov_radians) {
  float ndc_x = (2.0f * screen_x) / view_width - 1.0f;
  float ndc_y = (2.0f * screen_y) / view_height - 1.0f;

  float aspect = view_width / (view_height > 0.0f ? view_height : 1.0f);
  float tan_half_fov = tanf(fov_radians * 0.5f);

  float view_x = ndc_x * aspect * tan_half_fov;
  float view_y = ndc_y * tan_half_fov;
  float view_z = -1.0f;

  simd_float3 ray_world;
  ray_world.x = view_inverse.columns[0].x * view_x +
                view_inverse.columns[1].x * view_y +
                view_inverse.columns[2].x * view_z;
  ray_world.y = view_inverse.columns[0].y * view_x +
                view_inverse.columns[1].y * view_y +
                view_inverse.columns[2].y * view_z;
  ray_world.z = view_inverse.columns[0].z * view_x +
                view_inverse.columns[1].z * view_y +
                view_inverse.columns[2].z * view_z;

  return simd_normalize(ray_world);
}

bool raycast_intersects_sphere(simd_float3 ray_origin, simd_float3 ray_dir,
                               simd_float3 sphere_center, float sphere_radius,
                               float *out_distance) {
  double ox = ray_origin.x, oy = ray_origin.y, oz = ray_origin.z;
  double dx = ray_dir.x, dy = ray_dir.y, dz = ray_dir.z;
  double cx = sphere_center.x, cy = sphere_center.y, cz = sphere_center.z;

  double mx = ox - cx;
  double my = oy - cy;
  double mz = oz - cz;

  double b = mx * dx + my * dy + mz * dz;
  double c = mx * mx + my * my + mz * mz - (double)sphere_radius * (double)sphere_radius;

  if (c > 0.0 && b > 0.0)
    return false;

  double discr = b * b - c;
  if (discr < 0.0)
    return false;

  double t = -b - sqrt(discr);
  if (t < 0.0)
    t = 0.0;

  if (out_distance)
    *out_distance = (float)t;

  return true;
}