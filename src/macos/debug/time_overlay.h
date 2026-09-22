#ifndef MACOS_DEBUG_TIME_OVERLAY
#define MACOS_DEBUG_TIME_OVERLAY

#include "core/space/astro_time.h"
#include "macos/debug/overlay.h"
#include "macos/render/state/render_handler.h"

void debug_create_time_overlay(RenderState *state);
void debug_overlay_update_time(DebugOverlay *overlay, AstronomicalTime *time);

#endif