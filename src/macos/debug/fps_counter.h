#ifndef MACOS_DEBUG_FPS_COUNTER
#define MACOS_DEBUG_FPS_COUNTER

#include "macos/debug/overlay.h"
#include "macos/render/state/render_handler.h"

typedef struct {
  unsigned long long last_frame_time_nanos;
  unsigned long long frame_count;
  double current_frame_time_s;
  double fps;
  double fps_avg;
} FPSData;

void debug_create_fps_counter_overlay(RenderState *state);
void debug_overlay_update_fps(DebugOverlay *overlay, bool use_extended_data,
                              FPSData *out_data);

#endif