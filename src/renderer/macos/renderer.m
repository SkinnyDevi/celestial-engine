#import "renderer.h"
#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>

static RenderState *g_activeRenderState = NULL;

// Debug gizmo buffers (orbit sphere + fixation point sphere)
static id<MTLBuffer> g_debugOrbitSphereBuffer = nil;
static int g_debugOrbitSphereVertexCount = 0;
static id<MTLBuffer> g_debugFixationSphereBuffer = nil;
static int g_debugFixationSphereVertexCount = 0;

// Throttle per-frame debug logs (log every N frames)
static int g_debugFrameCounter = 0;

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

// Inline shader source matching displaced_grid_mesh.msl
static NSString *const kDisplacedGridShaderSource =
    @"#include <metal_stdlib>\n"
     "using namespace metal;\n"
     "struct VertexIn { packed_float3 position; };\n"
     "struct VertexOut { float4 position [[position]]; };\n"
     "struct Uniforms { float4x4 mvpMatrix; float4 gridColor; };\n"
     "vertex VertexOut grid_vertex(const device VertexIn *vertices "
     "[[buffer(0)]], "
     "constant Uniforms &uniforms [[buffer(1)]], "
     "uint vid [[vertex_id]]) {\n"
     "  VertexOut out;\n"
     "  out.position = uniforms.mvpMatrix * float4(vertices[vid].position, "
     "1.0);\n"
     "  return out;\n"
     "}\n"
     "fragment float4 grid_fragment(VertexOut in [[stage_in]], "
     "constant Uniforms &uniforms [[buffer(1)]]) {\n"
     "  return uniforms.gridColor;\n"
     "}\n";

static void update_camera_uniforms(RenderState *state) {
  if (!state || !RenderState_GetUniformBuffer(state)) {
    return;
  }

  Camera *camera = RenderState_GetCamera(state);

  CAMetalLayer *metalLayer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  float aspect =
      metalLayer.drawableSize.width / MAX(metalLayer.drawableSize.height, 1.0f);

  // Build view matrix by rotating the world (Blender-style), not via look_at
  simd_float4x4 view = camera_view_matrix(camera);
  simd_float4x4 projection =
      camera_perspective(70.0f * (float)M_PI / 180.0f, aspect, 0.1f, 100.0f);

  DisplacedMeshUniforms uniforms;
  uniforms.mvpMatrix = simd_mul(projection, view);
  uniforms.gridColor = (simd_float4){1.0f, 1.0f, 1.0f, 0.85f};

  id<MTLBuffer> uniformBuffer =
      (__bridge id<MTLBuffer>)RenderState_GetUniformBuffer(state);
  memcpy([uniformBuffer contents], &uniforms, sizeof(uniforms));
}

RendererHandle init_metal_window(int width, int height, const char *title) {
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
  g_activeRenderState = state;

  CAMetalLayer *metalLayer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  metalLayer.pixelFormat = MTLPixelFormatBGRA8Unorm;
  [window.contentView setWantsLayer:YES];
  [window.contentView setLayer:metalLayer];
  metalLayer.frame = window.contentView.bounds;
  metalLayer.autoresizingMask = kCALayerWidthSizable | kCALayerHeightSizable;
  metalLayer.drawableSize = CGSizeMake(width, height);

  // --- Generate displaced grid mesh vertices on CPU ---
  int grid_size = 10;
  float spacing = 1.0f;
  int num_vertices = (grid_size * 2 + 1) * 4;
  Vertex *vertices = generate_grid_vertices(grid_size, spacing, num_vertices);
  id<MTLBuffer> vertexBuffer =
      [metalLayer.device newBufferWithBytes:vertices
                                     length:(sizeof(Vertex) * num_vertices)
                                    options:MTLResourceStorageModeShared];
  RenderState_SetVec3Buffer(state, (__bridge void *)vertexBuffer);
  RenderState_SetVertexCount(state, num_vertices);
  free(vertices);

  LOG_DEBUG("Grid mesh: %d vertices, buffer size: %lu bytes", num_vertices,
            (unsigned long)(sizeof(Vertex) * num_vertices));

  // --- Compile the displaced grid shader ---
  NSError *error = nil;
  MTLCompileOptions *compileOptions = [MTLCompileOptions new];
  id<MTLLibrary> shaderLibrary =
      [metalLayer.device newLibraryWithSource:kDisplacedGridShaderSource
                                      options:compileOptions
                                        error:&error];
  if (error) {
    NSLog(@"Error creating shader library: %@", error);
    RenderState_Destroy(state);
    return NULL;
  }
  RenderState_SetShaderLibrary(state, (__bridge void *)shaderLibrary);

  // --- Create uniform buffer for MVP + grid color ---
  id<MTLBuffer> uniformBuffer =
      [metalLayer.device newBufferWithLength:sizeof(DisplacedMeshUniforms)
                                     options:MTLResourceStorageModeShared];
  RenderState_SetUniformBuffer(state, (__bridge void *)uniformBuffer);

  // --- Build the render pipeline ---
  MTLRenderPipelineDescriptor *pipelineDescriptor =
      [[MTLRenderPipelineDescriptor alloc] init];
  pipelineDescriptor.vertexFunction =
      [shaderLibrary newFunctionWithName:@"grid_vertex"];
  pipelineDescriptor.fragmentFunction =
      [shaderLibrary newFunctionWithName:@"grid_fragment"];
  pipelineDescriptor.colorAttachments[0].pixelFormat = metalLayer.pixelFormat;

  id<MTLRenderPipelineState> pipelineState =
      [metalLayer.device newRenderPipelineStateWithDescriptor:pipelineDescriptor
                                                        error:&error];
  if (error) {
    NSLog(@"Error creating pipeline state: %@", error);
    RenderState_Destroy(state);
    return NULL;
  }
  RenderState_SetPipelineState(state, (__bridge void *)pipelineState);

  if (cli_is_debug_mode()) {
    DebugOverlay *overlay = debug_overlay_create((__bridge void *)window);
    RenderState_SetDebugOverlay(state, overlay);
    debug_overlay_update_camera(overlay, RenderState_GetCamera(state));

    // --- Generate debug gizmo geometry ---

    // Orbit path sphere (unit sphere, will be scaled by zoom at draw time)
    int orbitCount = 0;
    Vertex *orbitVerts = debug_generate_sphere_wireframe(48, &orbitCount);
    g_debugOrbitSphereBuffer =
        [metalLayer.device newBufferWithBytes:orbitVerts
                                       length:(sizeof(Vertex) * orbitCount)
                                      options:MTLResourceStorageModeShared];
    g_debugOrbitSphereVertexCount = orbitCount;
    free(orbitVerts);
    LOG_DEBUG("Orbit sphere buffer: %d vertices, buffer=%p", orbitCount,
              (__bridge void *)g_debugOrbitSphereBuffer);

    // Fixation point sphere (unit sphere, will be scaled small at draw time)
    int fixCount = 0;
    Vertex *fixVerts = debug_generate_point_sphere(24, &fixCount);
    g_debugFixationSphereBuffer =
        [metalLayer.device newBufferWithBytes:fixVerts
                                       length:(sizeof(Vertex) * fixCount)
                                      options:MTLResourceStorageModeShared];
    g_debugFixationSphereVertexCount = fixCount;
    free(fixVerts);
    LOG_DEBUG("Fixation sphere buffer: %d vertices, buffer=%p", fixCount,
              (__bridge void *)g_debugFixationSphereBuffer);
  }

  Camera *camera = RenderState_GetCamera(state);
  camera_set_position(camera, simd_make_float3(5.0f, 5.0f, 5.0f));

  simd_float3 camPos = camera_orbit_position(camera);
  LOG_DEBUG("Camera initialized: az=%.3f el=%.3f zoom=%.3f center=(%.2f, "
            "%.2f, %.2f) pos=(%.2f, %.2f, %.2f)",
            camera->azimuth, camera->elevation, camera->zoom, camera->center.x,
            camera->center.y, camera->center.z, camPos.x, camPos.y, camPos.z);

  update_camera_uniforms(state);
  [NSApp finishLaunching];
  return (RendererHandle)state;
}

void draw_frame(RendererHandle handle) {
  RenderState *state = (RenderState *)handle;
  if (!state || !RenderState_GetPipelineState(state)) {
    return;
  }

  update_camera_uniforms(state);
  g_debugFrameCounter++;

  if (cli_is_debug_mode()) {
    DebugOverlay *overlay = RenderState_GetDebugOverlay(state);
    if (overlay) {
      debug_overlay_clear(overlay);
      debug_overlay_update_camera(overlay, RenderState_GetCamera(state));
    }
  }

  CAMetalLayer *metalLayer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  id<MTLCommandQueue> commandQueue =
      (__bridge id<MTLCommandQueue>)RenderState_GetCommandQueue(state);
  id<MTLRenderPipelineState> pipelineState =
      (__bridge id<MTLRenderPipelineState>)RenderState_GetPipelineState(state);
  id<MTLBuffer> vertexBuffer =
      (__bridge id<MTLBuffer>)RenderState_GetVec3Buffer(state);
  id<MTLBuffer> uniformBuffer =
      (__bridge id<MTLBuffer>)RenderState_GetUniformBuffer(state);

  @autoreleasepool {
    id<CAMetalDrawable> drawable = [metalLayer nextDrawable];
    if (!drawable) {
      return;
    }

    id<MTLCommandBuffer> commandBuffer = [commandQueue commandBuffer];
    MTLRenderPassDescriptor *passDescriptor =
        [MTLRenderPassDescriptor renderPassDescriptor];
    passDescriptor.colorAttachments[0].texture = drawable.texture;
    passDescriptor.colorAttachments[0].loadAction = MTLLoadActionClear;
    passDescriptor.colorAttachments[0].clearColor =
        MTLClearColorMake(0.0, 0.0, 0.0, 1.0);

    id<MTLRenderCommandEncoder> encoder =
        [commandBuffer renderCommandEncoderWithDescriptor:passDescriptor];
    [encoder setRenderPipelineState:pipelineState];

    // --- Draw the grid ---
    [encoder setVertexBuffer:vertexBuffer offset:0 atIndex:0];
    [encoder setVertexBuffer:uniformBuffer offset:0 atIndex:1];
    [encoder setFragmentBuffer:uniformBuffer offset:0 atIndex:1];
    [encoder drawPrimitives:MTLPrimitiveTypeLine
                vertexStart:0
                vertexCount:RenderState_GetVertexCount(state)];

    // --- Debug gizmo draws ---
    if (cli_is_debug_mode() && g_debugOrbitSphereBuffer &&
        g_debugFixationSphereBuffer) {
      Camera *cam = RenderState_GetCamera(state);
      float aspect = metalLayer.drawableSize.width /
                     MAX(metalLayer.drawableSize.height, 1.0f);
      simd_float4x4 view = camera_view_matrix(cam);
      simd_float4x4 proj = camera_perspective(70.0f * (float)M_PI / 180.0f,
                                              aspect, 0.1f, 100.0f);
      simd_float4x4 vp = simd_mul(proj, view);

      // Log camera state every 120 frames (~2 seconds at 60fps)
      if (g_debugFrameCounter % 120 == 0) {
        simd_float3 camPos = camera_orbit_position(cam);
        LOG_DEBUG("[Frame %d] Camera: zoom=%.3f center=(%.2f, %.2f, %.2f) "
                  "pos=(%.2f, %.2f, %.2f)",
                  g_debugFrameCounter, cam->zoom, cam->center.x, cam->center.y,
                  cam->center.z, camPos.x, camPos.y, camPos.z);
      }

      // 1) Orbit sphere (PINK): unit sphere scaled by zoom, at center
      {
        simd_float4x4 model = simd_mul(make_translation_matrix(cam->center),
                                       make_scale_matrix(cam->zoom));
        DisplacedMeshUniforms u;
        u.mvpMatrix = simd_mul(vp, model);
        u.gridColor = (simd_float4){1.0f, 0.41f, 0.71f, 0.7f}; // Hot pink

        [encoder setVertexBuffer:g_debugOrbitSphereBuffer offset:0 atIndex:0];
        [encoder setVertexBytes:&u length:sizeof(u) atIndex:1];
        [encoder setFragmentBytes:&u length:sizeof(u) atIndex:1];
        [encoder drawPrimitives:MTLPrimitiveTypeLine
                    vertexStart:0
                    vertexCount:g_debugOrbitSphereVertexCount];
      }

      // 2) Fixation point sphere (RED): small sphere at center
      {
        float fixationRadius = 0.15f; // Fixed small size
        simd_float4x4 model = simd_mul(make_translation_matrix(cam->center),
                                       make_scale_matrix(fixationRadius));
        DisplacedMeshUniforms u;
        u.mvpMatrix = simd_mul(vp, model);
        u.gridColor = (simd_float4){1.0f, 0.15f, 0.15f, 1.0f}; // Red

        [encoder setVertexBuffer:g_debugFixationSphereBuffer
                          offset:0
                         atIndex:0];
        [encoder setVertexBytes:&u length:sizeof(u) atIndex:1];
        [encoder setFragmentBytes:&u length:sizeof(u) atIndex:1];
        [encoder drawPrimitives:MTLPrimitiveTypeLine
                    vertexStart:0
                    vertexCount:g_debugFixationSphereVertexCount];
      }
    }

    [encoder endEncoding];

    [commandBuffer presentDrawable:drawable];
    [commandBuffer commit];
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

      if (!g_activeRenderState) {
        continue;
      }

      RenderState *state = g_activeRenderState;
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
