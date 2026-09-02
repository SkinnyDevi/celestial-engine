#ifndef MACOS_RENDER_HANDLER_H
#define MACOS_RENDER_HANDLER_H

#include "core/renderer/camera/camera.h"
#include <simd/simd.h>
#include <stdbool.h>

#ifndef __OBJC__
typedef void *NSWindow;
#endif

typedef struct {
  simd_float4x4 viewProjection;
} GridUniforms;

typedef struct RenderState RenderState;
typedef struct DebugOverlay DebugOverlay;

RenderState *RenderState_Create(void);
void RenderState_Init(RenderState *state, void *window);
void RenderState_Destroy(RenderState *state);

void *RenderState_GetWindow(RenderState *state);
void *RenderState_GetMetalLayer(RenderState *state);
void *RenderState_GetCommandQueue(RenderState *state);
void *RenderState_GetVec3Buffer(RenderState *state);
void *RenderState_GetUniformBuffer(RenderState *state);
void *RenderState_GetGridShaderLib(RenderState *state);
void *RenderState_GetPipelineState(RenderState *state);
DebugOverlay *RenderState_GetCameraDebugOverlay(RenderState *state);
Camera *RenderState_GetCamera(RenderState *state);

void RenderState_SetVec3Buffer(RenderState *state, void *buffer);
void RenderState_SetUniformBuffer(RenderState *state, void *buffer);
void RenderState_SetGridShaderLib(RenderState *state, void *library);
void RenderState_SetPipelineState(RenderState *state, void *pipelineState);
void RenderState_SetCameraDebugOverlay(RenderState *state,
                                       DebugOverlay *overlay);
void RenderState_SetVertexCount(RenderState *state, unsigned long count);
unsigned long RenderState_GetVertexCount(const RenderState *state);
void RenderState_SetDragging(RenderState *state, bool dragging);
bool RenderState_IsDragging(const RenderState *state);
void RenderState_SetLastMouse(RenderState *state, double x, double y);
void RenderState_GetLastMouse(const RenderState *state, double *x, double *y);

#endif