#ifndef MACOS_RENDER_CAMERA_CAMERA_H
#define MACOS_RENDER_CAMERA_CAMERA_H

#include "core/renderer/camera/camera.h"
#include "macos/render/state/render_state.h"

static const float kOrbitSensitivity = 0.007f;
static const float kMaxElevation = M_PI / 2.0f; // 90 degree clamp
static const float kZoomFactor = 1.05f;
static const float kMinzoom = 0.01f;
static const float kMaxzoom = 1e10f;

void update_camera_uniforms(RenderState *state);
void camera_follow_body(RenderState *state);

#endif // MACOS_RENDER_CAMERA_CAMERA_H