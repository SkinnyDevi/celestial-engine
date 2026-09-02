#ifndef MACOS_DEBUG_OVERLAY_H
#define MACOS_DEBUG_OVERLAY_H

#include "core/renderer/camera/camera.h"
#include <stdbool.h>
#include <stddef.h>

typedef struct {
  const char *label;
  const char *value;
} DebugOverlayField;

typedef struct DebugOverlay DebugOverlay;

DebugOverlay *debug_overlay_create(void *window);
void debug_overlay_destroy(DebugOverlay *overlay);
void debug_overlay_clear(DebugOverlay *overlay);
void debug_overlay_add_panel(DebugOverlay *overlay, const char *title, float x,
                             float y, float width, float height, float alpha,
                             const DebugOverlayField *fields,
                             size_t fieldCount);
void debug_overlay_set_visible(DebugOverlay *overlay, bool visible);
bool debug_overlay_is_visible(const DebugOverlay *overlay);

#endif
