#include "core/data/math.h"
#include <criterion/criterion.h>

Test(math_suite, test_scale_matrix) {
  simd_float4x4 mat = make_scale_matrix(2.0f);

  cr_assert_float_eq(mat.columns[0][0], 2.0f, 1e-6);
  cr_assert_float_eq(mat.columns[1][1], 2.0f, 1e-6);
  cr_assert_float_eq(mat.columns[2][2], 2.0f, 1e-6);
  cr_assert_float_eq(mat.columns[3][3], 1.0f, 1e-6);
}

Test(math_suite, test_translation_matrix) {
  simd_float3 t = simd_make_float3(1.0f, 2.0f, 3.0f);
  simd_float4x4 mat = make_translation_matrix(t);

  cr_assert_float_eq(mat.columns[3][0], 1.0f, 1e-6);
  cr_assert_float_eq(mat.columns[3][1], 2.0f, 1e-6);
  cr_assert_float_eq(mat.columns[3][2], 3.0f, 1e-6);
  cr_assert_float_eq(mat.columns[3][3], 1.0f, 1e-6);
}

Test(math_suite, test_label_alpha_distance_fading) {
  float earth_radius = 0.006371f; // render units

  // Very far away: dist = 100.0 > 1000 * 0.006371 (6.371) -> alpha 0
  float alpha_far = calculate_body_label_alpha(earth_radius, 100.0f, false, 12.0f, 1000.0f, 400.0f);
  cr_assert_float_eq(alpha_far, 0.0f, 1e-5, "Far away body should have alpha 0");

  // Zoomed in close: dist = 1.0 < 400 * 0.006371 (2.548) -> alpha 1
  float alpha_close = calculate_body_label_alpha(earth_radius, 1.0f, false, 1.0f, 1000.0f, 400.0f);
  cr_assert_float_eq(alpha_close, 1.0f, 1e-5, "Close body should have alpha 1");

  // Transition zone: dist = 700 * radius -> midway alpha ~0.5
  float dist_mid = earth_radius * 700.0f;
  float alpha_mid = calculate_body_label_alpha(earth_radius, dist_mid, false, dist_mid, 1000.0f, 400.0f);
  cr_assert(alpha_mid > 0.0f && alpha_mid < 1.0f, "Mid-distance body should have fractional alpha");
  cr_assert_float_eq(alpha_mid, 0.5f, 1e-4, "Mid-distance body should have alpha ~0.5");

  // Custom factor: dist = 8.0 ru is > 1000x radius (alpha 0 with 1000.0f),
  // but visible with custom factor 2000.0f
  float alpha_default = calculate_body_label_alpha(earth_radius, 8.0f, false, 1.0f, 1000.0f, 400.0f);
  float alpha_custom = calculate_body_label_alpha(earth_radius, 8.0f, false, 1.0f, 2000.0f, 400.0f);
  cr_assert_float_eq(alpha_default, 0.0f, 1e-5, "At 8.0 ru default factor gives 0");
  cr_assert(alpha_custom > 0.0f, "At 8.0 ru custom factor 2000 keeps label visible");
}

Test(math_suite, test_label_alpha_followed) {
  float moon_radius = 0.001737f;
  // If not followed, at dist=1.0 ru, ratio = 0.001737 -> partial alpha (~0.707)
  float alpha_unfollowed = calculate_body_label_alpha(moon_radius, 1.0f, false, 1.0f, 1000.0f, 400.0f);
  cr_assert(alpha_unfollowed < 1.0f);

  // If followed at zoom=1.0, alpha is 1.0
  float alpha_followed = calculate_body_label_alpha(moon_radius, 1.0f, true, 1.0f, 1000.0f, 400.0f);
  cr_assert_float_eq(alpha_followed, 1.0f, 1e-5, "Followed body at close zoom should have alpha 1");
}

Test(math_suite, test_project_sphere_top) {
  simd_float4x4 view = {0};
  view.columns[0] = simd_make_float4(1, 0, 0, 0);
  view.columns[1] = simd_make_float4(0, 1, 0, 0);
  view.columns[2] = simd_make_float4(0, 0, 1, 0);
  view.columns[3] = simd_make_float4(0, 0, 0, 1);

  // Simple perspective projection: yScale = 1.0, xScale = 1.0
  simd_float4x4 proj = {0};
  proj.columns[0] = simd_make_float4(1.0f, 0, 0, 0);
  proj.columns[1] = simd_make_float4(0, 1.0f, 0, 0);
  proj.columns[2] = simd_make_float4(0, 0, -1.0f, -1.0f);
  proj.columns[3] = simd_make_float4(0, 0, -0.02f, 0);

  simd_float3 body_pos = simd_make_float3(0.0f, 0.0f, -10.0f);
  float radius = 2.0f;
  float screen_x = 0.0f, screen_y_top = 0.0f, depth = 0.0f;

  bool ok = project_sphere_top(body_pos, radius, view, proj, 0.01f, 800.0f, 600.0f,
                               &screen_x, &screen_y_top, &depth);
  cr_assert(ok, "Sphere in front of camera should project successfully");
  cr_assert_float_eq(screen_x, 400.0f, 1e-4, "Screen X should be centered at 400");
  cr_assert(screen_y_top > 300.0f, "Screen Y top should be above center (300)");
  cr_assert_float_eq(depth, 10.0f, 1e-4, "Depth should be 10.0");

  // Sphere behind camera
  simd_float3 behind_pos = simd_make_float3(0.0f, 0.0f, 10.0f);
  bool behind_ok = project_sphere_top(behind_pos, radius, view, proj, 0.01f, 800.0f, 600.0f,
                                      &screen_x, &screen_y_top, &depth);
  cr_assert_not(behind_ok, "Sphere behind camera should be rejected");
}
