#ifndef MACOS_WINDOW_EVENT_INPUT_REGISTRY_H
#define MACOS_WINDOW_EVENT_INPUT_REGISTRY_H

#include <stdbool.h>
#include <stdint.h>

typedef struct RenderState RenderState;

typedef enum {
    KEY_ACTION_DOWN,
    KEY_ACTION_UP,
    KEY_ACTION_HELD
} KeyActionType;

typedef void (*KeyCallback)(RenderState *state, uint16_t key_code);

typedef struct InputRegistry InputRegistry;

InputRegistry *InputRegistry_Create(void);
void InputRegistry_Destroy(InputRegistry *registry);

void input_register_bind(InputRegistry *registry, uint16_t key_code, KeyActionType type, KeyCallback callback);
void input_process_key_down(InputRegistry *registry, RenderState *state, uint16_t key_code);
void input_process_key_up(InputRegistry *registry, RenderState *state, uint16_t key_code);
void input_update_held_keys(InputRegistry *registry, RenderState *state);

#endif // MACOS_WINDOW_EVENT_INPUT_REGISTRY_H
