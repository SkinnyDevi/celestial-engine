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

Vertex *debug_generate_sphere_wireframe(int segments_per_circle,
                                        int *out_vertex_count) {
  // 3 horizontal rings: equator + latitudes at y=±0.5
  // 3 vertical meridians at 0°, 60°, 120°
  int num_circles = 6;
  int verts_per_circle = segments_per_circle * 2;
  int total = num_circles * verts_per_circle;

  Vertex *v = calloc(total, sizeof(Vertex));
  int idx = 0;

  LOG_DEBUG("Generating orbit sphere wireframe: %d circles, %d segments each, "
            "%d total vertices",
            num_circles, segments_per_circle, total);

  // Horizontal rings
  float latitudes[] = {0.0f, 0.5f, -0.5f};
  for (int c = 0; c < 3; c++) {
    float y = latitudes[c];
    float r = sqrtf(1.0f - y * y);
    idx = generate_circle(v, idx, segments_per_circle, r, y, 0);
    LOG_DEBUG("  Latitude ring y=%.2f, radius=%.3f, idx now=%d", y, r, idx);
  }

  // Vertical meridians
  float meridians[] = {0.0f, (float)M_PI / 3.0f, 2.0f * (float)M_PI / 3.0f};
  for (int c = 0; c < 3; c++) {
    idx =
        generate_circle(v, idx, segments_per_circle, 1.0f, meridians[c], 1);
    LOG_DEBUG("  Meridian ring rot=%.3f rad, idx now=%d", meridians[c], idx);
  }

  LOG_DEBUG("Orbit sphere: generated %d vertices (expected %d)", idx, total);
  *out_vertex_count = idx;
  return v;
}

Vertex *debug_generate_point_sphere(int segments_per_circle,
                                    int *out_vertex_count) {
  // Small sphere with 3 rings (equator + 2 meridians) for the fixation point
  int num_circles = 3;
  int verts_per_circle = segments_per_circle * 2;
  int total = num_circles * verts_per_circle;

  Vertex *v = calloc(total, sizeof(Vertex));
  int idx = 0;

  LOG_DEBUG("Generating fixation point sphere: %d circles, %d segments each",
            num_circles, segments_per_circle);

  // One equator
  idx = generate_circle(v, idx, segments_per_circle, 1.0f, 0.0f, 0);

  // Two meridians at 0° and 90°
  idx = generate_circle(v, idx, segments_per_circle, 1.0f, 0.0f, 1);
  idx = generate_circle(v, idx, segments_per_circle, 1.0f,
                        (float)M_PI / 2.0f, 1);

  LOG_DEBUG("Fixation sphere: generated %d vertices (expected %d)", idx, total);
  *out_vertex_count = idx;
  return v;
}
