#ifndef CORE_DATA_MATH_H
#define CORE_DATA_MATH_H

#include <simd/simd.h>

simd_float4x4 make_scale_matrix(float s);
simd_float4x4 make_translation_matrix(simd_float3 t);

#endif // CORE_DATA_MATH_H