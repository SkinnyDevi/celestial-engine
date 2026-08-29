#ifndef SPATIAL_VEC3_H
#define SPATIAL_VEC3_H

typedef struct
{
	float x, y, z;
} Vec3;

typedef struct
{
	Vec3 position, rotation, scale;
} Transform;

typedef struct
{
	char name[32];
	Transform transform;
	float radius;
	float mass;
} CelestialBody;

#endif