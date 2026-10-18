#include "core/data/math.h"
#include <string.h>

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

float calculate_body_label_alpha(float base_radius_ru, float distance_ru,
                                 bool is_followed, float camera_zoom,
                                 float disappear_dist_factor,
                                 float full_opacity_dist_factor) {
  if (distance_ru <= 1e-6f || base_radius_ru <= 1e-9f)
    return 0.0f;

  if (disappear_dist_factor <= 0.0f)
    disappear_dist_factor = 1000.0f;

  if (full_opacity_dist_factor <= 0.0f ||
      full_opacity_dist_factor >= disappear_dist_factor)
    full_opacity_dist_factor = disappear_dist_factor * 0.4f;

  float max_dist = disappear_dist_factor * base_radius_ru;
  float full_dist = full_opacity_dist_factor * base_radius_ru;

  float alpha = 0.0f;
  if (distance_ru <= full_dist)
    alpha = 1.0f;
  else if (distance_ru < max_dist)
    alpha = (max_dist - distance_ru) / (max_dist - full_dist);

  if (is_followed) {
    float max_follow_zoom = 5.0f * (base_radius_ru > 0.05f ? 10.0f : 1.0f);
    if (camera_zoom <= max_follow_zoom) {
      float start_fade = 2.0f * (base_radius_ru > 0.05f ? 10.0f : 1.0f);
      float follow_alpha = 1.0f;
      if (camera_zoom > start_fade)
        follow_alpha =
            1.0f - (camera_zoom - start_fade) / (max_follow_zoom - start_fade);

      if (follow_alpha > alpha)
        alpha = follow_alpha;
    }
  }

  return alpha;
}

bool project_sphere_top(simd_float3 body_pos, float sphere_radius,
                        simd_float4x4 view, simd_float4x4 projection,
                        float near_plane, float view_width, float view_height,
                        float *out_screen_x, float *out_screen_y_top,
                        float *out_depth) {
  simd_float4 view_pos = simd_mul(
      view, simd_make_float4(body_pos.x, body_pos.y, body_pos.z, 1.0f));

  if (view_pos.z >= -near_plane)
    return false;

  simd_float4 view_pos_top = view_pos;
  view_pos_top.y += sphere_radius;

  simd_float4 clip_center = simd_mul(projection, view_pos);
  simd_float4 clip_top = simd_mul(projection, view_pos_top);

  if (clip_center.w <= 0.0001f)
    return false;

  float ndc_center_x = clip_center.x / clip_center.w;
  float ndc_center_y = clip_center.y / clip_center.w;
  float ndc_top_y = clip_top.y / clip_top.w;

  if (ndc_center_x < -1.4f || ndc_center_x > 1.4f || ndc_top_y < -1.4f ||
      ndc_center_y > 1.4f)
    return false;

  if (out_screen_x)
    *out_screen_x = (ndc_center_x * 0.5f + 0.5f) * view_width;

  if (out_screen_y_top)
    *out_screen_y_top = (ndc_top_y * 0.5f + 0.5f) * view_height;

  if (out_depth)
    *out_depth = -view_pos.z;

  return true;
}

static uint32_t radix_counts[65536];
static uint32_t radix_offsets[65536];

void radix_sort_descending(StarSortItem *src, StarSortItem *dst, size_t n) {
  if (n <= 1)
    return;

  // Pass 1: lower 16 bits (read src, write dst)
  memset(radix_counts, 0, sizeof(radix_counts));
  for (size_t i = 0; i < n; i++) {
    uint32_t u = *(uint32_t *)&src[i].dist_sq;
    uint16_t b = (~u) & 0xFFFF;
    radix_counts[b]++;
  }

  radix_offsets[0] = 0;
  for (int i = 1; i < 65536; i++)
    radix_offsets[i] = radix_offsets[i - 1] + radix_counts[i - 1];

  for (size_t i = 0; i < n; i++) {
    uint32_t u = *(uint32_t *)&src[i].dist_sq;
    uint16_t b = (~u) & 0xFFFF;
    dst[radix_offsets[b]++] = src[i];
  }

  // Pass 2: upper 16 bits (read dst, write back to src)
  memset(radix_counts, 0, sizeof(radix_counts));
  for (size_t i = 0; i < n; i++) {
    uint32_t u = *(uint32_t *)&dst[i].dist_sq;
    uint16_t b = ((~u) >> 16) & 0xFFFF;
    radix_counts[b]++;
  }

  radix_offsets[0] = 0;
  for (int i = 1; i < 65536; i++)
    radix_offsets[i] = radix_offsets[i - 1] + radix_counts[i - 1];

  for (size_t i = 0; i < n; i++) {
    uint32_t u = *(uint32_t *)&dst[i].dist_sq;
    uint16_t b = ((~u) >> 16) & 0xFFFF;
    src[radix_offsets[b]++] = dst[i];
  }
}