#import "debug_gizmos.h"
#import "../../../core/log/log.h"
#import <math.h>
#import <stdlib.h>

// Generates a wireframe circle as line segment pairs.
// plane: 0 = XZ (horizontal), 1 = XY, 2 = YZ
// offset: displacement along the perpendicular axis
static int generate_circle(Vertex *v, int idx, int segments, float radius,
                           float offset, int plane) {
  for (int i = 0; i < segments; i++) {
    float a0 = (float)i / segments * 2.0f * (float)M_PI;
    float a1 = (float)(i + 1) / segments * 2.0f * (float)M_PI;

    float x0, y0, z0, x1, y1, z1;

    switch (plane) {
    case 0: // XZ plane (horizontal ring at y=offset)
      x0 = radius * cosf(a0);
      z0 = radius * sinf(a0);
      y0 = offset;
      x1 = radius * cosf(a1);
      z1 = radius * sinf(a1);
      y1 = offset;
      break;
    case 1: // XY plane (vertical ring at z=0, rotated by offset radians)
    {
      float cx = cosf(a0), sx = sinf(a0);
      float cx1 = cosf(a1), sx1 = sinf(a1);
      float cr = cosf(offset), sr = sinf(offset);
      // Rotate (cx, sx, 0) around Y by offset
      x0 = cx * cr;
      y0 = sx;
      z0 = cx * sr;
      x1 = cx1 * cr;
      y1 = sx1;
      z1 = cx1 * sr;
      // Scale by radius
      x0 *= radius;
      y0 *= radius;
      z0 *= radius;
      x1 *= radius;
      y1 *= radius;
      z1 *= radius;
      break;
    }
    default:
      x0 = y0 = z0 = x1 = y1 = z1 = 0.0f;
      break;
    }

    v[idx++].position = (PackedFloat3){x0, y0, z0};
    v[idx++].position = (PackedFloat3){x1, y1, z1};
  }
  return idx;
}

Vertex *generate_sphere_wireframe(int num_circles, int segments_per_circle,
                                  int *out_vertex_count) {
  int vertices_per_circle = segments_per_circle * 2;
  int total_vertices = num_circles * vertices_per_circle;

  Vertex *vertices = calloc(total_vertices, sizeof(Vertex));
  int idx = 0;

  LOG_DEBUG("Generating orbit sphere wireframe: %d circles, %d segments each, "
            "%d total vertices",
            num_circles, segments_per_circle, total_vertices);

  // Horizontal rings
  int num_latitudes = num_circles / 2;
  for (int i = 0; i < num_latitudes; i++) {
    float latitude = (float)i / num_latitudes * M_PI - M_PI / 2.0f;
    float radius = cosf(latitude);
    float offset = sinf(latitude);
    idx =
        generate_circle(vertices, idx, segments_per_circle, radius, offset, 0);
    LOG_DEBUG(
        "Generated latitude ring: latitude=%.2f, radius=%.3f, offset=%.3f, "
        "idx=%d",
        latitude, radius, offset, idx);
  }

  // Vertical meridians
  int num_meridians = num_circles - num_latitudes;
  for (int i = 0; i < num_meridians; i++) {
    float longitude = (float)i / num_meridians * 2.0f * (float)M_PI;
    idx =
        generate_circle(vertices, idx, segments_per_circle, 1.0f, longitude, 1);
    LOG_DEBUG("Generated meridian ring: longitude=%.2f, radius=%.3f, "
              "offset=%.3f, idx=%d",
              longitude, 1.0f, longitude, idx);
  }

  LOG_DEBUG("Orbit sphere: generated %d vertices (expected %d)", idx,
            total_vertices);
  *out_vertex_count = idx;

  return vertices;
}

Vertex *debug_generate_quality_sphere_wireframe(int quality,
                                                WireframeQuality mesh_quality,
                                                int *out_vertex_count) {
  int num_circles = 4 * quality;
  int vertices_per_circle = mesh_quality * 2;
  int total_vertices = num_circles * vertices_per_circle;

  Vertex *vertices = calloc(total_vertices, sizeof(Vertex));
  int idx = 0;

  LOG_DEBUG("Generating orbit sphere wireframe: %d circles, %d segments each, "
            "%d total vertices",
            num_circles, mesh_quality, total_vertices);

  // Horizontal rings
  int num_latitudes = num_circles / 2;
  for (int i = 0; i < num_latitudes; i++) {
    float latitude = (float)i / num_latitudes * M_PI - M_PI / 2.0f;
    float radius = cosf(latitude);
    float offset = sinf(latitude);
    idx = generate_circle(vertices, idx, mesh_quality, radius, offset, 0);
    LOG_DEBUG(
        "Generated latitude ring: latitude=%.2f, radius=%.3f, offset=%.3f, "
        "idx=%d",
        latitude, radius, offset, idx);
  }

  // Vertical meridians
  int num_meridians = num_circles - num_latitudes;
  for (int i = 0; i < num_meridians; i++) {
    float longitude = (float)i / num_meridians * 2.0f * (float)M_PI;
    idx = generate_circle(vertices, idx, mesh_quality, 1.0f, longitude, 1);
    LOG_DEBUG("Generated meridian ring: longitude=%.2f, radius=%.3f, "
              "offset=%.3f, idx=%d",
              longitude, 1.0f, longitude, idx);
  }

  LOG_DEBUG("Orbit sphere: generated %d vertices (expected %d)", idx,
            total_vertices);
  *out_vertex_count = idx;

  return vertices;
}