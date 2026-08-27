#ifndef APP_RENDERER_H
#define APP_RENDERER_H

enum RenderingEngine { Metal, Vulkan };
typedef enum RenderingEngine RenderingEngine;

void render_with(RenderingEngine engine);

#endif
