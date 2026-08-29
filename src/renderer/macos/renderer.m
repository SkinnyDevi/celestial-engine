#import "renderer.h"
#import "../../cli/functions.h"
#import "debug/debug_overlay.h"
#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>

static RenderState *g_activeRenderState = NULL;

static NSString *const kGridShaderSource =
    @"#include <metal_stdlib>\n"
     "using namespace metal;\n"
     "struct VertexIn { float3 pos [[attribute(0)]]; };\n"
     "struct GridUniforms { float4x4 viewProjection; };\n"
     "struct VertexOut { float4 pos [[position]]; };\n"
     "vertex VertexOut vertex_main(VertexIn in [[stage_in]], "
     "constant GridUniforms &uniforms [[buffer(1)]]) {\n"
     "  VertexOut out;\n"
     "  out.pos = uniforms.viewProjection * float4(in.pos, 1.0);\n"
     "  return out;\n"
     "}\n"
     "fragment float4 fragment_main() { return float4(0.75, 0.82, 1.0, 1.0); "
     "}\n";

static void update_camera_uniforms(RenderState *state) {
  if (!state || !RenderState_GetUniformBuffer(state)) {
    return;
  }

  Camera *camera = RenderState_GetCamera(state);
  simd_float3 eye = camera_orbit_position(camera);

  CAMetalLayer *metalLayer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);
  float aspect =
      metalLayer.drawableSize.width / MAX(metalLayer.drawableSize.height, 1.0f);
  simd_float4x4 view =
      camera_look_at(eye, camera->center, simd_make_float3(0.0f, 1.0f, 0.0f));
  simd_float4x4 projection =
      camera_perspective(70.0f * (float)M_PI / 180.0f, aspect, 0.1f, 100.0f);

  GridUniforms uniforms = {simd_mul(projection, view)};
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

  NSError *error = nil;
  MTLCompileOptions *options = [MTLCompileOptions new];
  id<MTLLibrary> shaderLibrary =
      [metalLayer.device newLibraryWithSource:kGridShaderSource
                                      options:options
                                        error:&error];
  if (error) {
    NSLog(@"Error creating shader library: %@", error);
    RenderState_Destroy(state);
    return NULL;
  }
  RenderState_SetShaderLibrary(state, (__bridge void *)shaderLibrary);

  build_grid_mesh(state);
  id<MTLBuffer> uniformBuffer =
      [metalLayer.device newBufferWithLength:sizeof(GridUniforms)
                                     options:MTLResourceStorageModeShared];
  RenderState_SetUniformBuffer(state, (__bridge void *)uniformBuffer);

  MTLRenderPipelineDescriptor *pipelineDescriptor =
      [[MTLRenderPipelineDescriptor alloc] init];
  MTLVertexDescriptor *vertexDescriptor =
      [MTLVertexDescriptor vertexDescriptor];
  vertexDescriptor.attributes[0].format = MTLVertexFormatFloat3;
  vertexDescriptor.attributes[0].offset = 0;
  vertexDescriptor.attributes[0].bufferIndex = 0;
  vertexDescriptor.layouts[0].stride = sizeof(Vec3);
  vertexDescriptor.layouts[0].stepRate = 1;
  vertexDescriptor.layouts[0].stepFunction = MTLVertexStepFunctionPerVertex;

  pipelineDescriptor.vertexFunction =
      [shaderLibrary newFunctionWithName:@"vertex_main"];
  pipelineDescriptor.fragmentFunction =
      [shaderLibrary newFunctionWithName:@"fragment_main"];
  pipelineDescriptor.vertexDescriptor = vertexDescriptor;
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
  }

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
    [encoder setVertexBuffer:vertexBuffer offset:0 atIndex:0];
    [encoder setVertexBuffer:uniformBuffer offset:0 atIndex:1];
    [encoder drawPrimitives:MTLPrimitiveTypeLine
                vertexStart:0
                vertexCount:RenderState_GetVertexCount(state)];
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
        event_left_mouse_drag(state, point);
      } else if ([event type] == NSEventTypeLeftMouseUp) {
        RenderState_SetDragging(state, false);
      } else if ([event type] == NSEventTypeScrollWheel) {
        Camera *camera = RenderState_GetCamera(state);
        camera_update_from_input(camera, 0.0f, 0.0f,
                                 (float)[event scrollingDeltaY]);
      }
    }
  }
}
