#ifndef MACOS_DISPLACED_MESH_H
#define MACOS_DISPLACED_MESH_H

#include <simd/simd.h>

// GPU vertex position — 3 tightly packed floats (12 bytes) matching
// Metal's packed_float3 stride. Cannot use simd_float3 here because
// it is 16-byte aligned and would cause vertex buffer misalignment.
typedef struct {
  float x, y, z;
} PackedFloat3;

typedef struct {
  PackedFloat3 position;
} Vertex;

// Must match the Metal shader 'Uniforms' struct layout exactly
typedef struct {
  simd_float4x4 mvpMatrix;
  simd_float4 gridColor;
} DisplacedMeshUniforms;

Vertex *generate_grid_vertices(int grid_size, float spacing, int num_vertices);

#endif