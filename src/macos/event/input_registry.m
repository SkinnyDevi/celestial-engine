#import "input_registry.h"
#import <stdlib.h>

#import "core/data/dyn_array.h"

#define MAX_KEY_CODES 512

typedef struct {
  uint16_t key_code;
  KeyActionType action_type;
  KeyCallback callback;
} KeyBinding;

struct InputRegistry {
  DynamicArray bindings;
  bool keys_held[MAX_KEY_CODES];
};

InputRegistry *InputRegistry_Create(void) {
  InputRegistry *registry = calloc(1, sizeof(InputRegistry));
  if (registry)
    DynamicArray_init(&registry->bindings, sizeof(KeyBinding));

  return registry;
}

void InputRegistry_Destroy(InputRegistry *registry) {
  if (registry) {
    DynamicArray_free(&registry->bindings);
    free(registry);
  }
}

void input_register_bind(InputRegistry *registry, uint16_t key_code,
                         KeyActionType type, KeyCallback callback) {
  if (!registry)
    return;

  KeyBinding binding = {key_code, type, callback};
  DynamicArray_push(&registry->bindings, &binding);
}

void input_process_key_down(InputRegistry *registry, RenderState *state,
                            uint16_t key_code) {
  if (!registry || key_code >= MAX_KEY_CODES)
    return;

  bool was_held = registry->keys_held[key_code];
  registry->keys_held[key_code] = true;

  if (was_held)
    return;

  size_t count = DynamicArray_length(&registry->bindings);
  for (size_t i = 0; i < count; i++) {
    KeyBinding binding;
    DynamicArray_get(&registry->bindings, i, &binding);
    if (binding.key_code == key_code &&
        binding.action_type == KEY_ACTION_DOWN) {
      if (binding.callback)
        binding.callback(state, key_code);
    }
  }
}

void input_process_key_up(InputRegistry *registry, RenderState *state,
                          uint16_t key_code) {
  if (!registry || key_code >= MAX_KEY_CODES)
    return;
  registry->keys_held[key_code] = false;

  size_t count = DynamicArray_length(&registry->bindings);
  for (size_t i = 0; i < count; i++) {
    KeyBinding binding;
    DynamicArray_get(&registry->bindings, i, &binding);
    if (binding.key_code == key_code && binding.action_type == KEY_ACTION_UP) {
      if (binding.callback)
        binding.callback(state, key_code);
    }
  }
}

void input_update_held_keys(InputRegistry *registry, RenderState *state) {
  if (!registry)
    return;

  size_t count = DynamicArray_length(&registry->bindings);
  for (size_t i = 0; i < count; i++) {
    KeyBinding binding;
    DynamicArray_get(&registry->bindings, i, &binding);
    if (binding.action_type == KEY_ACTION_HELD) {
      if (binding.key_code < MAX_KEY_CODES &&
          registry->keys_held[binding.key_code]) {
        if (binding.callback)
          binding.callback(state, binding.key_code);
      }
    }
  }
}
