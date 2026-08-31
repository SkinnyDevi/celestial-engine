#ifndef MACOS_DEBUG_GIZMOS_H
#define MACOS_DEBUG_GIZMOS_H

#include "../grid/displaced_mesh.h"

// Generates a unit wireframe sphere (radius 1.0, centered at origin).
// Scale by camera zoom and translate to center via model matrix at draw time.
// Returns allocated vertex array — caller must free().
Vertex *debug_generate_sphere_wireframe(int segments_per_circle,
                                        int *out_vertex_count);

// Generates a small unit wireframe sphere for marking a point in space.
// Scale to desired size and translate via model matrix at draw time.
// Returns allocated vertex array — caller must free().
Vertex *debug_generate_point_sphere(int segments_per_circle,
                                    int *out_vertex_count);

#endif
