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

#import <dispatch/dispatch.h>

typedef struct {
  double x, y, z;
  float radius;
  simd_float4 color;
} StarStaticData;

typedef struct {
  simd_double3 center;
  double radius;
  bool active;
} StarClusterBounds;

static StarStaticData *cached_star_data = NULL;
static size_t cached_star_count = 0;
static uint32_t *cull_scratch_indices = NULL;

static StarClusterBounds m31_cluster = {0};

static size_t last_visible_count = 0;
static struct {
  float azimuth;
  float elevation;
  float zoom;
  simd_double3 center;
  float aspect;
} last_cull_cam = {0};
static bool last_cull_valid = false;

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
  float min_visual_size = dist * 0.0018f;
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

  if (cached_star_data) {
    free(cached_star_data);
    cached_star_data = NULL;
  }

  if (cull_scratch_indices) {
    free(cull_scratch_indices);
    cull_scratch_indices = NULL;
  }

  cached_star_data = malloc(sizeof(StarStaticData) * count);
  cull_scratch_indices = malloc(sizeof(uint32_t) * count);
  cached_star_count = count;
  last_cull_valid = false;
  last_visible_count = 0;

  size_t buffer_size = sizeof(StarInstance) * count;
  id<MTLBuffer> buffer =
      [metal_layer.device newBufferWithLength:buffer_size
                                      options:MTLResourceStorageModeShared];

  simd_double3 m31_min = {1e30, 1e30, 1e30};
  simd_double3 m31_max = {-1e30, -1e30, -1e30};
  size_t m31_count = 0;

  for (size_t i = 0; i < count; i++) {
    MTLStarGraphicsClass *star_gfx;
    DynamicArray_get(stars, i, &star_gfx);
    CelestialBody_Star *star = star_gfx->body;

    double wx = star->position.x * METERS_TO_RENDER_UNITS;
    double wy = star->position.y * METERS_TO_RENDER_UNITS;
    double wz = star->position.z * METERS_TO_RENDER_UNITS;

    cached_star_data[i].x = wx;
    cached_star_data[i].y = wy;
    cached_star_data[i].z = wz;
    cached_star_data[i].radius =
        (float)(star->radius_m * METERS_TO_RENDER_UNITS);
    cached_star_data[i].color = get_star_color(star->spectral_type);

    // M31 stars are external galaxy stars with distance from origin > 10^10
    // render units (> 1000 light years)
    double dist_sq = wx * wx + wy * wy + wz * wz;
    if (dist_sq > 1e20) {
      if (wx < m31_min.x)
        m31_min.x = wx;
      if (wy < m31_min.y)
        m31_min.y = wy;
      if (wz < m31_min.z)
        m31_min.z = wz;
      if (wx > m31_max.x)
        m31_max.x = wx;
      if (wy > m31_max.y)
        m31_max.y = wy;
      if (wz > m31_max.z)
        m31_max.z = wz;
      m31_count++;
    }
  }

  if (m31_count > 100) {
    m31_cluster.center = (m31_min + m31_max) * 0.5;
    double max_r_sq = 0.0;
    for (size_t i = 0; i < count; i++) {
      double wx = cached_star_data[i].x;
      double wy = cached_star_data[i].y;
      double wz = cached_star_data[i].z;
      if (wx * wx + wy * wy + wz * wz > 1e20) {
        simd_double3 diff = simd_make_double3(wx - m31_cluster.center.x,
                                              wy - m31_cluster.center.y,
                                              wz - m31_cluster.center.z);
        double r_sq = simd_length_squared(diff);
        if (r_sq > max_r_sq)
          max_r_sq = r_sq;
      }
    }

    m31_cluster.radius = sqrt(max_r_sq);
    m31_cluster.active = true;
    LOG_INFO("Configured M31 cluster bounding sphere: %lu stars, radius %.2e "
             "render units",
             m31_count, m31_cluster.radius);
  } else {
    m31_cluster.active = false;
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
  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  float aspect = metal_layer.drawableSize.width /
                 MAX(metal_layer.drawableSize.height, 1.0f);
  float near_plane, far_plane;
  camera_get_clipping_planes(camera, &near_plane, &far_plane);

  bool camera_changed = !last_cull_valid ||
                        camera->azimuth != last_cull_cam.azimuth ||
                        camera->elevation != last_cull_cam.elevation ||
                        camera->zoom != last_cull_cam.zoom ||
                        camera->center.x != last_cull_cam.center.x ||
                        camera->center.y != last_cull_cam.center.y ||
                        camera->center.z != last_cull_cam.center.z ||
                        aspect != last_cull_cam.aspect;

  if (camera_changed) {
    CameraFrustum frustum =
        camera_extract_frustum(camera, aspect, 75.0f * (float)M_PI / 180.0f);
    simd_float4 *planes = frustum.planes;

    double cx = camera->center.x;
    double cy = camera->center.y;
    double cz = camera->center.z;

    // Test M31 cluster bounding sphere in 5 nanoseconds
    bool m31_in_frustum = true;
    if (m31_cluster.active) {
      simd_double3 c_rel = m31_cluster.center - camera->center;
      for (int p = 0; p < 5; p++) {
        double dist = planes[p].x * c_rel.x + planes[p].y * c_rel.y +
                      planes[p].z * c_rel.z + planes[p].w;
        if (dist < -m31_cluster.radius) {
          m31_in_frustum = false;
          break;
        }
      }
    }

    // Parallel multi-threaded frustum culling across CPU cores using GCD
    size_t num_blocks = 8;
    if (star_count < 8192)
      num_blocks = 1;
    size_t block_size = (star_count + num_blocks - 1) / num_blocks;
    uint32_t *block_counts = calloc(num_blocks, sizeof(uint32_t));
    uint32_t *block_offsets = calloc(num_blocks, sizeof(uint32_t));

    simd_float4 p0 = planes[0], p1 = planes[1], p2 = planes[2], p3 = planes[3],
                p4 = planes[4];

    dispatch_apply(
        num_blocks, dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_HIGH, 0),
        ^(size_t b) {
          size_t start_idx = b * block_size;
          size_t end_idx = start_idx + block_size;
          if (end_idx > star_count)
            end_idx = star_count;

          uint32_t count = 0;
          uint32_t *out_indices = cull_scratch_indices + start_idx;

          for (size_t i = start_idx; i < end_idx; i++) {
            double wx = cached_star_data[i].x;
            double wy = cached_star_data[i].y;
            double wz = cached_star_data[i].z;

            // If M31 cluster is outside frustum, skip all external
            // stars (> 10^10 render units)
            if (!m31_in_frustum && (wx * wx + wy * wy + wz * wz > 1e20))
              continue;

            float rx = (float)(wx - cx);
            float ry = (float)(wy - cy);
            float rz = (float)(wz - cz);

            // Early-exit 5-plane test against camera frustum
            if (p0.x * rx + p0.y * ry + p0.z * rz + p0.w < 0.0f)
              continue;
            if (p1.x * rx + p1.y * ry + p1.z * rz + p1.w < 0.0f)
              continue;
            if (p2.x * rx + p2.y * ry + p2.z * rz + p2.w < 0.0f)
              continue;
            if (p3.x * rx + p3.y * ry + p3.z * rz + p3.w < 0.0f)
              continue;
            if (p4.x * rx + p4.y * ry + p4.z * rz + p4.w < 0.0f)
              continue;

            out_indices[count++] = (uint32_t)i;
          }
          block_counts[b] = count;
        });

    // Compute prefix sum offsets
    uint32_t total_visible = 0;
    for (size_t b = 0; b < num_blocks; b++) {
      block_offsets[b] = total_visible;
      total_visible += block_counts[b];
    }

    // Pass 2: Pack visible StarInstances directly into the Metal instance
    // buffer
    StarInstance *instances = (StarInstance *)[instance_buffer contents];
    dispatch_apply(
        num_blocks, dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_HIGH, 0),
        ^(size_t b) {
          uint32_t b_count = block_counts[b];
          if (b_count == 0)
            return;

          uint32_t *src_indices = cull_scratch_indices + b * block_size;
          StarInstance *dst = instances + block_offsets[b];

          for (uint32_t j = 0; j < b_count; j++) {
            uint32_t idx = src_indices[j];
            dst[j].position =
                (PackedFloat3){(float)(cached_star_data[idx].x - cx),
                               (float)(cached_star_data[idx].y - cy),
                               (float)(cached_star_data[idx].z - cz)};
            dst[j].radius = cached_star_data[idx].radius;
            dst[j].color = cached_star_data[idx].color;
          }
        });

    free(block_counts);
    free(block_offsets);

    last_visible_count = total_visible;
    last_cull_cam.azimuth = camera->azimuth;
    last_cull_cam.elevation = camera->elevation;
    last_cull_cam.zoom = camera->zoom;
    last_cull_cam.center = camera->center;
    last_cull_cam.aspect = aspect;
    last_cull_valid = true;
  }

  RenderState_SetRenderedStarCount(state, last_visible_count);

  if (last_visible_count == 0)
    return;

  StarUniforms uniforms;
  uniforms.viewMatrix = camera_view_matrix(camera);
  uniforms.projectionMatrix = camera_perspective(70.0f * (float)M_PI / 180.0f,
                                                 aspect, near_plane, far_plane);
  uniforms.minSizeFactor = 0.0018f;
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
            instanceCount:last_visible_count];
}

uint32_t get_rendered_stars_count(void) { return last_visible_count; }

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
  size_t count = DynamicArray_length(&bodies->stars);

  for (size_t i = 0; i < count; i++) {
    CelestialBody_Star *star;
    DynamicArray_get(&bodies->stars, i, &star);
    MTLStarGraphicsClass *mtl_star = MTLStarGraphics_Create(star);
    MTLStarGraphicsClass_init(mtl_star, render_state);
    DynamicArray_push(stars, &mtl_star);

    if (i < 5 || (i + 1) % 10000 == 0 || i == count - 1) {
      LOG_DEBUG("Registered star (%lu / %lu): %s (%s)", i + 1, count,
                ((CelestialBody_Star *)mtl_star->body)->name,
                ((CelestialBody_Star *)mtl_star->body)->body_id);
    }
  }

  init_star_instance_buffer(render_state);
}