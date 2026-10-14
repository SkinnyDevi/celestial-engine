#import "solid_sphere.h"
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <QuartzCore/CAMetalLayer.h>
#import <math.h>
#import <stdlib.h>

#import "macos/render/state/render_state.h"

SolidSphereMesh generate_solid_sphere(int latitude_bands, int longitude_bands) {
  SolidSphereMesh mesh;
  mesh.vertex_count = (latitude_bands + 1) * (longitude_bands + 1);
  mesh.index_count = latitude_bands * longitude_bands * 6;

  mesh.vertices = malloc(sizeof(Vertex) * mesh.vertex_count);
  mesh.indices = malloc(sizeof(uint16_t) * mesh.index_count);

  int v_idx = 0;
  for (int lat = 0; lat <= latitude_bands; lat++) {
    float theta = lat * M_PI / latitude_bands;
    float sinTheta = sinf(theta);
    float cosTheta = cosf(theta);

    for (int lon = 0; lon <= longitude_bands; lon++) {
      float phi = lon * 2 * M_PI / longitude_bands;
      float sinPhi = sinf(phi);
      float cosPhi = cosf(phi);

      float x = cosPhi * sinTheta;
      float y = cosTheta;
      float z = sinPhi * sinTheta;

      mesh.vertices[v_idx].position = (PackedFloat3){x, y, z};
      v_idx++;
    }
  }

  int i_idx = 0;
  for (int lat = 0; lat < latitude_bands; lat++) {
    for (int lon = 0; lon < longitude_bands; lon++) {
      int first = (lat * (longitude_bands + 1)) + lon;
      int second = first + longitude_bands + 1;

      // Triangle 1
      mesh.indices[i_idx++] = first;
      mesh.indices[i_idx++] = second;
      mesh.indices[i_idx++] = first + 1;

      // Triangle 2
      mesh.indices[i_idx++] = second;
      mesh.indices[i_idx++] = second + 1;
      mesh.indices[i_idx++] = first + 1;
    }
  }

  return mesh;
}

static id<MTLBuffer> shared_vbuf = nil;
static id<MTLBuffer> shared_ibuf = nil;
static int shared_idx_count = 0;

void get_shared_solid_sphere_buffers(void *render_state_ptr, void **out_vbuf,
                                     void **out_ibuf, int *out_index_count) {
  if (!shared_vbuf && render_state_ptr) {
    RenderState *state = (RenderState *)render_state_ptr;
    CAMetalLayer *metal_layer =
        (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);

    if (!metal_layer)
      return;

    SolidSphereMesh mesh = generate_solid_sphere(32, 32);
    shared_vbuf = [metal_layer.device
        newBufferWithBytes:mesh.vertices
                    length:(sizeof(Vertex) * mesh.vertex_count)
                   options:MTLResourceStorageModeShared];
    shared_ibuf = [metal_layer.device
        newBufferWithBytes:mesh.indices
                    length:(sizeof(uint16_t) * mesh.index_count)
                   options:MTLResourceStorageModeShared];
    shared_idx_count = mesh.index_count;
    free(mesh.vertices);
    free(mesh.indices);
  }

  if (out_vbuf)
    *out_vbuf = (__bridge void *)shared_vbuf;

  if (out_ibuf)
    *out_ibuf = (__bridge void *)shared_ibuf;

  if (out_index_count)
    *out_index_count = shared_idx_count;
}
