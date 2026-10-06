#include "core/data/raycast.h"
#include <criterion/criterion.h>

Test(raycast_suite, test_ray_intersects_sphere) {
  simd_float3 ray_origin = simd_make_float3(0, 0, 0);
  simd_float3 ray_dir = simd_make_float3(0, 0, 1); // Pointing forward in Z
  simd_float3 sphere_center = simd_make_float3(0, 0, 5);
  float radius = 1.0f;
  float dist = 0.0f;

  bool hit = raycast_intersects_sphere(ray_origin, ray_dir, sphere_center,
                                       radius, &dist);
  cr_assert(hit, "Ray should intersect the sphere");
  cr_assert_float_eq(dist, 4.0f, 1e-5,
                     "Distance should be 4.0 (5.0 - 1.0 radius)");
}

Test(raycast_suite, test_ray_misses_sphere) {
  simd_float3 ray_origin = simd_make_float3(0, 0, 0);
  simd_float3 ray_dir = simd_make_float3(0, 1, 0); // Pointing UP in Y
  simd_float3 sphere_center = simd_make_float3(0, 0, 5);
  float radius = 1.0f;
  float dist = 0.0f;

  bool hit = raycast_intersects_sphere(ray_origin, ray_dir, sphere_center,
                                       radius, &dist);
  cr_assert_not(hit, "Ray should miss the sphere");
}

Test(raycast_suite, test_raycast_screen_to_world_dir) {
  float view_width = 800.0f;
  float view_height = 600.0f;

  // Create I-matrix for the view (camera at origin, looking down -Z)
  simd_float4x4 view_inverse = {0};
  view_inverse.columns[0] = simd_make_float4(1, 0, 0, 0);
  view_inverse.columns[1] = simd_make_float4(0, 1, 0, 0);
  view_inverse.columns[2] = simd_make_float4(0, 0, 1, 0);
  view_inverse.columns[3] = simd_make_float4(0, 0, 0, 1);

  float fov_radians =
      90.0f * (float)M_PI / 180.0f; // 90 degree FOV for easy math

  // Center of the screen
  simd_float3 dir_center = raycast_screen_to_world_dir(
      400.0f, 300.0f, view_width, view_height, view_inverse, fov_radians);

  // At center, the ray should point straight forward along -Z
  cr_assert_float_eq(dir_center.x, 0.0f, 1e-5);
  cr_assert_float_eq(dir_center.y, 0.0f, 1e-5);
  cr_assert_float_eq(dir_center.z, -1.0f, 1e-5);
}
