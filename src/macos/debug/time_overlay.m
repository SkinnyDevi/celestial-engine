#import "time_overlay.h"
#include "core/space/astro_time.h"
#import <Foundation/NSObjCRuntime.h>
#import <stdio.h>
#import <stdlib.h>
#import <string.h>
#include <time.h>

#import "macos/debug/overlay.h"
#import "macos/render/state/render_handler.h"

void debug_create_time_overlay(RenderState *state) {
  DebugOverlay *overlay = debug_overlay_create(RenderState_GetWindow(state));
  RenderState_SetTimeOverlay(state, overlay);
}

void debug_overlay_update_time(DebugOverlay *overlay, AstronomicalTime *time) {
  if (!overlay || !time)
    return;

  if (!debug_overlay_is_visible(overlay))
    return;

  int year, month, day, hour, minute, second;
  jd_to_gregorian(time->current_jd, &year, &month, &day, &hour, &minute, &second);

  char date_buffer[32];
  char time_buffer[32];
  char jd_buffer[32];

  snprintf(date_buffer, sizeof(date_buffer), "%04d-%02d-%02d", year, month, day);
  snprintf(time_buffer, sizeof(time_buffer), "%02d:%02d:%02d", hour, minute, second);
  snprintf(jd_buffer, sizeof(jd_buffer), "%.2f", time->current_jd);

  DebugOverlayField fields[] = {
      {"Date", date_buffer}, {"Time", time_buffer}, {"Julian Day", jd_buffer}};

  debug_overlay_add_panel(overlay, "Time", 20.0f, -180.0f, 200.0f, 85.0f, 0.6f,
                          fields, 3);
}