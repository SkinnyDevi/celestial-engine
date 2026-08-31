#import "displaced_mesh.h"
#import <stdlib.h>

Vertex *generate_grid_vertices(int grid_size, float spacing, int num_vertices) {
  Vertex *vertices = calloc(num_vertices, sizeof(Vertex));

  int index = 0;
  for (int i = -grid_size; i <= grid_size; i++) {
    // X-Axis Parallel lines
    vertices[index++].position =
        (PackedFloat3){i * spacing, 0.0f, -grid_size * spacing};
    vertices[index++].position =
        (PackedFloat3){i * spacing, 0.0f, grid_size * spacing};

    // Z-Axis Parallel lines
    vertices[index++].position =
        (PackedFloat3){-grid_size * spacing, 0.0f, i * spacing};
    vertices[index++].position =
        (PackedFloat3){grid_size * spacing, 0.0f, i * spacing};
  }

  return vertices;
}