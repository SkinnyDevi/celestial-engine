#import "camera_properties.h"
#import <stdio.h>
#import <stdlib.h>
#import <string.h>

#import "core/renderer/camera/camera.h"

void debug_create_camera_properties_overlay(RenderState *state) {
  DebugOverlay *overlay = debug_overlay_create(RenderState_GetWindow(state));
  RenderState_SetCameraDebugOverlay(state, overlay);
  debug_overlay_update_camera(overlay, RenderState_GetCamera(state));
}

void debug_overlay_update_camera(DebugOverlay *overlay, const Camera *camera) {
  if (!overlay || !camera)
    return;

  if (!debug_overlay_is_visible(overlay))
    return;

  DebugOverlayField cameraFields[] = {
      {"azimuth", ""}, {"elevation", ""}, {"zoom", ""},
      {"center", ""},  {"position", ""},
  };

  char azBuf[32];
  char elBuf[32];
  char distBuf[32];
  char centerBuf[64];
  char posBuf[64];

  simd_float3 pos = camera_orbit_position(camera);

  snprintf(azBuf, sizeof(azBuf), "%0.3f", camera->azimuth);
  snprintf(elBuf, sizeof(elBuf), "%0.3f", camera->elevation);
  snprintf(distBuf, sizeof(distBuf), "%0.3f", camera->zoom);
  snprintf(centerBuf, sizeof(centerBuf), "(%0.2f, %0.2f, %0.2f)",
           camera->center.x, camera->center.y, camera->center.z);
  snprintf(posBuf, sizeof(posBuf), "(%0.2f, %0.2f, %0.2f)", pos.x, pos.y,
           pos.z);

  cameraFields[0].value = strdup(azBuf);
  cameraFields[1].value = strdup(elBuf);
  cameraFields[2].value = strdup(distBuf);
  cameraFields[3].value = strdup(centerBuf);
  cameraFields[4].value = strdup(posBuf);

  debug_overlay_add_panel(overlay, "Camera", 20.0f, 20.0f, 230.0f, 136.0f, 0.6f,
                          cameraFields, 5);

  for (size_t i = 0; i < 5; ++i) {
    free((void *)cameraFields[i].value);
    cameraFields[i].value = NULL;
  }
}