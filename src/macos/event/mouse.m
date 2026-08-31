#import "mouse.h"

void event_left_mouse_down(RenderState *state, MousePoint mouse) {
  RenderState_SetDragging(state, true);
  RenderState_SetLastMouse(state, mouse.x, mouse.y);
}

void event_left_mouse_drag(RenderState *state, MousePoint current, bool shiftHeld) {
  double lastX = 0.0;
  double lastY = 0.0;
  RenderState_GetLastMouse(state, &lastX, &lastY);

  double dx = current.x - lastX;
  double dy = current.y - lastY;
  RenderState_SetLastMouse(state, current.x, current.y);

  Camera *camera = RenderState_GetCamera(state);
  if (shiftHeld) {
    camera_pan_from_input(camera, (float)dx, (float)dy);
  } else {
    camera_orbit_from_input(camera, (float)dx, (float)dy);
  }
}