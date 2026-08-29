#import "render_handler.h"
#import "debug/debug_overlay.h"
#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>

typedef struct {
  NSWindow *window;
  CAMetalLayer *metalLayer;
  id<MTLCommandQueue> commandQueue;
  id<MTLBuffer> vec3Buffer;
  id<MTLBuffer> uniformBuffer;
  id<MTLLibrary> shaderLibrary;
  id<MTLRenderPipelineState> pipelineState;
  DebugOverlay *debugOverlay;
  Camera camera;
  bool dragging;
  NSPoint lastMouse;
  NSUInteger gridVertexCount;
} RenderStateImpl;

RenderState *RenderState_Create(void) {
  RenderStateImpl *impl = calloc(1, sizeof(RenderStateImpl));
  if (!impl) {
    return NULL;
  }

  impl->dragging = false;
  impl->lastMouse = NSZeroPoint;
  impl->gridVertexCount = 0;
  impl->window = nil;
  impl->metalLayer = nil;
  impl->commandQueue = nil;
  impl->vec3Buffer = nil;
  impl->uniformBuffer = nil;
  impl->shaderLibrary = nil;
  impl->pipelineState = nil;
  impl->debugOverlay = nil;
  camera_init(&impl->camera);

  return (RenderState *)impl;
}

void RenderState_Init(RenderState *state, void *window) {
  if (!state || !window) {
    return;
  }

  RenderStateImpl *impl = (RenderStateImpl *)state;
  impl->window = (__bridge NSWindow *)window;
  impl->metalLayer = [CAMetalLayer layer];
  impl->metalLayer.device = MTLCreateSystemDefaultDevice();
  impl->metalLayer.pixelFormat = MTLPixelFormatBGRA8Unorm;
  impl->metalLayer.framebufferOnly = YES;
  [impl->window.contentView.layer addSublayer:impl->metalLayer];

  impl->commandQueue = [impl->metalLayer.device newCommandQueue];
  impl->shaderLibrary = [impl->metalLayer.device newDefaultLibrary];
  impl->debugOverlay = NULL;
  camera_init(&impl->camera);
  impl->dragging = false;
  impl->lastMouse = NSZeroPoint;
  impl->gridVertexCount = 0;
}

void RenderState_Destroy(RenderState *state) {
  if (!state) {
    return;
  }

  RenderStateImpl *impl = (RenderStateImpl *)state;
  impl->vec3Buffer = nil;
  impl->uniformBuffer = nil;
  impl->shaderLibrary = nil;
  impl->pipelineState = nil;
  impl->commandQueue = nil;
  impl->metalLayer = nil;
  impl->window = nil;
  debug_overlay_destroy(impl->debugOverlay);
  impl->debugOverlay = nil;
  free(state);
}

void *RenderState_GetWindow(RenderState *state) {
  if (!state) {
    return NULL;
  }

  return (__bridge void *)((RenderStateImpl *)state)->window;
}

void *RenderState_GetMetalLayer(RenderState *state) {
  if (!state) {
    return NULL;
  }

  return (__bridge void *)((RenderStateImpl *)state)->metalLayer;
}

void *RenderState_GetCommandQueue(RenderState *state) {
  if (!state) {
    return NULL;
  }

  return (__bridge void *)((RenderStateImpl *)state)->commandQueue;
}

void *RenderState_GetVec3Buffer(RenderState *state) {
  if (!state) {
    return NULL;
  }

  return (__bridge void *)((RenderStateImpl *)state)->vec3Buffer;
}

void *RenderState_GetUniformBuffer(RenderState *state) {
  if (!state) {
    return NULL;
  }

  return (__bridge void *)((RenderStateImpl *)state)->uniformBuffer;
}

void *RenderState_GetShaderLibrary(RenderState *state) {
  if (!state) {
    return NULL;
  }

  return (__bridge void *)((RenderStateImpl *)state)->shaderLibrary;
}

void *RenderState_GetPipelineState(RenderState *state) {
  if (!state) {
    return NULL;
  }

  return (__bridge void *)((RenderStateImpl *)state)->pipelineState;
}

DebugOverlay *RenderState_GetDebugOverlay(RenderState *state) {
  if (!state) {
    return NULL;
  }

  return ((RenderStateImpl *)state)->debugOverlay;
}

Camera *RenderState_GetCamera(RenderState *state) {
  if (!state) {
    return NULL;
  }

  return &((RenderStateImpl *)state)->camera;
}

void RenderState_SetVec3Buffer(RenderState *state, void *buffer) {
  if (!state) {
    return;
  }

  ((RenderStateImpl *)state)->vec3Buffer = (__bridge id<MTLBuffer>)buffer;
}

void RenderState_SetUniformBuffer(RenderState *state, void *buffer) {
  if (!state) {
    return;
  }

  ((RenderStateImpl *)state)->uniformBuffer = (__bridge id<MTLBuffer>)buffer;
}

void RenderState_SetShaderLibrary(RenderState *state, void *library) {
  if (!state) {
    return;
  }

  ((RenderStateImpl *)state)->shaderLibrary = (__bridge id<MTLLibrary>)library;
}

void RenderState_SetPipelineState(RenderState *state, void *pipelineState) {
  if (!state) {
    return;
  }

  ((RenderStateImpl *)state)->pipelineState =
      (__bridge id<MTLRenderPipelineState>)pipelineState;
}

void RenderState_SetDebugOverlay(RenderState *state, DebugOverlay *overlay) {
  if (!state) {
    return;
  }

  ((RenderStateImpl *)state)->debugOverlay = overlay;
}

void RenderState_SetVertexCount(RenderState *state, unsigned long count) {
  if (!state) {
    return;
  }

  ((RenderStateImpl *)state)->gridVertexCount = (NSUInteger)count;
}

unsigned long RenderState_GetVertexCount(const RenderState *state) {
  if (!state) {
    return 0;
  }

  return (unsigned long)((const RenderStateImpl *)state)->gridVertexCount;
}

void RenderState_SetDragging(RenderState *state, bool dragging) {
  if (!state) {
    return;
  }

  ((RenderStateImpl *)state)->dragging = dragging;
}

bool RenderState_IsDragging(const RenderState *state) {
  if (!state) {
    return false;
  }

  return ((const RenderStateImpl *)state)->dragging;
}

void RenderState_SetLastMouse(RenderState *state, double x, double y) {
  if (!state) {
    return;
  }

  ((RenderStateImpl *)state)->lastMouse = NSMakePoint(x, y);
}

void RenderState_GetLastMouse(const RenderState *state, double *x, double *y) {
  if (!state || !x || !y) {
    return;
  }

  *x = ((const RenderStateImpl *)state)->lastMouse.x;
  *y = ((const RenderStateImpl *)state)->lastMouse.y;
}