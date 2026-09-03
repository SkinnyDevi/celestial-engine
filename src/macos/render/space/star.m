#import "star.h"
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <stdlib.h>

#import "core/log/log.h"
#import "core/space/star.h"
#import "macos/render/grid/displaced_mesh.h"
#import "macos/render/shape/solid_sphere.h"

simd_float4 get_star_color(StarSpectralType spectral_type) {
  switch (spectral_type) {
  case SPECTRAL_CLASS_O:
    return (simd_float4){0.3f, 0.3f, 1.0f, 1.0f};
  case SPECTRAL_CLASS_B:
    return (simd_float4){0.5f, 0.5f, 1.0f, 1.0f};
  case SPECTRAL_CLASS_A:
    return (simd_float4){0.8f, 0.8f, 1.0f, 1.0f};
  case SPECTRAL_CLASS_F:
    return (simd_float4){1.0f, 1.0f, 1.0f, 1.0f};
  case SPECTRAL_CLASS_G:
    return (simd_float4){1.0f, 1.0f, 0.2f, 1.0f};
  case SPECTRAL_CLASS_K:
    return (simd_float4){1.0f, 0.8f, 0.5f, 1.0f};
  case SPECTRAL_CLASS_M:
    return (simd_float4){1.0f, 0.5f, 0.3f, 1.0f};
  default:
    return (simd_float4){1.0f, 0.0f, 1.0f, 1.0f};
  }
}

void MTLStarGraphicsClass_init(MTLStarGraphicsClass *star,
                               RenderState *render_state) {
  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(render_state);
  if (!metal_layer)
    return;

  SolidSphereMesh mesh = generate_solid_sphere(32, 32);

  id<MTLBuffer> vertex_buffer = [metal_layer.device
      newBufferWithBytes:mesh.vertices
                  length:(sizeof(Vertex) * mesh.vertex_count)
                 options:MTLResourceStorageModeShared];

  id<MTLBuffer> index_buffer = [metal_layer.device
      newBufferWithBytes:mesh.indices
                  length:(sizeof(uint16_t) * mesh.index_count)
                 options:MTLResourceStorageModeShared];

  star->vertex_buffer = (void *)CFBridgingRetain(vertex_buffer);
  star->index_buffer = (void *)CFBridgingRetain(index_buffer);
  star->index_count = mesh.index_count;

  free(mesh.vertices);
  free(mesh.indices);
}

void MTLStarGraphicsClass_draw(MTLStarGraphicsClass *star,
                               RenderState *render_state, void *encoder_ptr) {
  id<MTLRenderCommandEncoder> encoder =
      (__bridge id<MTLRenderCommandEncoder>)encoder_ptr;

  // NOTE: Uniforms (MVP matrix and color) will need to be passed and bound here
  // based on star->body->position / radius.
  simd_float4 color = get_star_color(star->body->spectral_type);

  DisplacedMeshUniforms uniforms;
  id<MTLBuffer> uniform_buffer =
      (__bridge id<MTLBuffer>)RenderState_GetUniformBuffer(render_state);
  if (uniform_buffer) {
    memcpy(&uniforms, [uniform_buffer contents], sizeof(uniforms));
  } else {
    memset(&uniforms, 0, sizeof(uniforms));
  }

  uniforms.gridColor = color;

  [encoder setVertexBytes:&uniforms length:sizeof(uniforms) atIndex:1];
  [encoder setFragmentBytes:&uniforms length:sizeof(uniforms) atIndex:1];

  if (star->pipeline_state) {
    id<MTLRenderPipelineState> pipeline =
        (__bridge id<MTLRenderPipelineState>)star->pipeline_state;
    [encoder setRenderPipelineState:pipeline];
  }

  if (star->vertex_buffer) {
    id<MTLBuffer> vbuf = (__bridge id<MTLBuffer>)star->vertex_buffer;
    [encoder setVertexBuffer:vbuf offset:0 atIndex:0];
  }

  if (star->index_buffer) {
    id<MTLBuffer> ibuf = (__bridge id<MTLBuffer>)star->index_buffer;
    [encoder drawIndexedPrimitives:MTLPrimitiveTypeTriangle
                        indexCount:star->index_count
                         indexType:MTLIndexTypeUInt16
                       indexBuffer:ibuf
                 indexBufferOffset:0];
  }
}

MTLStarGraphicsClass *MTLStarGraphics_Create(CelestialBody_Star *body) {
  MTLStarGraphicsClass *star = malloc(sizeof(MTLStarGraphicsClass));
  if (!star) {
    LOG_ERROR("Failed to allocate memory for star graphics for star: %s (%s)",
              body->name, body->body_id);
    return NULL;
  }

  star->body = body;

  return star;
}

void MTLStarGraphics_Destroy(MTLStarGraphicsClass *star_graphics) {
  if (!star_graphics)
    return;

  if (star_graphics->vertex_buffer)
    CFRelease(star_graphics->vertex_buffer);
  if (star_graphics->index_buffer)
    CFRelease(star_graphics->index_buffer);
  if (star_graphics->pipeline_state)
    CFRelease(star_graphics->pipeline_state);

  free(star_graphics);
}