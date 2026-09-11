#ifndef MACOS_DISPLACED_MESH_H
#define MACOS_DISPLACED_MESH_H

#include "macos/debug/fps_counter.h"
#include "macos/render/shape/vertex.h"

typedef struct RenderState RenderState;

Vertex *generate_grid_vertices(int grid_size, float spacing, int num_vertices);
float dynamic_grid_spacing(float zoom);
void init_grid_mesh(RenderState *state, int grid_size, float spacing);
void toggle_grid_visibility(RenderState *state);
void update_grid_scale(RenderState *state);

#endif