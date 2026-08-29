#ifndef MACOS_RENDERER_H
#define MACOS_RENDERER_H

#include "render_handler.h"
#include "grid/spatial_grid.h"
#include "../camera/camera.h"
#include "../../spatial/spatial.h"
#include "event/mouse.h"

// Renderer state handler
typedef void *RendererHandle;

// C functions declared from objective C
RendererHandle init_metal_window(int width, int height, const char *title);
void draw_frame(RendererHandle handle);
void pump_os_events(void);

#endif
