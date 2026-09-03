#ifndef MACOS_DEBUG_CAMERA_PROPERTIES_H
#define MACOS_DEBUG_CAMERA_PROPERTIES_H

#include "core/renderer/camera/camera.h"
#include "macos/debug/overlay.h"
#include "macos/render/state/render_handler.h"

void debug_create_camera_properties_overlay(RenderState *state);
void debug_overlay_update_camera(DebugOverlay *overlay, const Camera *camera);

#endif