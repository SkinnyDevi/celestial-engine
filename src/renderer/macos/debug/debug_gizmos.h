#ifndef MACOS_DEBUG_GIZMOS_H
#define MACOS_DEBUG_GIZMOS_H

#include "../grid/displaced_mesh.h"

typedef enum {
  LOW_QUALITY = 8,
  MEDIUM_QUALITY = 16,
  HIGH_QUALITY = 32,
  MAX_QUALITY = 64
} WireframeQuality;

Vertex *debug_generate_quality_sphere_wireframe(int quality,
                                                WireframeQuality mesh_quality,
                                                int *out_vertex_count);

#endif
