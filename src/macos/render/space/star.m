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

#define MAX_STAR_CLUSTERS 64

typedef struct {
  double x, y, z;
  float radius;
  simd_float4 color;
  uint8_t cluster_id;
  MTLStarGraphicsClass *star_gfx;
} StarStaticData;

typedef struct {
  char name[64];
  simd_double3 center;
  double radius;
  size_t count;
  bool active;
  bool in_frustum;
} StarCluster;

static StarStaticData *cached_star_data = NULL;
static size_t cached_star_count = 0;
static StarSortItem *cull_scratch_items = NULL;
static StarSortItem *sort_temp_items = NULL;

static StarCluster star_clusters[MAX_STAR_CLUSTERS];
static size_t star_cluster_count = 0;

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

  if (cull_scratch_items) {
    free(cull_scratch_items);
    cull_scratch_items = NULL;
  }

  if (sort_temp_items) {
    free(sort_temp_items);
    sort_temp_items = NULL;
  }

  cached_star_data = malloc(sizeof(StarStaticData) * count);
  cull_scratch_items = malloc(sizeof(StarSortItem) * count);
  sort_temp_items = malloc(sizeof(StarSortItem) * count);
  cached_star_count = count;
  last_cull_valid = false;
  last_visible_count = 0;

  size_t buffer_size = sizeof(StarInstance) * count;
  id<MTLBuffer> buffer =
      [metal_layer.device newBufferWithLength:buffer_size
                                      options:MTLResourceStorageModeShared];

  memset(star_clusters, 0, sizeof(star_clusters));
  star_cluster_count = 0;

  // Cluster 0 is reserved for local stars (Solar Neighborhood, distance <=
  // 10^10 render units)
  star_clusters[0].center = simd_make_double3(0.0, 0.0, 0.0);
  star_clusters[0].radius = 1e10; // ~1000 light years
  star_clusters[0].active = true;
  star_clusters[0].in_frustum = true;
  strncpy(star_clusters[0].name, "Solar Neighborhood",
          sizeof(star_clusters[0].name) - 1);
  star_cluster_count = 1;

  // Deep-sky clustering helpers
  simd_double3 cluster_min[MAX_STAR_CLUSTERS];
  simd_double3 cluster_max[MAX_STAR_CLUSTERS];
  simd_double3 cluster_dir[MAX_STAR_CLUSTERS];
  for (size_t c = 0; c < MAX_STAR_CLUSTERS; c++) {
    cluster_min[c] = simd_make_double3(1e30, 1e30, 1e30);
    cluster_max[c] = simd_make_double3(-1e30, -1e30, -1e30);
    cluster_dir[c] = simd_make_double3(0.0, 0.0, 0.0);
  }

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
    cached_star_data[i].star_gfx = star_gfx;

    // Local stars: within origin radius 10^10 render units
    double dist_sq = wx * wx + wy * wy + wz * wz;
    if (dist_sq <= 1e20) {
      cached_star_data[i].cluster_id = 0;
      star_clusters[0].count++;
    } else {
      // Deep-sky star: group by directional cone from origin
      double inv_len = 1.0 / sqrt(dist_sq);
      simd_double3 s_dir =
          simd_make_double3(wx * inv_len, wy * inv_len, wz * inv_len);

      int matched_cluster = -1;
      for (size_t c = 1; c < star_cluster_count; c++) {
        double dot = simd_dot(s_dir, cluster_dir[c]);
        if (dot > 0.8) {
          matched_cluster = (int)c;
          break;
        }
      }

      if (matched_cluster < 0) {
        if (star_cluster_count < MAX_STAR_CLUSTERS) {
          matched_cluster = (int)star_cluster_count++;
          star_clusters[matched_cluster].active = true;
          star_clusters[matched_cluster].in_frustum = true;
          cluster_dir[matched_cluster] = s_dir;
          snprintf(star_clusters[matched_cluster].name,
                   sizeof(star_clusters[matched_cluster].name),
                   "Deep-Sky Cluster %d", matched_cluster);
        } else {
          matched_cluster = 1;
        }
      }

      uint8_t cid = (uint8_t)matched_cluster;
      cached_star_data[i].cluster_id = cid;
      star_clusters[cid].count++;

      if (wx < cluster_min[cid].x)
        cluster_min[cid].x = wx;
      if (wy < cluster_min[cid].y)
        cluster_min[cid].y = wy;
      if (wz < cluster_min[cid].z)
        cluster_min[cid].z = wz;
      if (wx > cluster_max[cid].x)
        cluster_max[cid].x = wx;
      if (wy > cluster_max[cid].y)
        cluster_max[cid].y = wy;
      if (wz > cluster_max[cid].z)
        cluster_max[cid].z = wz;
    }
  }

  // Finalize cluster centers and bounding radii
  for (size_t c = 1; c < star_cluster_count; c++) {
    if (!star_clusters[c].active || star_clusters[c].count == 0)
      continue;

    star_clusters[c].center = (cluster_min[c] + cluster_max[c]) * 0.5;
    double max_r_sq = 0.0;
    for (size_t i = 0; i < count; i++) {
      if (cached_star_data[i].cluster_id != c)
        continue;
      simd_double3 diff =
          simd_make_double3(cached_star_data[i].x - star_clusters[c].center.x,
                            cached_star_data[i].y - star_clusters[c].center.y,
                            cached_star_data[i].z - star_clusters[c].center.z);
      double r_sq = simd_length_squared(diff);
      if (r_sq > max_r_sq)
        max_r_sq = r_sq;
    }
    star_clusters[c].radius = sqrt(max_r_sq);
    LOG_INFO(
        "Configured star cluster %zu (%s): %lu stars, radius %.2e render units",
        c, star_clusters[c].name, star_clusters[c].count,
        star_clusters[c].radius);
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

    // Test each star cluster bounding sphere against camera frustum
    uint32_t cluster_frustum_mask = 1; // Bit 0 is local stars (always tested)

    for (size_t c = 1; c < star_cluster_count; c++) {
      if (!star_clusters[c].active) {
        star_clusters[c].in_frustum = false;
        continue;
      }
      bool in_f = true;
      simd_double3 c_rel = star_clusters[c].center - camera->center;
      for (int p = 0; p < 5; p++) {
        double dist = planes[p].x * c_rel.x + planes[p].y * c_rel.y +
                      planes[p].z * c_rel.z + planes[p].w;
        if (dist < -star_clusters[c].radius) {
          in_f = false;
          break;
        }
      }
      star_clusters[c].in_frustum = in_f;
      if (in_f) {
        cluster_frustum_mask |= (1u << c);
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
    uint32_t frustum_mask = cluster_frustum_mask;
    simd_float3 cam_orbit_pos = camera_orbit_position(camera);

    dispatch_apply(num_blocks,
                   dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_HIGH, 0),
                   ^(size_t b) {
                     size_t start_idx = b * block_size;
                     size_t end_idx = start_idx + block_size;
                     if (end_idx > star_count)
                       end_idx = star_count;

                     uint32_t count = 0;
                     StarSortItem *out_items = cull_scratch_items + start_idx;

                     for (size_t i = start_idx; i < end_idx; i++) {
                       uint8_t cid = cached_star_data[i].cluster_id;
                       if (!(frustum_mask & (1u << cid)))
                         continue;

                       double wx = cached_star_data[i].x;
                       double wy = cached_star_data[i].y;
                       double wz = cached_star_data[i].z;

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

                       float dx = rx - cam_orbit_pos.x;
                       float dy = ry - cam_orbit_pos.y;
                       float dz = rz - cam_orbit_pos.z;
                       float dist_sq = dx * dx + dy * dy + dz * dz;

                       out_items[count].index = (uint32_t)i;
                       out_items[count].dist_sq = dist_sq;
                       count++;
                     }
                     block_counts[b] = count;
                   });

    // Compute prefix sum offsets
    uint32_t total_visible = 0;
    for (size_t b = 0; b < num_blocks; b++) {
      block_offsets[b] = total_visible;
      total_visible += block_counts[b];
    }

    if (total_visible > 0) {
      // Compact blocks into sort_temp_items
      dispatch_apply(num_blocks,
                     dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_HIGH, 0),
                     ^(size_t b) {
                       if (block_counts[b] > 0) {
                         memcpy(sort_temp_items + block_offsets[b],
                                cull_scratch_items + b * block_size,
                                block_counts[b] * sizeof(StarSortItem));
                       }
                     });

      // Radix sort descending: furthest stars first, closest stars last
      radix_sort_descending(sort_temp_items, cull_scratch_items, total_visible);

      // Pass 2: Pack sorted visible StarInstances directly into the Metal
      // instance buffer
      StarInstance *instances = (StarInstance *)[instance_buffer contents];
      dispatch_apply(
          num_blocks,
          dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_HIGH, 0),
          ^(size_t b) {
            size_t start = b * (total_visible + num_blocks - 1) / num_blocks;
            size_t end =
                (b + 1) * (total_visible + num_blocks - 1) / num_blocks;
            if (end > total_visible)
              end = total_visible;

            for (size_t j = start; j < end; j++) {
              uint32_t idx = sort_temp_items[j].index;
              instances[j].position =
                  (PackedFloat3){(float)(cached_star_data[idx].x - cx),
                                 (float)(cached_star_data[idx].y - cy),
                                 (float)(cached_star_data[idx].z - cz)};
              instances[j].radius = cached_star_data[idx].radius;
              instances[j].color = cached_star_data[idx].color;
            }
          });
    }

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

void star_get_candidate_labels(
    RenderState *state, simd_double3 cam_world_pos,
    void (^callback)(MTLStarGraphicsClass *star, simd_double3 world_pos,
                     float radius_m, const char *name, simd_float4 color)) {
  if (!cached_star_data || cached_star_count == 0)
    return;

  void *followed_body = RenderState_GetFollowedBody(state);
  FollowType followed_type = RenderState_GetFollowedType(state);
  MTLStarGraphicsClass *followed_star =
      (followed_type == FOLLOW_STAR) ? (MTLStarGraphicsClass *)followed_body
                                     : NULL;

  // 1. If a star is followed, always process it immediately
  if (followed_star && followed_star->body) {
    simd_double3 world_pos = simd_make_double3(
        followed_star->body->position.x * METERS_TO_RENDER_UNITS,
        followed_star->body->position.y * METERS_TO_RENDER_UNITS,
        followed_star->body->position.z * METERS_TO_RENDER_UNITS);
    simd_float4 color = get_star_color(followed_star->body->spectral_type);
    callback(followed_star, world_pos, (float)followed_star->body->radius_m,
             followed_star->body->name, color);
  }

  // 2. Check which clusters are near the camera
  const double max_label_dist = 1e7; // ~10 million render units (~1 light year)
  bool cluster_near[MAX_STAR_CLUSTERS];
  memset(cluster_near, 0, sizeof(cluster_near));

  // Local stars (cluster 0) are centered around (0,0,0)
  double dist_origin = simd_length(cam_world_pos);
  if (dist_origin <= 1e10 + max_label_dist)
    cluster_near[0] = true;

  bool any_cluster_near = cluster_near[0];
  for (size_t c = 1; c < star_cluster_count; c++) {
    if (!star_clusters[c].active)
      continue;

    double dist_to_cluster =
        simd_distance(cam_world_pos, star_clusters[c].center);
    if (dist_to_cluster <= star_clusters[c].radius + max_label_dist) {
      cluster_near[c] = true;
      any_cluster_near = true;
    }
  }

  if (!any_cluster_near)
    return;

  // 3. Scan only stars belonging to near clusters
  for (size_t i = 0; i < cached_star_count; i++) {
    uint8_t cid = cached_star_data[i].cluster_id;
    if (!cluster_near[cid])
      continue;

    // Fast distance rejection against camera
    double dx = cached_star_data[i].x - cam_world_pos.x;
    double dy = cached_star_data[i].y - cam_world_pos.y;
    double dz = cached_star_data[i].z - cam_world_pos.z;
    double dist_sq = dx * dx + dy * dy + dz * dz;

    double max_d = (double)cached_star_data[i].radius * 10000.0;
    if (dist_sq > max_d * max_d)
      continue;

    MTLStarGraphicsClass *star = cached_star_data[i].star_gfx;
    if (!star || !star->body || star == followed_star)
      continue;

    simd_double3 world_pos = simd_make_double3(
        cached_star_data[i].x, cached_star_data[i].y, cached_star_data[i].z);
    callback(star, world_pos, (float)star->body->radius_m, star->body->name,
             cached_star_data[i].color);
  }
}

void star_check_intersect(
    RenderState *state, simd_float3 ray_origin,
    void (^check_intersect)(simd_float3 pos, float base_radius,
                            float click_radius, void *star, FollowType type)) {
  if (!cached_star_data || cached_star_count == 0)
    return;

  Camera *camera = RenderState_GetCamera(state);
  double cx = camera->center.x;
  double cy = camera->center.y;
  double cz = camera->center.z;

  for (size_t i = 0; i < cached_star_count; i++) {
    uint8_t cid = cached_star_data[i].cluster_id;
    if (cid > 0 && cid < star_cluster_count && !star_clusters[cid].in_frustum)
      continue;

    double rel_x = cached_star_data[i].x - cx;
    double rel_y = cached_star_data[i].y - cy;
    double rel_z = cached_star_data[i].z - cz;
    simd_float3 pos =
        simd_make_float3((float)rel_x, (float)rel_y, (float)rel_z);
    float base_radius = cached_star_data[i].radius;
    double dx = (double)ray_origin.x - (double)pos.x;
    double dy = (double)ray_origin.y - (double)pos.y;
    double dz = (double)ray_origin.z - (double)pos.z;
    float dist = (float)sqrt(dx * dx + dy * dy + dz * dz);
    float click_radius = dist * 0.045f;
    check_intersect(pos, base_radius, fmaxf(base_radius * 1.3f, click_radius),
                    cached_star_data[i].star_gfx, FOLLOW_STAR);
  }
}