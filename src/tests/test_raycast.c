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
