#import "fps_counter.h"
#include "core/log/log.h"
#import <Foundation/NSObjCRuntime.h>
#import <stdio.h>
#import <stdlib.h>
#import <string.h>
#import <time.h>

#import "macos/debug/overlay.h"
#import "macos/render/state/render_handler.h"

#define FPS_AVG_ENTRIES 64

static FPSData fps_data = {.last_frame_time_nanos = 0, .frame_count = 0};
static double fps_entries[FPS_AVG_ENTRIES] = {0};
static int fps_entry_index = 0;
static int fps_entries_size = 0;

struct timespec current_time;
static struct timespec last_frame_time;

void debug_create_fps_counter_overlay(RenderState *state) {
  DebugOverlay *overlay = debug_overlay_create(RenderState_GetWindow(state));
  RenderState_SetFPSCounterOverlay(state, overlay);

  fps_data.last_frame_time_nanos = 0;
  fps_data.frame_count = 0;
  fps_data.fps_avg = 0;
  fps_entry_index = 0;

  for (size_t i = 0; i < FPS_AVG_ENTRIES; i++)
    fps_entries[i] = 0;
}

void add_fps_entry(double fps) {
  fps_entries[fps_entry_index] = fps;
  fps_entry_index = (fps_entry_index + 1) % FPS_AVG_ENTRIES;
  fps_entries_size = MIN(fps_entries_size + 1, FPS_AVG_ENTRIES);
}

void count_fps() {
  clock_gettime(CLOCK_MONOTONIC, &current_time);
  uint64_t current_frame_time_nanos =
      (current_time.tv_sec - last_frame_time.tv_sec) * 1e9 +
      (current_time.tv_nsec - last_frame_time.tv_nsec);

  fps_data.frame_count++;
  fps_data.last_frame_time_nanos = current_frame_time_nanos;
  fps_data.fps = 1.0f / (current_frame_time_nanos / 1e9f);
  add_fps_entry(fps_data.fps);

  last_frame_time = current_time;
}

void get_fps_avg() {
  double total_fps = 0;
  for (int i = 0; i < fps_entries_size; i++)
    total_fps += fps_entries[i];

  fps_data.fps_avg = total_fps / fps_entries_size;
}

void debug_overlay_update_fps(DebugOverlay *overlay, bool use_extended_data,
                              FPSData *out_data) {
  if (!overlay)
    return;

  if (!debug_overlay_is_visible(overlay))
    return;

  count_fps();
  get_fps_avg();

  DebugOverlayField fps_fields[] = {{"FPS", ""}};
  DebugOverlayField extended_fps_fields[] = {
      {"Current frame", ""}, {"FPS", ""}, {"Current frame time", ""}};

  char fps_buffer[32];
  char current_frame_buffer[32];
  char current_frame_time_buffer[32];

  if (use_extended_data) {
    snprintf(fps_buffer, sizeof(fps_buffer), "%lf", fps_data.fps);
    snprintf(current_frame_buffer, sizeof(current_frame_buffer), "%llu",
             fps_data.frame_count);
    snprintf(current_frame_time_buffer, sizeof(current_frame_time_buffer),
             "%llu", fps_data.last_frame_time_nanos);
    extended_fps_fields[0].value = strdup(current_frame_buffer);
    extended_fps_fields[1].value = strdup(fps_buffer);
    extended_fps_fields[2].value = strdup(current_frame_time_buffer);
    debug_overlay_add_panel(overlay, "FPS Counter", 20.0f, -80.0f, 200.0f,
                            75.0f, 0.5f, extended_fps_fields, 3);

    for (size_t i = 0; i < 3; i++) {
      free((void *)extended_fps_fields[i].value);
      extended_fps_fields[i].value = NULL;
    }
  } else {
    snprintf(fps_buffer, sizeof(fps_buffer), "%0.2f", fps_data.fps_avg);
    fps_fields[0].value = strdup(fps_buffer);
    debug_overlay_add_panel(overlay, "FPS Counter", 20.0f, -60.0f, 90.0f, 40.0f,
                            0.5f, fps_fields, 1);

    free((void *)fps_fields[0].value);
    fps_fields[0].value = NULL;
  }

  memcpy(out_data, &fps_data, sizeof(FPSData));
}