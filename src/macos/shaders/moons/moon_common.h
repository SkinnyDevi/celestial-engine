#ifndef MOONS_MOON_COMMON_H
#define MOONS_MOON_COMMON_H

#ifdef __METAL_VERSION__
#include <metal_stdlib>
using namespace metal;

struct MoonUniforms {
  float4x4 mvpMatrix;    // Model-View-Projection matrix (64 bytes, offset 0)
  float4x4 modelMatrix;  // Model-to-world matrix (64 bytes, offset 64)
  float4 baseColor;      // Primary palette color (16 bytes, offset 128)
  float4 secondaryColor; // Secondary/rift/maria color (16 bytes, offset 144)
  float4 accentColor;    // Accent/ejecta/lava color (16 bytes, offset 160)
  packed_float3
      cameraPos; // Camera position in world space (12 bytes, offset 176)
  float time;    // Simulation time in seconds (4 bytes, offset 188)
  packed_float3
      lightDirection; // Normalized vector to host star (12 bytes, offset 192)
  float
      lightIntensity; // Light intensity / star luminosity (4 bytes, offset 204)
  float surfaceRoughness; // Surface roughness (4 bytes, offset 208)
  float albedo;           // Surface albedo / reflectance (4 bytes, offset 212)
  float seed;             // Unique procedural seed (4 bytes, offset 216)
  float rotationSpeed;    // Rotation rate (4 bytes, offset 220)
  packed_float3 hostPlanetPos; // Position of host planet (12 bytes, offset 224)
  float planetshineIntensity;  // Secondary illumination from host planet (4
                               // bytes, offset 236)
  float4 hostPlanetColor; // Color reflected from host planet (16 bytes, offset
                          // 240)
};

struct MoonVertexIn {
  packed_float3 position;
};

struct MoonVertexOut {
  float4 position [[position]];
  float3 worldPos;
  float3 normal;   // in world space
  float3 localPos; // in local space (unit sphere)
  float2 uv;
};

inline MoonVertexOut moon_vertex_impl(const device MoonVertexIn *vertices,
                                      constant MoonUniforms &uniforms,
                                      uint vid) {
  MoonVertexOut out;
  float3 localPos = float3(vertices[vid].position);
  float4 worldPos = uniforms.modelMatrix * float4(localPos, 1.0f);
  out.position = uniforms.mvpMatrix * float4(localPos, 1.0f);
  out.worldPos = worldPos.xyz;
  out.normal = normalize((uniforms.modelMatrix * float4(localPos, 0.0f)).xyz);
  out.localPos = normalize(localPos);

  float u = 0.5f + atan2(localPos.z, localPos.x) / (2.0f * 3.14159265359f);
  float v = 0.5f - asin(clamp(localPos.y, -1.0f, 1.0f)) / 3.14159265359f;
  out.uv = float2(u, v);
  return out;
}

#else // C / Objective-C Host Headers

#include "core/space/moon.h"
#include "macos/render/shape/vertex.h"
#include <simd/simd.h>

typedef struct {
  simd_float4x4 mvpMatrix; // Model-View-Projection matrix (64 bytes, offset 0)
  simd_float4x4 modelMatrix; // Model-to-world matrix (64 bytes, offset 64)
  simd_float4 baseColor;     // Primary palette color (16 bytes, offset 128)
  simd_float4
      secondaryColor;      // Secondary/rift/maria color (16 bytes, offset 144)
  simd_float4 accentColor; // Accent/ejecta/lava color (16 bytes, offset 160)
  PackedFloat3
      cameraPos; // Camera position in world space (12 bytes, offset 176)
  float time;    // Simulation time in seconds (4 bytes, offset 188)
  PackedFloat3
      lightDirection; // Normalized vector to host star (12 bytes, offset 192)
  float
      lightIntensity; // Light intensity / star luminosity (4 bytes, offset 204)
  float surfaceRoughness; // Surface roughness (4 bytes, offset 208)
  float albedo;           // Surface albedo / reflectance (4 bytes, offset 212)
  float seed;             // Unique procedural seed (4 bytes, offset 216)
  float rotationSpeed;    // Rotation rate (4 bytes, offset 220)
  PackedFloat3 hostPlanetPos;  // Position of host planet (12 bytes, offset 224)
  float planetshineIntensity;  // Secondary illumination from host planet (4
                               // bytes, offset 236)
  simd_float4 hostPlanetColor; // Color reflected from host planet (16 bytes,
                               // offset 240)
} MoonUniforms;

static inline void get_moon_palette(MoonClass moon_class, simd_float4 *out_base,
                                    simd_float4 *out_secondary,
                                    simd_float4 *out_accent,
                                    float *out_roughness, float *out_albedo) {
  switch (moon_class) {
  case MOON_CLASS_ROCKY:
    if (out_base)
      *out_base = (simd_float4){0.68f, 0.67f, 0.65f, 1.0f};
    if (out_secondary)
      *out_secondary = (simd_float4){0.22f, 0.22f, 0.24f, 1.0f};
    if (out_accent)
      *out_accent = (simd_float4){0.92f, 0.90f, 0.85f, 1.0f};
    if (out_roughness)
      *out_roughness = 0.92f;
    if (out_albedo)
      *out_albedo = 0.12f;
    break;
  case MOON_CLASS_ICY:
    if (out_base)
      *out_base = (simd_float4){0.88f, 0.92f, 0.98f, 1.0f};
    if (out_secondary)
      *out_secondary = (simd_float4){0.62f, 0.32f, 0.18f, 1.0f};
    if (out_accent)
      *out_accent = (simd_float4){0.45f, 0.75f, 0.95f, 1.0f};
    if (out_roughness)
      *out_roughness = 0.35f;
    if (out_albedo)
      *out_albedo = 0.68f;
    break;
  case MOON_CLASS_CAPTURED:
    if (out_base)
      *out_base = (simd_float4){0.32f, 0.30f, 0.28f, 1.0f};
    if (out_secondary)
      *out_secondary = (simd_float4){0.18f, 0.16f, 0.15f, 1.0f};
    if (out_accent)
      *out_accent = (simd_float4){0.48f, 0.44f, 0.40f, 1.0f};
    if (out_roughness)
      *out_roughness = 0.98f;
    if (out_albedo)
      *out_albedo = 0.06f;
    break;
  case MOON_CLASS_VOLCANIC:
    if (out_base)
      *out_base = (simd_float4){0.92f, 0.85f, 0.35f, 1.0f};
    if (out_secondary)
      *out_secondary = (simd_float4){0.78f, 0.42f, 0.10f, 1.0f};
    if (out_accent)
      *out_accent = (simd_float4){0.98f, 0.25f, 0.02f, 1.0f};
    if (out_roughness)
      *out_roughness = 0.65f;
    if (out_albedo)
      *out_albedo = 0.62f;
    break;
  default:
    if (out_base)
      *out_base = (simd_float4){0.6f, 0.6f, 0.6f, 1.0f};
    if (out_secondary)
      *out_secondary = (simd_float4){0.3f, 0.3f, 0.3f, 1.0f};
    if (out_accent)
      *out_accent = (simd_float4){0.8f, 0.8f, 0.8f, 1.0f};
    if (out_roughness)
      *out_roughness = 0.8f;
    if (out_albedo)
      *out_albedo = 0.2f;
    break;
  }
}

#endif // __METAL_VERSION__

#endif // MOONS_MOON_COMMON_H
