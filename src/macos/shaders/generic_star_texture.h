#ifndef MACOS_SHADERS_GENERIC_STAR_TEXTURE_H
#define MACOS_SHADERS_GENERIC_STAR_TEXTURE_H

#include "core/space/star.h"
#include "macos/render/shape/vertex.h"
#include <simd/simd.h>

#ifdef __OBJC__
#import <Metal/Metal.h>
#endif

// -----------------------------------------------------------------------------
// Metal Buffer Uniform Structures (Matching generic_star_texture.msl byte layouts)
// -----------------------------------------------------------------------------

// Parameters for star_texture_compute (112 bytes)
typedef struct {
  simd_float4 baseColor;          // Base spectral color (RGBA)
  simd_float4 hotColor;           // Hot granule / flare highlight color (RGBA)
  simd_float4 coolColor;          // Intergranular lane / cooler plasma color (RGBA)
  simd_float4 spotColor;          // Sunspot umbra color (RGBA)
  float time;                     // Elapsed animation time in seconds
  float granulationScale;         // Frequency of convection cells (default: ~28.0)
  float turbulence;               // Plasma flow turbulence intensity (default: ~1.0)
  float spotIntensity;            // Sunspot prominence (0.0 = none, 1.0 = active)
  float limbDarkeningCoeff;       // Limb darkening strength (default: ~0.65)
  float coronaGlow;               // Radiant corona glow intensity (default: ~0.4)
  float rotationSpeed;            // Differential surface rotation rate
  float seed;                     // Procedural variation seed
  simd_uint2 textureSize;         // Output texture width & height
  simd_float2 _pad;               // 16-byte alignment padding
} StarTextureParams;

// Uniforms for star_mesh_vertex & star_mesh_fragment (224 bytes)
typedef struct {
  simd_float4x4 mvpMatrix;        // Model-View-Projection matrix
  simd_float4x4 modelMatrix;      // Model-to-world matrix
  simd_float4 baseColor;          // Base spectral color
  simd_float4 hotColor;           // Hot granule highlight color
  simd_float4 coolColor;          // Intergranular lane color
  simd_float4 spotColor;          // Sunspot umbra color
  PackedFloat3 cameraPos;         // Camera world position (for view angle & limb darkening)
  float time;                     // Simulation time
  float granulationScale;         // Convection cell frequency
  float turbulence;               // Plasma turbulence intensity
  float spotIntensity;            // Sunspot prominence
  float limbDarkening;            // Limb darkening coefficient
} StarMeshUniforms;

// Uniforms for star_billboard_vertex & star_billboard_fragment (240 bytes)
typedef struct {
  simd_float4x4 viewMatrix;       // Camera view matrix
  simd_float4x4 projectionMatrix; // Camera projection matrix
  simd_float4 baseColor;          // Base spectral color
  simd_float4 hotColor;           // Hot highlight color
  simd_float4 coolColor;          // Cool lane color
  simd_float4 spotColor;          // Sunspot umbra color
  float radius;                   // Star radius in render units
  float time;                     // Animation time
  float granulationScale;         // Convection frequency
  float turbulence;               // Turbulence intensity
  float spotIntensity;            // Sunspot intensity
  float coronaGlow;               // Corona intensity
  float limbDarkening;            // Limb darkening coefficient
  float closeFactor;              // Transition factor between point and sphere
  simd_float2 _pad;               // Alignment padding
} StarBillboardUniforms;

// -----------------------------------------------------------------------------
// Spectral Palette Helpers
// -----------------------------------------------------------------------------

// Populate base, hot, cool, and sunspot colors tailored to spectral class
static inline void get_star_spectral_palette(
    StarSpectralType spectral_type,
    simd_float4 *out_base,
    simd_float4 *out_hot,
    simd_float4 *out_cool,
    simd_float4 *out_spot)
{
  switch (spectral_type) {
  case SPECTRAL_CLASS_O:
    if (out_base) *out_base = (simd_float4){0.35f, 0.45f, 1.0f, 1.0f};
    if (out_hot)  *out_hot  = (simd_float4){0.85f, 0.90f, 1.0f, 1.0f};
    if (out_cool) *out_cool = (simd_float4){0.15f, 0.20f, 0.65f, 1.0f};
    if (out_spot) *out_spot = (simd_float4){0.05f, 0.08f, 0.25f, 1.0f};
    break;
  case SPECTRAL_CLASS_B:
    if (out_base) *out_base = (simd_float4){0.55f, 0.65f, 1.0f, 1.0f};
    if (out_hot)  *out_hot  = (simd_float4){0.90f, 0.95f, 1.0f, 1.0f};
    if (out_cool) *out_cool = (simd_float4){0.25f, 0.35f, 0.70f, 1.0f};
    if (out_spot) *out_spot = (simd_float4){0.08f, 0.10f, 0.30f, 1.0f};
    break;
  case SPECTRAL_CLASS_A:
    if (out_base) *out_base = (simd_float4){0.82f, 0.88f, 1.0f, 1.0f};
    if (out_hot)  *out_hot  = (simd_float4){1.00f, 1.00f, 1.0f, 1.0f};
    if (out_cool) *out_cool = (simd_float4){0.45f, 0.50f, 0.75f, 1.0f};
    if (out_spot) *out_spot = (simd_float4){0.15f, 0.18f, 0.35f, 1.0f};
    break;
  case SPECTRAL_CLASS_F:
    if (out_base) *out_base = (simd_float4){1.00f, 0.96f, 0.88f, 1.0f};
    if (out_hot)  *out_hot  = (simd_float4){1.00f, 1.00f, 0.98f, 1.0f};
    if (out_cool) *out_cool = (simd_float4){0.70f, 0.60f, 0.40f, 1.0f};
    if (out_spot) *out_spot = (simd_float4){0.25f, 0.20f, 0.10f, 1.0f};
    break;
  case SPECTRAL_CLASS_G: // e.g. Sun
    if (out_base) *out_base = (simd_float4){1.00f, 0.82f, 0.25f, 1.0f};
    if (out_hot)  *out_hot  = (simd_float4){1.00f, 0.98f, 0.75f, 1.0f};
    if (out_cool) *out_cool = (simd_float4){0.85f, 0.45f, 0.10f, 1.0f};
    if (out_spot) *out_spot = (simd_float4){0.20f, 0.08f, 0.02f, 1.0f};
    break;
  case SPECTRAL_CLASS_K:
    if (out_base) *out_base = (simd_float4){1.00f, 0.58f, 0.20f, 1.0f};
    if (out_hot)  *out_hot  = (simd_float4){1.00f, 0.85f, 0.45f, 1.0f};
    if (out_cool) *out_cool = (simd_float4){0.75f, 0.30f, 0.05f, 1.0f};
    if (out_spot) *out_spot = (simd_float4){0.18f, 0.05f, 0.01f, 1.0f};
    break;
  case SPECTRAL_CLASS_M:
    if (out_base) *out_base = (simd_float4){1.00f, 0.32f, 0.12f, 1.0f};
    if (out_hot)  *out_hot  = (simd_float4){1.00f, 0.60f, 0.25f, 1.0f};
    if (out_cool) *out_cool = (simd_float4){0.55f, 0.12f, 0.04f, 1.0f};
    if (out_spot) *out_spot = (simd_float4){0.12f, 0.02f, 0.01f, 1.0f};
    break;
  default:
    if (out_base) *out_base = (simd_float4){1.0f, 1.0f, 1.0f, 1.0f};
    if (out_hot)  *out_hot  = (simd_float4){1.0f, 1.0f, 1.0f, 1.0f};
    if (out_cool) *out_cool = (simd_float4){0.5f, 0.5f, 0.5f, 1.0f};
    if (out_spot) *out_spot = (simd_float4){0.1f, 0.1f, 0.1f, 1.0f};
    break;
  }
}

#endif // MACOS_SHADERS_GENERIC_STAR_TEXTURE_H
