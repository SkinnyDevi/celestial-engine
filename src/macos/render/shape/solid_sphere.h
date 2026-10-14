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

void get_shared_solid_sphere_buffers(void *render_state_ptr, void **out_vbuf,
                                     void **out_ibuf, int *out_index_count);

#endif // MACOS_RENDER_SHAPE_SOLID_SPHERE_H
