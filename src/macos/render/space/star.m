#import "star.h"
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <stdlib.h>

#import "core/log/log.h"
#import "core/renderer/camera/camera.h"
#import "core/space/defined/stars.h"
#import "core/space/units.h"

#import "macos/render/grid/displaced_mesh.h"
#import "macos/shaders/shader_loader.h"

typedef struct {
  double x, y, z;
} StarWorldPos;

static StarWorldPos *cached_world_positions = NULL;
static size_t cached_world_count = 0;

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
  star->vertex_buffer = NULL;
  star->index_buffer = NULL;
  star->index_count = 0;
  star->pipeline_state = NULL;
}

void MTLStarGraphicsClass_draw(MTLStarGraphicsClass *star,
                               RenderState *render_state, void *encoder_ptr) {
  // Fallback for drawing an individual star if ever called directly
  if (!star || !star->vertex_buffer || !star->index_buffer)
    return;

  id<MTLRenderCommandEncoder> encoder =
      (__bridge id<MTLRenderCommandEncoder>)encoder_ptr;
  simd_float4 color = get_star_color(star->body->spectral_type);

  DisplacedMeshUniforms uniforms;
  id<MTLBuffer> uniform_buffer =
      (__bridge id<MTLBuffer>)RenderState_GetUniformBuffer(render_state);
  if (uniform_buffer) {
    memcpy(&uniforms, [uniform_buffer contents], sizeof(uniforms));
  } else {
    memset(&uniforms, 0, sizeof(uniforms));
  }

  float base_scale = (float)(star->body->radius_m * METERS_TO_RENDER_UNITS);

  Camera *camera = RenderState_GetCamera(render_state);
  simd_float3 cam_pos = camera_orbit_position(camera);
  double rel_x =
      star->body->position.x * METERS_TO_RENDER_UNITS - camera->center.x;
  double rel_y =
      star->body->position.y * METERS_TO_RENDER_UNITS - camera->center.y;
  double rel_z =
      star->body->position.z * METERS_TO_RENDER_UNITS - camera->center.z;
  simd_float3 body_pos =
      simd_make_float3((float)rel_x, (float)rel_y, (float)rel_z);

  float dist = simd_distance(cam_pos, body_pos);
  float min_visual_size = dist * 0.003f;
  float render_scale =
      base_scale > min_visual_size ? base_scale : min_visual_size;

  simd_float4x4 model = {0};
  model.columns[0] = simd_make_float4(render_scale, 0.0f, 0.0f, 0.0f);
  model.columns[1] = simd_make_float4(0.0f, render_scale, 0.0f, 0.0f);
  model.columns[2] = simd_make_float4(0.0f, 0.0f, render_scale, 0.0f);
  model.columns[3] = simd_make_float4(body_pos.x, body_pos.y, body_pos.z, 1.0f);

  uniforms.mvpMatrix = simd_mul(uniforms.mvpMatrix, model);
  uniforms.gridColor = color;

  [encoder setVertexBytes:&uniforms length:sizeof(uniforms) atIndex:1];
  [encoder setFragmentBytes:&uniforms length:sizeof(uniforms) atIndex:1];

  if (star->pipeline_state) {
    id<MTLRenderPipelineState> pipeline =
        (__bridge id<MTLRenderPipelineState>)star->pipeline_state;
    [encoder setRenderPipelineState:pipeline];
  }

  id<MTLBuffer> vbuf = (__bridge id<MTLBuffer>)star->vertex_buffer;
  [encoder setVertexBuffer:vbuf offset:0 atIndex:0];

  id<MTLBuffer> ibuf = (__bridge id<MTLBuffer>)star->index_buffer;
  [encoder drawIndexedPrimitives:MTLPrimitiveTypeTriangle
                      indexCount:star->index_count
                       indexType:MTLIndexTypeUInt16
                     indexBuffer:ibuf
               indexBufferOffset:0];
}

MTLStarGraphicsClass *MTLStarGraphics_Create(CelestialBody_Star *body) {
  MTLStarGraphicsClass *star = calloc(1, sizeof(MTLStarGraphicsClass));
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

void create_star_render_pipeline(RenderState *state) {
  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  if (!metal_layer)
    return;

  const char *shader_src = load_shader_file("celestialbody_instance");
  if (!shader_src) {
    LOG_ERROR("%s", "Failed to load celestialbody_instance shader");
    exit(EXIT_FAILURE);
  }

  NSError *error = nil;
  NSString *source_str = [NSString stringWithUTF8String:shader_src];
  MTLCompileOptions *options = [MTLCompileOptions new];
  id<MTLLibrary> library = [metal_layer.device newLibraryWithSource:source_str
                                                            options:options
                                                              error:&error];
  if (error) {
    LOG_ERROR("Error compiling celestialbody_instance shader library: %s",
              [[error localizedDescription] UTF8String]);
    exit(EXIT_FAILURE);
  }

  MTLRenderPipelineDescriptor *desc =
      [[MTLRenderPipelineDescriptor alloc] init];
  desc.vertexFunction = [library newFunctionWithName:@"star_vertex"];
  desc.fragmentFunction = [library newFunctionWithName:@"star_fragment"];
  desc.colorAttachments[0].pixelFormat = metal_layer.pixelFormat;

  // Alpha blending for antialiased circular discs and dense field glowing
  desc.colorAttachments[0].blendingEnabled = YES;
  desc.colorAttachments[0].rgbBlendOperation = MTLBlendOperationAdd;
  desc.colorAttachments[0].alphaBlendOperation = MTLBlendOperationAdd;
  desc.colorAttachments[0].sourceRGBBlendFactor = MTLBlendFactorSourceAlpha;
  desc.colorAttachments[0].sourceAlphaBlendFactor = MTLBlendFactorSourceAlpha;
  desc.colorAttachments[0].destinationRGBBlendFactor =
      MTLBlendFactorOneMinusSourceAlpha;
  desc.colorAttachments[0].destinationAlphaBlendFactor =
      MTLBlendFactorOneMinusSourceAlpha;

  desc.depthAttachmentPixelFormat = MTLPixelFormatDepth32Float;

  id<MTLRenderPipelineState> pipeline_state =
      [metal_layer.device newRenderPipelineStateWithDescriptor:desc
                                                         error:&error];
  if (error) {
    LOG_ERROR("Error creating star render pipeline state: %s",
              [[error localizedDescription] UTF8String]);
    exit(EXIT_FAILURE);
  }
  RenderState_SetStarPipelineState(state, (__bridge void *)pipeline_state);

  // Depth stencil state: LessEqual compare tests against planets/closer objects
  MTLDepthStencilDescriptor *depth_desc =
      [[MTLDepthStencilDescriptor alloc] init];
  depth_desc.depthCompareFunction = MTLCompareFunctionLessEqual;
  // Depth write is enabled: fragment shader writes true depth for resolved
  // solid star bodies and far-plane depth for distant glow/corona
  depth_desc.depthWriteEnabled = YES;
  id<MTLDepthStencilState> depth_state =
      [metal_layer.device newDepthStencilStateWithDescriptor:depth_desc];
  RenderState_SetStarDepthState(state, (__bridge void *)depth_state);
}

void init_star_instance_buffer(RenderState *state) {
  DynamicArray *stars = RenderState_GetStars(state);
  size_t count = DynamicArray_length(stars);
  if (count == 0)
    return;

  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  if (!metal_layer)
    return;

  if (cached_world_positions) {
    free(cached_world_positions);
    cached_world_positions = NULL;
  }
  cached_world_positions = malloc(sizeof(StarWorldPos) * count);
  cached_world_count = count;

  size_t buffer_size = sizeof(StarInstance) * count;
  id<MTLBuffer> buffer =
      [metal_layer.device newBufferWithLength:buffer_size
                                      options:MTLResourceStorageModeShared];

  StarInstance *instances = (StarInstance *)[buffer contents];
  for (size_t i = 0; i < count; i++) {
    MTLStarGraphicsClass *star_gfx;
    DynamicArray_get(stars, i, &star_gfx);
    CelestialBody_Star *star = star_gfx->body;

    cached_world_positions[i].x = star->position.x * METERS_TO_RENDER_UNITS;
    cached_world_positions[i].y = star->position.y * METERS_TO_RENDER_UNITS;
    cached_world_positions[i].z = star->position.z * METERS_TO_RENDER_UNITS;

    instances[i].radius = (float)(star->radius_m * METERS_TO_RENDER_UNITS);
    instances[i].color = get_star_color(star->spectral_type);
  }

  RenderState_SetStarInstanceBuffer(state, (__bridge void *)buffer);
  RenderState_SetStarInstanceCount(state, count);
  LOG_INFO("Initialized instanced star buffer for %lu stars (%.2f MB)", count,
           (double)buffer_size / (1024.0 * 1024.0));
}

void draw_stars_instanced(RenderState *state, void *encoder_ptr) {
  if (!state || !encoder_ptr)
    return;

  id<MTLRenderCommandEncoder> encoder =
      (__bridge id<MTLRenderCommandEncoder>)encoder_ptr;
  id<MTLRenderPipelineState> pipeline =
      (__bridge id<MTLRenderPipelineState>)RenderState_GetStarPipelineState(
          state);
  id<MTLDepthStencilState> depth_state =
      (__bridge id<MTLDepthStencilState>)RenderState_GetStarDepthState(state);
  id<MTLBuffer> instance_buffer =
      (__bridge id<MTLBuffer>)RenderState_GetStarInstanceBuffer(state);
  size_t star_count = RenderState_GetStarInstanceCount(state);

  if (!pipeline || !instance_buffer || star_count == 0)
    return;

  Camera *camera = RenderState_GetCamera(state);

  // Update instance positions relative to current camera center whenever camera
  // moves
  static simd_double3 last_center = {-1e30, -1e30, -1e30};
  if (camera->center.x != last_center.x || camera->center.y != last_center.y ||
      camera->center.z != last_center.z) {
    StarInstance *instances = (StarInstance *)[instance_buffer contents];
    double cx = camera->center.x;
    double cy = camera->center.y;
    double cz = camera->center.z;
    for (size_t i = 0; i < star_count; i++) {
      instances[i].position =
          (PackedFloat3){(float)(cached_world_positions[i].x - cx),
                         (float)(cached_world_positions[i].y - cy),
                         (float)(cached_world_positions[i].z - cz)};
    }
    last_center = camera->center;
  }

  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  float aspect = metal_layer.drawableSize.width /
                 MAX(metal_layer.drawableSize.height, 1.0f);
  float near_plane, far_plane;
  camera_get_clipping_planes(camera, &near_plane, &far_plane);

  StarUniforms uniforms;
  uniforms.viewMatrix = camera_view_matrix(camera);
  uniforms.projectionMatrix = camera_perspective(70.0f * (float)M_PI / 180.0f,
                                                 aspect, near_plane, far_plane);
  uniforms.minSizeFactor = 0.003f;
  uniforms._pad[0] = 0.0f;
  uniforms._pad[1] = 0.0f;
  uniforms._pad[2] = 0.0f;

  [encoder setRenderPipelineState:pipeline];
  if (depth_state)
    [encoder setDepthStencilState:depth_state];
  [encoder setVertexBytes:&uniforms length:sizeof(uniforms) atIndex:0];
  [encoder setVertexBuffer:instance_buffer offset:0 atIndex:1];

  [encoder drawPrimitives:MTLPrimitiveTypeTriangle
              vertexStart:0
              vertexCount:6
            instanceCount:star_count];
}

void init_celestial_body_stars(RenderState *render_state) {
  DynamicArray *stars = RenderState_GetStars(render_state);

  MTLStarGraphicsClass *mtl_sun = MTLStarGraphics_Create(&SUN);
  MTLStarGraphicsClass *mtl_test = MTLStarGraphics_Create(&TEST_STAR);
  DynamicArray_push(stars, &mtl_sun);
  // DynamicArray_push(stars, &mtl_test);

  size_t count = DynamicArray_length(stars);
  for (size_t i = 0; i < count; i++) {
    MTLStarGraphicsClass *star;
    DynamicArray_get(stars, i, &star);
    MTLStarGraphicsClass_init(star, render_state);
    LOG_DEBUG("Registered star (%lu): %s (%s)", i,
              ((CelestialBody_Star *)star->body)->name,
              ((CelestialBody_Star *)star->body)->body_id);
  }

  init_star_instance_buffer(render_state);
}

void load_celestial_body_stars_from_file(RenderState *render_state,
                                         LoadedSimulationBodies *bodies) {
  DynamicArray *stars = RenderState_GetStars(render_state);

  for (size_t i = 0; i < bodies->num_stars; i++) {
    CelestialBody_Star *star = &bodies->stars[i];
    MTLStarGraphicsClass *mtl_star = MTLStarGraphics_Create(star);
    MTLStarGraphicsClass_init(mtl_star, render_state);
    DynamicArray_push(stars, &mtl_star);

    if (i < 5 || (i + 1) % 10000 == 0 || i == bodies->num_stars - 1) {
      LOG_DEBUG("Registered star (%lu / %lu): %s (%s)", i + 1,
                bodies->num_stars, ((CelestialBody_Star *)mtl_star->body)->name,
                ((CelestialBody_Star *)mtl_star->body)->body_id);
    }
  }

  init_star_instance_buffer(render_state);
}