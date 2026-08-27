#import "renderer.h"
#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>

typedef struct {
  NSWindow *window;
  CAMetalLayer *metalLayer;
  id<MTLCommandQueue> commandQueue;
} RenderState;

RendererHandle init_metal_window(int width, int height, const char *title) {
  // 1. Initialize Application
  [NSApplication sharedApplication];
  [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];

  // 2. Create Window
  NSRect frame = NSMakeRect(0, 0, width, height);
  NSWindow *window = [[NSWindow alloc]
      initWithContentRect:frame
                styleMask:(NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                           NSWindowStyleMaskResizable)
                  backing:NSBackingStoreBuffered
                    defer:NO];
  [window setTitle:[NSString stringWithUTF8String:title]];
  [window makeKeyAndOrderFront:nil];

  // 3. Setup Metal Layer
  CAMetalLayer *metalLayer = [CAMetalLayer layer];
  metalLayer.device = MTLCreateSystemDefaultDevice();
  metalLayer.pixelFormat = MTLPixelFormatBGRA8Unorm;

  [window.contentView setWantsLayer:YES];
  [window.contentView setLayer:metalLayer];

  // 4. Store state to return to C
  RenderState *state = (RenderState *)malloc(sizeof(RenderState));
  state->window = window;
  state->metalLayer = metalLayer;
  state->commandQueue = [metalLayer.device newCommandQueue];

  [NSApp finishLaunching];

  return (RendererHandle)state;
}

void draw_frame(RendererHandle handle) {
  RenderState *state = (RenderState *)handle;

  // The autoreleasepool is mandatory to prevent memory leaks every frame
  @autoreleasepool {
    id<CAMetalDrawable> drawable = [state->metalLayer nextDrawable];
    if (!drawable)
      return;

    id<MTLCommandBuffer> commandBuffer = [state->commandQueue commandBuffer];

    MTLRenderPassDescriptor *passDescriptor =
        [MTLRenderPassDescriptor renderPassDescriptor];
    passDescriptor.colorAttachments[0].texture = drawable.texture;
    passDescriptor.colorAttachments[0].loadAction = MTLLoadActionClear;
    passDescriptor.colorAttachments[0].clearColor =
        MTLClearColorMake(0.1, 0.2, 0.4, 1.0); // Dark blue background
    id<MTLRenderCommandEncoder> encoder =
        [commandBuffer renderCommandEncoderWithDescriptor:passDescriptor];
    // Shaders and drawing commands would go here
    [encoder endEncoding];

    [commandBuffer presentDrawable:drawable];
    [commandBuffer commit];
  }
}

// macOS requires the main thread to process window events
void pump_os_events(void) {
  @autoreleasepool {
    NSEvent *event;
    while ((event = [NSApp nextEventMatchingMask:NSEventMaskAny
                                       untilDate:nil
                                          inMode:NSDefaultRunLoopMode
                                         dequeue:YES])) {
      [NSApp sendEvent:event];
    }
  }
}
