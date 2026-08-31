#import "spatial_grid.h"
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>

void build_grid_mesh(RenderState *state) {
  int gridSize = 32;
  float halfExtent = 10.0f;
  int vertexCount = (gridSize + 1) * 6;
  simd_float3 *vertices = calloc((size_t)vertexCount, sizeof(simd_float3));
  int index = 0;

  for (int i = 0; i <= gridSize; ++i) {
    float t = ((float)i / (float)gridSize - 0.5f) * (halfExtent * 2.0f);
    vertices[index++] = (simd_float3){-halfExtent, 0.0f, t};
    vertices[index++] = (simd_float3){halfExtent, 0.0f, t};
    vertices[index++] = (simd_float3){t, 0.0f, -halfExtent};
    vertices[index++] = (simd_float3){t, 0.0f, halfExtent};
    vertices[index++] = (simd_float3){-halfExtent, t, 0.0f};
    vertices[index++] = (simd_float3){halfExtent, t, 0.0f};
  }

  CAMetalLayer *metalLayer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  id<MTLDevice> device = metalLayer.device;
  id<MTLBuffer> vertexBuffer =
      [device newBufferWithBytes:vertices
                          length:vertexCount * sizeof(simd_float3)
                         options:MTLResourceStorageModeShared];
  RenderState_SetVec3Buffer(state, (__bridge void *)vertexBuffer);
  RenderState_SetVertexCount(state, (unsigned long)vertexCount);
  free(vertices);
}