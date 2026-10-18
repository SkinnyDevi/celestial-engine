#ifndef CORE_DATA_MATH_H
#define CORE_DATA_MATH_H

#include <simd/simd.h>
#include <stdbool.h>

simd_float4x4 make_scale_matrix(float s);
simd_float4x4 make_translation_matrix(simd_float3 t);

float calculate_body_label_alpha(float base_radius_ru, float distance_ru,
                                 bool is_followed, float camera_zoom,
                                 float disappear_dist_factor,
                                 float full_opacity_dist_factor);

bool project_sphere_top(simd_float3 body_pos, float sphere_radius,
                        simd_float4x4 view, simd_float4x4 projection,
                        float near_plane, float view_width, float view_height,
                        float *out_screen_x, float *out_screen_y_top,
                        float *out_depth);

typedef struct {
  uint32_t index;
  float dist_sq;
} StarSortItem;

void radix_sort_descending(StarSortItem *src, StarSortItem *dst, size_t n);

#endif // CORE_DATA_MATH_H