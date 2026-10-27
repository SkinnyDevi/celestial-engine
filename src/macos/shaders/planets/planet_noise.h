#ifndef PLANETS_PLANET_NOISE_H
#define PLANETS_PLANET_NOISE_H

#ifdef __METAL_VERSION__
#include <metal_stdlib>
using namespace metal;

// Fast 3D pseudo-random hash
inline float3 planet_hash33(float3 p) {
  p = fract(p * float3(0.1031f, 0.1030f, 0.0973f));
  p += dot(p, p.yxz + 33.33f);

  return fract((p.xxy + p.yxx) * p.zyx);
}

// 3D Gradient Vector
inline float3 planet_gradient(float3 p) {
  float3 h = planet_hash33(p);
  float z = 1.0f - 2.0f * h.x;
  float r = sqrt(max(0.0f, 1.0f - z * z));
  float phi = 6.28318530718f * h.y;

  return float3(r * cos(phi), r * sin(phi), z);
}

// 3D Gradient Noise with quintic Hermite interpolation (C2 continuous)
inline float planet_noise3d(float3 p) {
  float3 i = floor(p);
  float3 f = fract(p);
  float3 u = f * f * f * (f * (f * 6.0f - 15.0f) + 10.0f);

  float n000 = dot(planet_gradient(i + float3(0.0f, 0.0f, 0.0f)),
                   f - float3(0.0f, 0.0f, 0.0f));
  float n100 = dot(planet_gradient(i + float3(1.0f, 0.0f, 0.0f)),
                   f - float3(1.0f, 0.0f, 0.0f));
  float n010 = dot(planet_gradient(i + float3(0.0f, 1.0f, 0.0f)),
                   f - float3(0.0f, 1.0f, 0.0f));
  float n110 = dot(planet_gradient(i + float3(1.0f, 1.0f, 0.0f)),
                   f - float3(1.0f, 1.0f, 0.0f));
  float n001 = dot(planet_gradient(i + float3(0.0f, 0.0f, 1.0f)),
                   f - float3(0.0f, 0.0f, 1.0f));
  float n101 = dot(planet_gradient(i + float3(1.0f, 0.0f, 1.0f)),
                   f - float3(1.0f, 0.0f, 1.0f));
  float n011 = dot(planet_gradient(i + float3(0.0f, 1.0f, 1.0f)),
                   f - float3(0.0f, 1.0f, 1.0f));
  float n111 = dot(planet_gradient(i + float3(1.0f, 1.0f, 1.0f)),
                   f - float3(1.0f, 1.0f, 1.0f));

  return mix(mix(mix(n000, n100, u.x), mix(n010, n110, u.x), u.y),
             mix(mix(n001, n101, u.x), mix(n011, n111, u.x), u.y), u.z);
}

// Multi-octave Fractional Brownian Motion (FBM)
inline float planet_fbm3d(float3 p, int octaves) {
  float v = 0.0f;
  float a = 0.5f;
  float3 shift = float3(100.0f);
  for (int i = 0; i < octaves; ++i) {
    v += a * planet_noise3d(p);
    p = p * 2.05f + shift;
    a *= 0.5f;
  }

  return v;
}

// 3D Voronoi / Cellular Noise (Worley Noise)
// Returns float2(d1, d2) for craters, tectonic cracks, and polygonal ice plains
inline float2 planet_voronoi3d(float3 p) {
  float3 i = floor(p);
  float3 f = fract(p);

  float d1 = 8.0f;
  float d2 = 8.0f;

  for (int z = -1; z <= 1; z++) {
    for (int y = -1; y <= 1; y++) {
      for (int x = -1; x <= 1; x++) {
        float3 neighbor = float3(float(x), float(y), float(z));
        float3 point = planet_hash33(i + neighbor);
        float3 diff = neighbor + point - f;
        float dist = length(diff);
        if (dist < d1) {
          d2 = d1;
          d1 = dist;
        } else if (dist < d2) {
          d2 = dist;
        }
      }
    }
  }

  return float2(d1, d2);
}

// Rotation around Y axis (planetary polar axis)
inline float3 planet_rotate_y(float3 v, float angle) {
  float s = sin(angle);
  float c = cos(angle);

  return float3(c * v.x + s * v.z, v.y, -s * v.x + c * v.z);
}
#endif

#endif // PLANETS_PLANET_NOISE_H
