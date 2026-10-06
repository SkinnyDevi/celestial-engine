#ifndef MACOS_DEBUG_SCALE_BAR_H
#define MACOS_DEBUG_SCALE_BAR_H

#include "core/renderer/camera/camera.h"

void create_scale_bar(void *window);
void update_scale_bar(const Camera *camera, float screen_width,
                      float screen_height);
void destroy_scale_bar(void);

#endif
