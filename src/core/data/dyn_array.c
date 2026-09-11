#include "dyn_array.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void DynamicArray_init(DynamicArray *array, size_t type_size) {
  array->data = NULL;
  array->length = 0;
  array->capacity = 0;
  array->type_size = type_size;
}

void DynamicArray_push(DynamicArray *array, void *value) {
  if (array->length >= array->capacity) {
    array->capacity = (array->capacity == 0) ? 4 : array->capacity * 2;
    array->data = realloc(array->data, array->capacity * array->type_size);
  }

  char *target_address =
      (char *)array->data + (array->length * array->type_size);

  memcpy(target_address, value, array->type_size);
  array->length++;
}

void DynamicArray_remove_last(DynamicArray *array) {
  if (!array || array->length == 0)
    return;

  array->length--;
}

void DynamicArray_remove_at(DynamicArray *array, size_t index) {
  if (!array || index >= array->length)
    return;

  char *target_address = (char *)array->data + (index * array->type_size);
  memmove(target_address, target_address + array->type_size,
          (array->length - index - 1) * array->type_size);
  array->length--;
}

void DynamicArray_get(DynamicArray *array, size_t index, void *dest) {
  if (!array || index >= array->length)
    return;

  char *target_address = (char *)array->data + (index * array->type_size);
  memcpy(dest, target_address, array->type_size);
}

size_t DynamicArray_length(DynamicArray *array) {
  if (!array)
    return 0;

  return array->length;
}

void DynamicArray_free(DynamicArray *array) {
  if (!array)
    return;

  free(array->data);
  array->data = NULL;
  array->length = 0;
  array->capacity = 0;
  array->type_size = 0;
}