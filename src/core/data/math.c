#include "core/data/math.h"

simd_float4x4 make_scale_matrix(float s) {
  simd_float4x4 m = {0};
  m.columns[0] = simd_make_float4(s, 0, 0, 0);
  m.columns[1] = simd_make_float4(0, s, 0, 0);
  m.columns[2] = simd_make_float4(0, 0, s, 0);
  m.columns[3] = simd_make_float4(0, 0, 0, 1);
  return m;
}

simd_float4x4 make_translation_matrix(simd_float3 t) {
  simd_float4x4 m = {0};
  m.columns[0] = simd_make_float4(1, 0, 0, 0);
  m.columns[1] = simd_make_float4(0, 1, 0, 0);
  m.columns[2] = simd_make_float4(0, 0, 1, 0);
  m.columns[3] = simd_make_float4(t.x, t.y, t.z, 1);
  return m;
}