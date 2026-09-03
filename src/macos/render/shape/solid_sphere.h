#ifndef MACOS_RENDER_SHAPE_SOLID_SPHERE_H
#define MACOS_RENDER_SHAPE_SOLID_SPHERE_H

#include "macos/render/shape/vertex.h"
#include <stdint.h>

typedef struct {
  Vertex *vertices;
  uint16_t *indices;
  int vertex_count;
  int index_count;
} SolidSphereMesh;

SolidSphereMesh generate_solid_sphere(int latitude_bands, int longitude_bands);

#endif // MACOS_RENDER_SHAPE_SOLID_SPHERE_H
