#import "celestial_bodies_culling_count.h"
#import "core/log/log.h"

#import "macos/debug/overlay.h"
#import "macos/render/state/render_state.h"

#import <stdio.h>
#import <stdlib.h>
#import <string.h>

#define MAX_BODY_TYPES 16

static CelestialBodyTypeEntry g_registered_types[MAX_BODY_TYPES];
static size_t g_registered_type_count = 0;
static bool g_registry_initialized = false;

static size_t get_stars_rendered(const RenderState *state) {
  return state ? RenderState_GetRenderedStarCount(state) : 0;
}

static size_t get_stars_loaded(const RenderState *state) {
  if (!state)
    return 0;
  DynamicArray *stars = RenderState_GetStars((RenderState *)state);
  return stars ? DynamicArray_length(stars) : 0;
}

static size_t get_planets_rendered(const RenderState *state) {
  return state ? RenderState_GetRenderedPlanetCount(state) : 0;
}

static size_t get_planets_loaded(const RenderState *state) {
  if (!state)
    return 0;
  DynamicArray *planets = RenderState_GetPlanets((RenderState *)state);
  return planets ? DynamicArray_length(planets) : 0;
}

static size_t get_moons_rendered(const RenderState *state) {
  return state ? RenderState_GetRenderedMoonCount(state) : 0;
}

static size_t get_moons_loaded(const RenderState *state) {
  if (!state)
    return 0;
  DynamicArray *moons = RenderState_GetMoons((RenderState *)state);
  return moons ? DynamicArray_length(moons) : 0;
}

bool debug_celestial_bodies_culling_register_type(
    const char *name, CelestialBodyCountGetter get_rendered,
    CelestialBodyCountGetter get_loaded) {
  if (!name || g_registered_type_count >= MAX_BODY_TYPES)
    return false;

  for (size_t i = 0; i < g_registered_type_count; i++) {
    if (strcmp(g_registered_types[i].name, name) == 0) {
      g_registered_types[i].get_rendered = get_rendered;
      g_registered_types[i].get_loaded = get_loaded;
      return true;
    }
  }

  CelestialBodyTypeEntry *entry =
      &g_registered_types[g_registered_type_count++];
  strncpy(entry->name, name, sizeof(entry->name) - 1);
  entry->name[sizeof(entry->name) - 1] = '\0';
  entry->get_rendered = get_rendered;
  entry->get_loaded = get_loaded;
  return true;
}

void debug_celestial_bodies_culling_init_registry(void) {
  if (g_registry_initialized)
    return;

  g_registered_type_count = 0;
  debug_celestial_bodies_culling_register_type("Stars", get_stars_rendered,
                                               get_stars_loaded);
  debug_celestial_bodies_culling_register_type("Planets", get_planets_rendered,
                                               get_planets_loaded);
  debug_celestial_bodies_culling_register_type("Moons", get_moons_rendered,
                                               get_moons_loaded);
  g_registry_initialized = true;
}

void debug_create_celestial_bodies_culling_overlay(RenderState *state) {
  debug_celestial_bodies_culling_init_registry();
  DebugOverlay *overlay = debug_overlay_create(RenderState_GetWindow(state));
  RenderState_SetCelestialBodiesOverlay(state, overlay);
}

static void format_count(size_t n, char *out, size_t out_len) {
  char temp[32];
  snprintf(temp, sizeof(temp), "%zu", n);
  size_t len = strlen(temp);
  size_t commas = (len > 0) ? (len - 1) / 3 : 0;
  if (len + commas + 1 > out_len) {
    snprintf(out, out_len, "%zu", n);
    return;
  }

  size_t j = len + commas;
  out[j--] = '\0';
  for (int i = (int)len - 1, count = 0; i >= 0; i--, count++) {
    if (count > 0 && count % 3 == 0)
      out[j--] = ',';
    out[j--] = temp[i];
  }
}

void debug_overlay_update_celestial_bodies_culling(DebugOverlay *overlay,
                                                   RenderState *state) {
  if (!overlay || !state)
    return;

  if (!debug_overlay_is_visible(overlay))
    return;

  debug_celestial_bodies_culling_init_registry();

  size_t total_rendered = 0;
  size_t total_loaded = 0;
  size_t field_count = 0;

  DebugOverlayField fields[MAX_BODY_TYPES + 1];

  for (size_t i = 0; i < g_registered_type_count; i++) {
    const CelestialBodyTypeEntry *entry = &g_registered_types[i];
    size_t rendered = entry->get_rendered ? entry->get_rendered(state) : 0;
    size_t loaded = entry->get_loaded ? entry->get_loaded(state) : 0;

    total_rendered += rendered;
    total_loaded += loaded;

    char rendered_str[32];
    char loaded_str[32];
    format_count(rendered, rendered_str, sizeof(rendered_str));
    format_count(loaded, loaded_str, sizeof(loaded_str));

    char val_buf[80];
    snprintf(val_buf, sizeof(val_buf), "%s / %s", rendered_str, loaded_str);

    fields[field_count].label = entry->name;
    fields[field_count].value = strdup(val_buf);
    field_count++;
  }

  char total_rendered_str[32];
  char total_loaded_str[32];
  format_count(total_rendered, total_rendered_str, sizeof(total_rendered_str));
  format_count(total_loaded, total_loaded_str, sizeof(total_loaded_str));
  char total_val_buf[80];
  snprintf(total_val_buf, sizeof(total_val_buf), "%s / %s", total_rendered_str,
           total_loaded_str);

  fields[field_count].label = "Total";
  fields[field_count].value = strdup(total_val_buf);
  field_count++;

  float panel_width = 240.0f;
  float panel_height = 36.0f + (float)field_count * 16.0f;

  float x = -(panel_width + 20.0f);
  float y = -(20.0f + panel_height);

  debug_overlay_add_panel(overlay, "Celestial Bodies", x, y, panel_width,
                          panel_height, 0.6f, fields, field_count);

  for (size_t i = 0; i < field_count; i++) {
    free((void *)fields[i].value);
    fields[i].value = NULL;
  }
}
