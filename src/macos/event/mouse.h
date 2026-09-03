#ifndef MACOS_WINDOW_EVENT_MOUSE_H
#define MACOS_WINDOW_EVENT_MOUSE_H

#include "macos/render/state/render_handler.h"
#include <stdbool.h>

typedef struct {
  double x;
  double y;
} MousePoint;

void event_left_mouse_down(RenderState *state, MousePoint mouse);
void event_left_mouse_drag(RenderState *state, MousePoint mouse,
                           bool shiftHeld);

#endif