#ifndef MACOS_RENDERER_H
#define MACOS_RENDERER_H

#include "../../cli/functions.h"
#include "../../core/log/log.h"
#include "../../spatial/spatial.h"
#include "../camera/camera.h"
#include "debug/debug_gizmos.h"
#include "debug/debug_overlay.h"
#include "event/mouse.h"
#include "grid/displaced_mesh.h"
#include "grid/spatial_grid.h"
#include "render_handler.h"

// Renderer state handler
typedef void *RendererHandle;

RendererHandle init_metal_window(int width, int height, const char *title);
void draw_frame(RendererHandle handle);
void pump_os_events(void);

#endif
