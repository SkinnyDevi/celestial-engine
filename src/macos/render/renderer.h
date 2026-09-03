#ifndef MACOS_RENDERER_H
#define MACOS_RENDERER_H

typedef void *RendererHandle;

RendererHandle init_metal_window(int width, int height, const char *title);
void draw_frame(RendererHandle handle);
void pump_os_events(void);

#endif
