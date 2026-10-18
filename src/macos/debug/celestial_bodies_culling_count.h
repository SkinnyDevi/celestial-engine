#ifndef MACOS_DEBUG_CELESTIAL_BODIES_CULLING_COUNT_H
#define MACOS_DEBUG_CELESTIAL_BODIES_CULLING_COUNT_H

#include "macos/debug/overlay.h"
#include "macos/render/state/render_state.h"

#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef size_t (*CelestialBodyCountGetter)(const RenderState *state);

typedef struct {
  char name[32];
  CelestialBodyCountGetter get_rendered;
  CelestialBodyCountGetter get_loaded;
} CelestialBodyTypeEntry;

void debug_create_celestial_bodies_culling_overlay(RenderState *state);
void debug_overlay_update_celestial_bodies_culling(DebugOverlay *overlay,
                                                   RenderState *state);

bool debug_celestial_bodies_culling_register_type(
    const char *name, CelestialBodyCountGetter get_rendered,
    CelestialBodyCountGetter get_loaded);
void debug_celestial_bodies_culling_init_registry(void);
void debug_overlay_celestial_bodies_culling_log_count(DebugOverlay *overlay,
                                                      RenderState *state);

#ifdef __cplusplus
}
#endif

#endif // MACOS_DEBUG_CELESTIAL_BODIES_H
