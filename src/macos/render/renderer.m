#import "renderer.h"
#include "core/data/dyn_array.h"
#include "core/space/star.h"
#include "macos/render/space/defined/stars.h"
#include "macos/render/space/star.h"
#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>

#import "core/cli/functions.h"
#import "core/log/log.h"
#import "core/renderer/camera/camera.h"

#import "macos/debug/camera_properties.h"
#import "macos/debug/flags.h"
#import "macos/debug/fps_counter.h"
#import "macos/debug/overlay.h"
#import "macos/debug/sphere_wireframe.h"

#import "macos/event/mouse.h"

#import "macos/render/grid/displaced_mesh.h"
#import "macos/render/grid/spatial_grid.h"
#import "macos/render/state/render_handler.h"
#import "macos/shaders/shader_loader.h"

static RenderState *app_render_state = NULL;

#if DEBUG_CAMERA_PATH_WIREFRAME_VISIBLE
static id<MTLBuffer> debug_camera_orbit_sphere_buffer = nil;
static int debug_camera_orbit_sphere_vertices = 0;
#endif

#if DEBUG_CAMERA_FIXATION_POINT_VISIBLE
static id<MTLBuffer> debug_camera_fixation_sphere_buffer = nil;
static int debug_camera_fixation_sphere_vertices = 0;
#endif

static simd_float4x4 make_scale_matrix(float s) {
  simd_float4x4 m = {0};
  m.columns[0] = simd_make_float4(s, 0, 0, 0);
  m.columns[1] = simd_make_float4(0, s, 0, 0);
  m.columns[2] = simd_make_float4(0, 0, s, 0);
  m.columns[3] = simd_make_float4(0, 0, 0, 1);
  return m;
}

static simd_float4x4 make_translation_matrix(simd_float3 t) {
  simd_float4x4 m = {0};
  m.columns[0] = simd_make_float4(1, 0, 0, 0);
  m.columns[1] = simd_make_float4(0, 1, 0, 0);
  m.columns[2] = simd_make_float4(0, 0, 1, 0);
  m.columns[3] = simd_make_float4(t.x, t.y, t.z, 1);
  return m;
}

static void update_camera_uniforms(RenderState *state) {
  if (!state || !RenderState_GetUniformBuffer(state)) {
    return;
  }

  Camera *camera = RenderState_GetCamera(state);

  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  float aspect = metal_layer.drawableSize.width /
                 MAX(metal_layer.drawableSize.height, 1.0f);

  simd_float4x4 view = camera_view_matrix(camera);
  simd_float4x4 projection =
      camera_perspective(70.0f * (float)M_PI / 180.0f, aspect, 0.1f, 100.0f);

  DisplacedMeshUniforms uniforms;
  uniforms.mvpMatrix = simd_mul(projection, view);
  uniforms.gridColor = (simd_float4){1.0f, 1.0f, 1.0f, 0.85f};

  id<MTLBuffer> uniform_buffer =
      (__bridge id<MTLBuffer>)RenderState_GetUniformBuffer(state);
  memcpy([uniform_buffer contents], &uniforms, sizeof(uniforms));
}

// CPU side
void init_grid_mesh(RenderState *state, int grid_size, float spacing) {
  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);

  int num_vertices = (grid_size * 2 + 1) * 4;
  Vertex *vertices = generate_grid_vertices(grid_size, spacing, num_vertices);
  id<MTLBuffer> vertex_buffer =
      [metal_layer.device newBufferWithBytes:vertices
                                      length:(sizeof(Vertex) * num_vertices)
                                     options:MTLResourceStorageModeShared];
  RenderState_SetVec3Buffer(state, (__bridge void *)vertex_buffer);
  RenderState_SetVertexCount(state, num_vertices);
  free(vertices);

  LOG_DEBUG("Grid mesh: %d vertices, buffer size: %lu bytes", num_vertices,
            (unsigned long)(sizeof(Vertex) * num_vertices));
}

void create_render_pipeline(RenderState *state) {
  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  id<MTLLibrary> shader_library =
      (__bridge id<MTLLibrary>)RenderState_GetGridShaderLib(state);

  MTLRenderPipelineDescriptor *pipeline_descriptor =
      [[MTLRenderPipelineDescriptor alloc] init];
  pipeline_descriptor.vertexFunction =
      [shader_library newFunctionWithName:@"grid_vertex"];
  pipeline_descriptor.fragmentFunction =
      [shader_library newFunctionWithName:@"grid_fragment"];
  pipeline_descriptor.colorAttachments[0].pixelFormat = metal_layer.pixelFormat;

  NSError *error = nil;
  id<MTLRenderPipelineState> pipeline_state = [metal_layer.device
      newRenderPipelineStateWithDescriptor:pipeline_descriptor
                                     error:&error];
  if (error) {
    LOG_ERROR("Error creating pipeline state: %s",
              [[error localizedDescription] UTF8String]);
    exit(EXIT_FAILURE);
  }
  RenderState_SetPipelineState(state, (__bridge void *)pipeline_state);
}

void generate_debug_graphics(RenderState *state) {
  if (cli_should_show_fps() || cli_is_debug_mode())
    debug_create_fps_counter_overlay(state);

  if (!cli_is_debug_mode())
    return;

#if DEBUG_CAMERA_PROPERTIES_VISIBLE
  debug_create_camera_properties_overlay(state);
#endif

  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);

#if DEBUG_CAMERA_PATH_WIREFRAME_VISIBLE
  int orbit_count = 0;
  Vertex *orbit_vertices =
      debug_generate_quality_sphere_wireframe(4, MEDIUM_QUALITY, &orbit_count);
  debug_camera_orbit_sphere_buffer =
      [metal_layer.device newBufferWithBytes:orbit_vertices
                                      length:(sizeof(Vertex) * orbit_count)
                                     options:MTLResourceStorageModeShared];
  debug_camera_orbit_sphere_vertices = orbit_count;
  free(orbit_vertices);
  LOG_DEBUG("Orbit sphere buffer: %d vertices, buffer=%p", orbit_count,
            (__bridge void *)debug_camera_orbit_sphere_buffer);
#endif

#if DEBUG_CAMERA_FIXATION_POINT_VISIBLE
  int fixation_count = 0;
  Vertex *fixation_vertices = debug_generate_quality_sphere_wireframe(
      4, MEDIUM_QUALITY, &fixation_count);
  debug_camera_fixation_sphere_buffer =
      [metal_layer.device newBufferWithBytes:fixation_vertices
                                      length:(sizeof(Vertex) * fixation_count)
                                     options:MTLResourceStorageModeShared];
  debug_camera_fixation_sphere_vertices = fixation_count;
  free(fixation_vertices);
  LOG_DEBUG("Fixation sphere buffer: %d vertices, buffer=%p", fixation_count,
            (__bridge void *)debug_camera_fixation_sphere_buffer);
#endif
}

void init_celestial_bodies(RenderState *render_state) {
  DynamicArray *stars = RenderState_GetStars(render_state);

  MTLStarGraphicsClass *mtl_sun = MTLStarGraphics_Create(&SUN);
  DynamicArray_push(stars, &mtl_sun);

  size_t count = DynamicArray_length(stars);
  for (size_t i = 0; i < count; i++) {
    MTLStarGraphicsClass *star;
    DynamicArray_get(stars, i, &star);
    MTLStarGraphicsClass_init(star, render_state);
    LOG_DEBUG("Registered star (%lu): %s (%s)", i,
              ((CelestialBody_Star *)star->body)->name,
              ((CelestialBody_Star *)star->body)->body_id);
  }
  LOG_DEBUG("Total celestial bodies registered: %lu",
            DynamicArray_length(stars));
}

RendererHandle init_metal_window(int width, int height, const char *title) {
  LOG_DEBUG("Initializing Metal window.", NULL);
  [NSApplication sharedApplication];
  [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];

  NSRect frame = NSMakeRect(0, 0, width, height);
  NSWindow *window = [[NSWindow alloc]
      initWithContentRect:frame
                styleMask:(NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                           NSWindowStyleMaskResizable)
                  backing:NSBackingStoreBuffered
                    defer:NO];
  [window setTitle:[NSString stringWithUTF8String:title]];
  [window makeKeyAndOrderFront:nil];
  [NSApp activateIgnoringOtherApps:YES];

  RenderState *state = RenderState_Create();
  if (!state) {
    return NULL;
  }

  RenderState_Init(state, (__bridge void *)window);
  app_render_state = state;

  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  metal_layer.pixelFormat = MTLPixelFormatBGRA8Unorm;
  [window.contentView setWantsLayer:YES];
  [window.contentView setLayer:metal_layer];
  metal_layer.frame = window.contentView.bounds;
  metal_layer.autoresizingMask = kCALayerWidthSizable | kCALayerHeightSizable;
  metal_layer.drawableSize = CGSizeMake(width, height);

  init_grid_mesh(state, 10, 1.0f);
  compile_grid_shader_lib(state, "displaced_grid_mesh");

  id<MTLBuffer> uniform_buffer =
      [metal_layer.device newBufferWithLength:sizeof(DisplacedMeshUniforms)
                                      options:MTLResourceStorageModeShared];
  RenderState_SetUniformBuffer(state, (__bridge void *)uniform_buffer);

  create_render_pipeline(state);
  generate_debug_graphics(state);
  init_celestial_bodies(state);

  Camera *camera = RenderState_GetCamera(state);
  simd_float3 cam_pos = camera_orbit_position(camera);
  LOG_DEBUG("Camera initialized: az=%.3f el=%.3f zoom=%.3f center=(%.2f, "
            "%.2f, %.2f) pos=(%.2f, %.2f, %.2f)",
            camera->azimuth, camera->elevation, camera->zoom, camera->center.x,
            camera->center.y, camera->center.z, cam_pos.x, cam_pos.y,
            cam_pos.z);

  update_camera_uniforms(state);
  [NSApp finishLaunching];
  LOG_DEBUG("Metal window initialized.", NULL);
  return (RendererHandle)state;
}

void draw_debug_fps(RenderState *state, bool use_extended_data,
                    FPSData *out_data) {
  if (!cli_is_debug_mode() && !cli_should_show_fps())
    return;

  DebugOverlay *overlay = RenderState_GetFPSCounterOverlay(state);
  if (!overlay)
    return;

  debug_overlay_clear(overlay);
  debug_overlay_update_fps(overlay, use_extended_data, out_data);
}

void draw_debug_graphics(RenderState *state,
                         id<MTLRenderCommandEncoder> encoder) {
  FPSData fps_data;
  draw_debug_fps(state,
                 DEBUG_FPS_COUNTER_ADVANCED_VISIBLE &&
                     cli_should_show_advanced_fps(),
                 &fps_data);

  if (!cli_is_debug_mode())
    return;

  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);

  Camera *cam = RenderState_GetCamera(state);
  float aspect = metal_layer.drawableSize.width /
                 MAX(metal_layer.drawableSize.height, 1.0f);
  simd_float4x4 view = camera_view_matrix(cam);
  simd_float4x4 proj =
      camera_perspective(70.0f * (float)M_PI / 180.0f, aspect, 0.1f, 100.0f);
  simd_float4x4 vp = simd_mul(proj, view);

#if DEBUG_CAMERA_PROPERTIES_VISIBLE
  unsigned long long debug_frame_counter = fps_data.frame_count;
  if (debug_frame_counter % 120 == 0) {
    simd_float3 cam_pos = camera_orbit_position(cam);
    LOG_DEBUG(
        "[Frame %llu | FPS %.2f] Camera: zoom=%.3f center=(%.2f, %.2f, %.2f) "
        "pos=(%.2f, %.2f, %.2f)",
        debug_frame_counter, fps_data.fps_avg, cam->zoom, cam->center.x,
        cam->center.y, cam->center.z, cam_pos.x, cam_pos.y, cam_pos.z);
  }
#endif

#if DEBUG_CAMERA_PATH_WIREFRAME_VISIBLE
  {
    simd_float4x4 model = simd_mul(make_translation_matrix(cam->center),
                                   make_scale_matrix(cam->zoom));
    DisplacedMeshUniforms mesh_uniforms;
    mesh_uniforms.mvpMatrix = simd_mul(vp, model);
    mesh_uniforms.gridColor = (simd_float4){1.0f, 0.41f, 0.71f, 0.7f}; // Pink

    [encoder setVertexBuffer:debug_camera_orbit_sphere_buffer
                      offset:0
                     atIndex:0];
    [encoder setVertexBytes:&mesh_uniforms
                     length:sizeof(mesh_uniforms)
                    atIndex:1];
    [encoder setFragmentBytes:&mesh_uniforms
                       length:sizeof(mesh_uniforms)
                      atIndex:1];
    [encoder drawPrimitives:MTLPrimitiveTypeLine
                vertexStart:0
                vertexCount:debug_camera_orbit_sphere_vertices];
  }
#endif

#if DEBUG_CAMERA_FIXATION_POINT_VISIBLE
  {
    float fixation_radius = 0.15f;
    simd_float4x4 model = simd_mul(make_translation_matrix(cam->center),
                                   make_scale_matrix(fixation_radius));
    DisplacedMeshUniforms mesh_uniforms;
    mesh_uniforms.mvpMatrix = simd_mul(vp, model);
    mesh_uniforms.gridColor = (simd_float4){1.0f, 0.15f, 0.15f, 1.0f}; // Red

    [encoder setVertexBuffer:debug_camera_fixation_sphere_buffer
                      offset:0
                     atIndex:0];
    [encoder setVertexBytes:&mesh_uniforms
                     length:sizeof(mesh_uniforms)
                    atIndex:1];
    [encoder setFragmentBytes:&mesh_uniforms
                       length:sizeof(mesh_uniforms)
                      atIndex:1];
    [encoder drawPrimitives:MTLPrimitiveTypeLine
                vertexStart:0
                vertexCount:debug_camera_fixation_sphere_vertices];
  }
#endif
}

void draw_grid(RenderState *state, id<MTLRenderCommandEncoder> encoder) {
  id<MTLBuffer> vertex_buffer =
      (__bridge id<MTLBuffer>)RenderState_GetVec3Buffer(state);
  id<MTLBuffer> uniform_buffer =
      (__bridge id<MTLBuffer>)RenderState_GetUniformBuffer(state);

  [encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
  [encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
  [encoder setFragmentBuffer:uniform_buffer offset:0 atIndex:1];
  [encoder drawPrimitives:MTLPrimitiveTypeLine
              vertexStart:0
              vertexCount:RenderState_GetVertexCount(state)];
}

void draw_celestial_bodies(RenderState *state,
                           id<MTLRenderCommandEncoder> encoder) {
  DynamicArray *stars = RenderState_GetStars(state);
  for (size_t i = 0; i < stars->length; i++) {
    MTLStarGraphicsClass *star;
    DynamicArray_get(stars, i, &star);
    MTLStarGraphicsClass_draw(star, state, (__bridge void *)encoder);
  }
}

void draw_frame(RendererHandle handle) {
  RenderState *state = (RenderState *)handle;
  if (!state || !RenderState_GetPipelineState(state))
    return;

  update_camera_uniforms(state);

#if DEBUG_CAMERA_PROPERTIES_VISIBLE
  if (cli_is_debug_mode()) {
    DebugOverlay *overlay = RenderState_GetCameraDebugOverlay(state);
    if (overlay) {
      debug_overlay_clear(overlay);
      debug_overlay_update_camera(overlay, RenderState_GetCamera(state));
    }
  }
#endif

  CAMetalLayer *metal_layer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  id<MTLCommandQueue> command_queue =
      (__bridge id<MTLCommandQueue>)RenderState_GetCommandQueue(state);
  id<MTLRenderPipelineState> pipeline_state =
      (__bridge id<MTLRenderPipelineState>)RenderState_GetPipelineState(state);

  @autoreleasepool {
    id<CAMetalDrawable> drawable = [metal_layer nextDrawable];
    if (!drawable)
      return;

    id<MTLCommandBuffer> command_buffer = [command_queue commandBuffer];
    MTLRenderPassDescriptor *pass_descriptor =
        [MTLRenderPassDescriptor renderPassDescriptor];
    pass_descriptor.colorAttachments[0].texture = drawable.texture;
    pass_descriptor.colorAttachments[0].loadAction = MTLLoadActionClear;
    pass_descriptor.colorAttachments[0].clearColor =
        MTLClearColorMake(0.0, 0.0, 0.0, 1.0); // BG Color

    id<MTLRenderCommandEncoder> encoder =
        [command_buffer renderCommandEncoderWithDescriptor:pass_descriptor];
    [encoder setRenderPipelineState:pipeline_state];

    draw_grid(state, encoder);
    draw_debug_graphics(state, encoder);
    draw_celestial_bodies(state, encoder);

    [encoder endEncoding];

    [command_buffer presentDrawable:drawable];
    [command_buffer commit];
  }
}

void pump_os_events(void) {
  @autoreleasepool {
    NSEvent *event;
    while ((event = [NSApp
                nextEventMatchingMask:NSEventMaskAny
                            untilDate:[NSDate dateWithTimeIntervalSinceNow:0.0]
                               inMode:NSDefaultRunLoopMode
                              dequeue:YES])) {
      [NSApp sendEvent:event];

      if (!app_render_state)
        continue;

      RenderState *state = app_render_state;
      if ([event type] == NSEventTypeLeftMouseDown) {
        NSPoint mouse = [event locationInWindow];
        MousePoint point = {mouse.x, mouse.y};
        event_left_mouse_down(state, point);
      } else if ([event type] == NSEventTypeLeftMouseDragged) {
        NSPoint current = [event locationInWindow];
        MousePoint point = {current.x, current.y};
        bool shiftHeld =
            ([event modifierFlags] & NSEventModifierFlagShift) != 0;
        event_left_mouse_drag(state, point, shiftHeld);
      } else if ([event type] == NSEventTypeLeftMouseUp) {
        RenderState_SetDragging(state, false);
      } else if ([event type] == NSEventTypeScrollWheel) {
        Camera *camera = RenderState_GetCamera(state);
        camera_zoom_from_input(camera, (float)[event scrollingDeltaY]);
      }
    }
  }
}
