#ifndef MACOS_RENDER_BODY_LABEL_H
#define MACOS_RENDER_BODY_LABEL_H

#include "macos/event/mouse.h"
#include "macos/render/state/render_state.h"
#include <simd/simd.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

void create_body_labels(void *window_ptr);
void destroy_body_labels(void);
void update_body_labels(RenderState *state);
void toggle_body_labels_visibility(RenderState *state);

bool body_label_find_at_point(MousePoint mouse, void **out_obj,
                              FollowType *out_type, float *out_radius,
                              simd_float3 *out_center);

#ifdef __cplusplus
}
#endif

#endif // MACOS_RENDER_BODY_LABEL_H
