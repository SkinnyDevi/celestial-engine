#ifndef MACOS_RENDER_CAMERA_CAMERA_H
#define MACOS_RENDER_CAMERA_CAMERA_H

#include "core/renderer/camera/camera.h"
#include "macos/render/state/render_state.h"

void update_camera_uniforms(RenderState *state);
void camera_follow_body(RenderState *state);

#endif // MACOS_RENDER_CAMERA_CAMERA_H