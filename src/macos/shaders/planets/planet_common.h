#ifndef PLANETS_PLANET_COMMON_H
#define PLANETS_PLANET_COMMON_H

#ifdef __METAL_VERSION__
#include <metal_stdlib>
using namespace metal;

struct PlanetUniforms {
  float4x4 mvpMatrix;     // Model-View-Projection matrix (64 bytes, offset 0)
  float4x4 modelMatrix;   // Model-to-world matrix (64 bytes, offset 64)
  float4 baseColor;       // Primary palette color (16 bytes, offset 128)
  float4 secondaryColor;  // Secondary/accent color (16 bytes, offset 144)
  float4 atmosphereColor; // Atmospheric limb color (16 bytes, offset 160)
  packed_float3
      cameraPos; // Camera position in world space (12 bytes, offset 176)
  float time;    // Simulation time in seconds (4 bytes, offset 188)
  packed_float3
      lightDirection; // Normalized vector to host star (12 bytes, offset 192)
  float
      lightIntensity; // Light intensity / star luminosity (4 bytes, offset 204)
  float surfaceRoughness;  // Terrain roughness (4 bytes, offset 208)
  float atmosphereDensity; // Atmospheric haze strength (4 bytes, offset 212)
  float seed;              // Unique procedural seed (4 bytes, offset 216)
  float rotationSpeed;     // Planetary rotation rate (4 bytes, offset 220)
};

struct PlanetVertexIn {
  packed_float3 position;
};

struct PlanetVertexOut {
  float4 position [[position]];
  float3 worldPos;
  float3 normal;   // in world space
  float3 localPos; // in local space (unit sphere)
  float2 uv;
};

inline PlanetVertexOut planet_vertex_impl(const device PlanetVertexIn *vertices,
                                          constant PlanetUniforms &uniforms,
                                          uint vid) {
  PlanetVertexOut out;
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

#include "core/space/planet.h"
#include "macos/render/shape/vertex.h"

#include <simd/simd.h>

typedef struct {
  simd_float4x4 mvpMatrix; // Model-View-Projection matrix (64 bytes, offset 0)
  simd_float4x4 modelMatrix;   // Model-to-world matrix (64 bytes, offset 64)
  simd_float4 baseColor;       // Primary palette color (16 bytes, offset 128)
  simd_float4 secondaryColor;  // Secondary/accent color (16 bytes, offset 144)
  simd_float4 atmosphereColor; // Atmospheric limb color (16 bytes, offset 160)
  PackedFloat3
      cameraPos; // Camera position in world space (12 bytes, offset 176)
  float time;    // Simulation time in seconds (4 bytes, offset 188)
  PackedFloat3
      lightDirection; // Normalized vector to host star (12 bytes, offset 192)
  float
      lightIntensity; // Light intensity / star luminosity (4 bytes, offset 204)
  float surfaceRoughness;  // Terrain roughness (4 bytes, offset 208)
  float atmosphereDensity; // Atmospheric haze strength (4 bytes, offset 212)
  float seed;              // Unique procedural seed (4 bytes, offset 216)
  float rotationSpeed;     // Planetary rotation rate (4 bytes, offset 220)
} PlanetUniforms;

static inline void
get_planet_palette(PlanetClass planet_class, AtmosphereType atmos_type,
                   simd_float4 *out_base, simd_float4 *out_secondary,
                   simd_float4 *out_atmos, float *out_roughness,
                   float *out_atmos_density) {
  switch (planet_class) {
  case PLANET_CLASS_TERRESTRIAL:
    if (out_base)
      *out_base = (simd_float4){0.05f, 0.22f, 0.55f, 1.0f}; // Ocean blue
    if (out_secondary)
      *out_secondary = (simd_float4){0.30f, 0.55f, 0.25f, 1.0f}; // Land green
    if (out_atmos)
      *out_atmos = (simd_float4){0.35f, 0.65f, 1.0f, 1.0f}; // Azure atmosphere
    if (out_roughness)
      *out_roughness = 0.5f;
    if (out_atmos_density) {
      if (atmos_type == ATMOSPHERE_NONE)
        *out_atmos_density = 0.0f;
      else if (atmos_type == ATMOSPHERE_THIN)
        *out_atmos_density = 0.35f;
      else if (atmos_type == ATMOSPHERE_DENSE)
        *out_atmos_density = 1.6f;
      else
        *out_atmos_density = 0.85f;
    }
    break;
  case PLANET_CLASS_GAS_GIANT:
    if (out_base)
      *out_base = (simd_float4){0.85f, 0.72f, 0.52f, 1.0f};
    if (out_secondary)
      *out_secondary = (simd_float4){0.72f, 0.40f, 0.22f, 1.0f};
    if (out_atmos)
      *out_atmos = (simd_float4){0.95f, 0.85f, 0.70f, 0.5f};
    if (out_roughness)
      *out_roughness = 0.8f;
    if (out_atmos_density)
      *out_atmos_density = 1.0f;
    break;
  case PLANET_CLASS_ICE_GIANT:
    if (out_base)
      *out_base = (simd_float4){0.22f, 0.55f, 0.95f, 1.0f};
    if (out_secondary)
      *out_secondary = (simd_float4){0.45f, 0.85f, 0.92f, 1.0f};
    if (out_atmos)
      *out_atmos = (simd_float4){0.40f, 0.80f, 1.00f, 0.8f};
    if (out_roughness)
      *out_roughness = 0.6f;
    if (out_atmos_density)
      *out_atmos_density = 1.2f;
    break;
  case PLANET_CLASS_DWARF:
    if (out_base)
      *out_base = (simd_float4){0.55f, 0.52f, 0.48f, 1.0f};
    if (out_secondary)
      *out_secondary = (simd_float4){0.78f, 0.72f, 0.65f, 1.0f};
    if (out_atmos)
      *out_atmos = (simd_float4){0.60f, 0.70f, 0.80f, 0.1f};
    if (out_roughness)
      *out_roughness = 0.95f;
    if (out_atmos_density)
      *out_atmos_density = 0.05f;
    break;
  case PLANET_CLASS_ROGUE:
    if (out_base)
      *out_base = (simd_float4){0.08f, 0.06f, 0.10f, 1.0f};
    if (out_secondary)
      *out_secondary = (simd_float4){0.95f, 0.35f, 0.05f, 1.0f};
    if (out_atmos)
      *out_atmos = (simd_float4){0.20f, 0.08f, 0.35f, 0.3f};
    if (out_roughness)
      *out_roughness = 0.7f;
    if (out_atmos_density)
      *out_atmos_density = 0.2f;
    break;
  default:
    if (out_base)
      *out_base = (simd_float4){0.5f, 0.5f, 0.5f, 1.0f};
    if (out_secondary)
      *out_secondary = (simd_float4){0.3f, 0.3f, 0.3f, 1.0f};
    if (out_atmos)
      *out_atmos = (simd_float4){0.5f, 0.5f, 1.0f, 0.5f};
    if (out_roughness)
      *out_roughness = 0.5f;
    if (out_atmos_density)
      *out_atmos_density = 0.5f;
    break;
  }
}

#endif // __METAL_VERSION__

#endif // PLANETS_PLANET_COMMON_H
