#ifndef SPATIAL_VEC3_H
#define SPATIAL_VEC3_H

#include <simd/simd.h>

typedef struct
{
	simd_float3 position, rotation, scale;
} Transform;

typedef struct
{
	char name[32];
	Transform transform;
	float radius;
	float mass;
} CelestialBody;

#endif