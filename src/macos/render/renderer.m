#import "renderer.h"
#import <AppKit/AppKit.h>
#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <mach/mach_time.h>

#import "core/cli/functions.h"
#import "core/cli/instance_data.h"
#import "core/data/dyn_array.h"
#import "core/data/math.h"
#import "core/data/raycast.h"
#import "core/log/log.h"
#import "core/space/astro_time.h"
#import "core/space/orbit.h"
#import "core/space/units.h"

#import "macos/debug/camera_properties.h"
#import "macos/debug/flags.h"
#import "macos/debug/fps_counter.h"
#import "macos/debug/graphics.h"
#import "macos/debug/sphere_wireframe.h"
#import "macos/debug/time_overlay.h"

#import "macos/event/input_registry.h"
#import "macos/event/mouse.h"

#import "macos/render/camera/camera.h"
#import "macos/render/grid/displaced_mesh.h"
#import "macos/render/scale_bar/scale_bar.h"
#import "macos/render/space/graphics.h"
#import "macos/render/space/moon.h"
#import "macos/render/space/planet.h"
#import "macos/render/space/star.h"
#import "macos/render/state/render_state.h"
#import "macos/shaders/shader_loader.h"

static RenderState *app_render_state = NULL;

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

  // Enable alpha blending
  pipeline_descriptor.colorAttachments[0].blendingEnabled = YES;
  pipeline_descriptor.colorAttachments[0].rgbBlendOperation =
      MTLBlendOperationAdd;
  pipeline_descriptor.colorAttachments[0].alphaBlendOperation =
      MTLBlendOperationAdd;
  pipeline_descriptor.colorAttachments[0].sourceRGBBlendFactor =
      MTLBlendFactorSourceAlpha;
  pipeline_descriptor.colorAttachments[0].sourceAlphaBlendFactor =
      MTLBlendFactorSourceAlpha;
  pipeline_descriptor.colorAttachments[0].destinationRGBBlendFactor =
      MTLBlendFactorOneMinusSourceAlpha;
  pipeline_descriptor.colorAttachments[0].destinationAlphaBlendFactor =
      MTLBlendFactorOneMinusSourceAlpha;

  pipeline_descriptor.depthAttachmentPixelFormat = MTLPixelFormatDepth32Float;

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

  MTLDepthStencilDescriptor *depth_descriptor =
      [[MTLDepthStencilDescriptor alloc] init];
  depth_descriptor.depthCompareFunction = MTLCompareFunctionLess;
  depth_descriptor.depthWriteEnabled = YES;
  id<MTLDepthStencilState> depth_state =
      [metal_layer.device newDepthStencilStateWithDescriptor:depth_descriptor];
  RenderState_SetDepthStencilState(state, (__bridge void *)depth_state);
}

/*
 * Depth texture is used to keep track of the depth of different pixels
 * to draw them in the correct order
 */
void handle_depth_texture(RenderState *state, CAMetalLayer *metal_layer) {
  CGSize drawableSize = metal_layer.drawableSize;
  id<MTLTexture> currentDepth =
      (__bridge id<MTLTexture>)RenderState_GetDepthTexture(state);

  if (!currentDepth || currentDepth.width != (NSUInteger)drawableSize.width ||
      currentDepth.height != (NSUInteger)drawableSize.height) {
    if (drawableSize.width > 0 && drawableSize.height > 0) {
      MTLTextureDescriptor *depthDescriptor = [MTLTextureDescriptor
          texture2DDescriptorWithPixelFormat:MTLPixelFormatDepth32Float
                                       width:drawableSize.width
                                      height:drawableSize.height
                                   mipmapped:NO];
      depthDescriptor.storageMode = MTLStorageModePrivate;
      depthDescriptor.usage = MTLTextureUsageRenderTarget;
      id<MTLTexture> newDepth =
          [metal_layer.device newTextureWithDescriptor:depthDescriptor];
      RenderState_SetDepthTexture(state, (__bridge void *)newDepth);
      currentDepth = newDepth;
    }
  }
}

MTLRenderPassDescriptor *
create_render_pass_descriptor(RenderState *state,
                              id<CAMetalDrawable> drawable) {
  if (!drawable)
    return nil;

  MTLRenderPassDescriptor *pass_descriptor =
      [MTLRenderPassDescriptor renderPassDescriptor];
  pass_descriptor.colorAttachments[0].texture = drawable.texture;
  pass_descriptor.colorAttachments[0].loadAction = MTLLoadActionClear;
  pass_descriptor.colorAttachments[0].clearColor =
      MTLClearColorMake(0.0, 0.0, 0.0, 1.0); // BG Color

  id<MTLTexture> currentDepth =
      (__bridge id<MTLTexture>)RenderState_GetDepthTexture(state);
  if (currentDepth) {
    pass_descriptor.depthAttachment.texture = currentDepth;
    pass_descriptor.depthAttachment.loadAction = MTLLoadActionClear;
    pass_descriptor.depthAttachment.storeAction = MTLStoreActionDontCare;
    pass_descriptor.depthAttachment.clearDepth = 1.0;
  }

  return pass_descriptor;
}

void update_celestial_bodies_position(RenderState *state, double days) {
  DynamicArray *planets = RenderState_GetPlanets(state);
  for (size_t i = 0; i < DynamicArray_length(planets); i++) {
    MTLPlanetGraphicsClass *planet;
    DynamicArray_get(planets, i, &planet);
    if (planet->body->orbit)
      planet->body->position =
          orbit_calculate_position(planet->body->orbit, days);
  }

  DynamicArray *moons = RenderState_GetMoons(state);
  for (size_t i = 0; i < DynamicArray_length(moons); i++) {
    MTLMoonGraphicsClass *moon;
    DynamicArray_get(moons, i, &moon);
    if (moon->body->orbit) {
      moon->body->position = orbit_calculate_position(moon->body->orbit, days);
    }
  }
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
  if (!state)
    return NULL;

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

  init_grid_mesh(state, 10, 0.2f);
  compile_grid_shader_lib(state, "displaced_grid_mesh");

  id<MTLBuffer> uniform_buffer =
      [metal_layer.device newBufferWithLength:sizeof(DisplacedMeshUniforms)
                                      options:MTLResourceStorageModeShared];
  RenderState_SetUniformBuffer(state, (__bridge void *)uniform_buffer);

  create_render_pipeline(state);
  generate_debug_graphics(state);
  init_celestial_bodies(state);
  create_scale_bar((__bridge void *)window);

  AstronomicalTime *sim_time = RenderState_GetSimTime(state);
  astro_time_from_cli_args(sim_time, cli_get_sim_date());
  RenderState_SetSimTime(state, sim_time);

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

void draw_celestial_bodies(RenderState *state,
                           id<MTLRenderCommandEncoder> encoder) {
  DynamicArray *stars = RenderState_GetStars(state);
  size_t star_count = DynamicArray_length(stars);
  for (size_t i = 0; i < star_count; i++) {
    MTLStarGraphicsClass *star;
    DynamicArray_get(stars, i, &star);
    MTLStarGraphicsClass_draw(star, state, (__bridge void *)encoder);
  }

  DynamicArray *planets = RenderState_GetPlanets(state);
  size_t planet_count = DynamicArray_length(planets);
  for (size_t i = 0; i < planet_count; i++) {
    MTLPlanetGraphicsClass *planet;
    DynamicArray_get(planets, i, &planet);
    MTLPlanetGraphicsClass_draw(planet, state, (__bridge void *)encoder);
  }

  DynamicArray *moons = RenderState_GetMoons(state);
  size_t moon_count = DynamicArray_length(moons);
  for (size_t i = 0; i < moon_count; i++) {
    MTLMoonGraphicsClass *moon;
    DynamicArray_get(moons, i, &moon);
    MTLMoonGraphicsClass_draw(moon, state, (__bridge void *)encoder);
  }
}

void draw_frame(RendererHandle handle) {
  RenderState *state = (RenderState *)handle;
  if (!state || !RenderState_GetPipelineState(state))
    return;

  static uint64_t last_time = 0;
  uint64_t current_time = mach_absolute_time();
  if (last_time != 0) {
    mach_timebase_info_data_t timebase;
    mach_timebase_info(&timebase);
    float dt = (float)(current_time - last_time) * (float)timebase.numer /
               (float)timebase.denom / 1e9f;

    Camera *cam = RenderState_GetCamera(state);
    if (cam->is_transitioning)
      camera_update_transition(cam, dt);

    AstronomicalTime *sim_time = RenderState_GetSimTime(state);
    astro_time_update(sim_time, dt);

    double days = astro_time_get_days_since_epoch(sim_time);

    update_celestial_bodies_position(state, days);

    if (RenderState_IsFollowing(state))
      camera_follow_body(state);
  }
  last_time = current_time;

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

    handle_depth_texture(state, metal_layer);
    MTLRenderPassDescriptor *pass_descriptor =
        create_render_pass_descriptor(state, drawable);

    id<MTLRenderCommandEncoder> encoder =
        [command_buffer renderCommandEncoderWithDescriptor:pass_descriptor];
    [encoder setRenderPipelineState:pipeline_state];

    id<MTLDepthStencilState> depthState =
        (__bridge id<MTLDepthStencilState>)RenderState_GetDepthStencilState(
            state);
    if (depthState)
      [encoder setDepthStencilState:depthState];

    update_grid_scale(state);
    draw_grid(state, (__bridge void *)encoder);
    draw_debug_graphics(state, (__bridge void *)(encoder));
    draw_celestial_bodies(state, encoder);
    update_scale_bar(RenderState_GetCamera(state),
                     metal_layer.drawableSize.width,
                     metal_layer.drawableSize.height);

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
      input_update_held_keys(RenderState_GetInputRegistry(state), state);

      // Key down and key up events should only be processed if they are not
      // repeats
      if ([event type] == NSEventTypeKeyDown && ![event isARepeat]) {
        input_process_key_down(RenderState_GetInputRegistry(state), state,
                               [event keyCode]);
      } else if ([event type] == NSEventTypeKeyUp) {
        input_process_key_up(RenderState_GetInputRegistry(state), state,
                             [event keyCode]);
      }

      if ([event type] == NSEventTypeLeftMouseDown) {
        NSPoint mouse = [event locationInWindow];
        MousePoint point = {mouse.x, mouse.y};
        bool shiftHeld =
            ([event modifierFlags] & NSEventModifierFlagShift) != 0;
        if ([event clickCount] == 2)
          event_mouse_double_click(state, point);
        else
          event_left_mouse_down(state, point, shiftHeld);

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