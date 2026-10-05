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
