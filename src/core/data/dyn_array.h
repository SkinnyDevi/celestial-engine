#ifndef DYNAMIC_ARRAY_H
#define DYNAMIC_ARRAY_H

#include <stddef.h>

typedef struct {
  void *data;
  size_t length;
  size_t capacity;
  size_t type_size;
} DynamicArray;

void DynamicArray_init(DynamicArray *arr, size_t type_size);
void DynamicArray_push(DynamicArray *arr, void *val);
void DynamicArray_free(DynamicArray *array);
void DynamicArray_remove_last(DynamicArray *array);
void DynamicArray_remove_at(DynamicArray *array, size_t index);
void DynamicArray_get(DynamicArray *array, size_t index, void *dest);
size_t DynamicArray_length(DynamicArray *array);

#endif