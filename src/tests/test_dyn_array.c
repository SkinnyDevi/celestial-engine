#include "core/data/dyn_array.h"
#include <criterion/criterion.h>

Test(dyn_array_suite, test_init) {
  DynamicArray arr;
  DynamicArray_init(&arr, sizeof(int));

  cr_assert_eq(arr.length, 0);
  cr_assert_eq(arr.capacity, 0);
  cr_assert_eq(arr.type_size, sizeof(int));
  cr_assert_null(arr.data);

  DynamicArray_free(&arr);
}

Test(dyn_array_suite, test_push_and_get) {
  DynamicArray arr;
  DynamicArray_init(&arr, sizeof(int));

  int val1 = 10;
  int val2 = 20;
  int val3 = 30;

  DynamicArray_push(&arr, &val1);
  DynamicArray_push(&arr, &val2);
  DynamicArray_push(&arr, &val3);

  cr_assert_eq(arr.length, 3);
  cr_assert(arr.capacity >= 3);

  int out_val = 0;

  DynamicArray_get(&arr, 0, &out_val);
  cr_assert_eq(out_val, 10);

  DynamicArray_get(&arr, 1, &out_val);
  cr_assert_eq(out_val, 20);

  DynamicArray_get(&arr, 2, &out_val);
  cr_assert_eq(out_val, 30);

  DynamicArray_free(&arr);
}

Test(dyn_array_suite, test_remove_last) {
  DynamicArray arr;
  DynamicArray_init(&arr, sizeof(int));

  int val1 = 10;
  int val2 = 20;
  DynamicArray_push(&arr, &val1);
  DynamicArray_push(&arr, &val2);
  cr_assert_eq(DynamicArray_length(&arr), 2);

  DynamicArray_remove_last(&arr);
  cr_assert_eq(DynamicArray_length(&arr), 1);

  int out_val = 0;
  DynamicArray_get(&arr, 0, &out_val);
  cr_assert_eq(out_val, 10);

  // Removing from array with 1 item
  DynamicArray_remove_last(&arr);
  cr_assert_eq(DynamicArray_length(&arr), 0);

  // Removing from empty array shouldn't crash
  DynamicArray_remove_last(&arr);
  cr_assert_eq(DynamicArray_length(&arr), 0);

  DynamicArray_free(&arr);
}

Test(dyn_array_suite, test_remove_at) {
  DynamicArray arr;
  DynamicArray_init(&arr, sizeof(int));

  int vals[] = {10, 20, 30, 40, 50};
  for (int i = 0; i < 5; i++)
    DynamicArray_push(&arr, &vals[i]);

  // Remove element at index 2 (value 30)
  DynamicArray_remove_at(&arr, 2);

  cr_assert_eq(DynamicArray_length(&arr), 4);

  int out_val = 0;
  DynamicArray_get(&arr, 2, &out_val);
  cr_assert_eq(out_val, 40,
               "Element at index 2 should now be 40 after shifting");

  DynamicArray_get(&arr, 3, &out_val);
  cr_assert_eq(out_val, 50,
               "Element at index 3 should now be 50 after shifting");

  // Remove first element
  DynamicArray_remove_at(&arr, 0);
  cr_assert_eq(DynamicArray_length(&arr), 3);
  DynamicArray_get(&arr, 0, &out_val);
  cr_assert_eq(out_val, 20);

  // Remove last element using remove_at
  DynamicArray_remove_at(&arr, 2);
  cr_assert_eq(DynamicArray_length(&arr), 2);

  // Remove out of bounds shouldn't crash
  DynamicArray_remove_at(&arr, 10);
  cr_assert_eq(DynamicArray_length(&arr), 2);

  DynamicArray_free(&arr);
}

Test(dyn_array_suite, test_struct_resizing) {
  typedef struct {
    float x, y, z;
    int id;
  } Point;

  DynamicArray arr;
  DynamicArray_init(&arr, sizeof(Point));

  // Push enough elements to trigger multiple internal reallocations
  for (int i = 0; i < 1000; i++) {
    Point p = {(float)i, (float)(i * 2), (float)(i * 3), i};
    DynamicArray_push(&arr, &p);
  }

  cr_assert_eq(DynamicArray_length(&arr), 1000);
  cr_assert(arr.capacity >= 1000,
            "Capacity should have grown to hold 1000 elements");

  // Verify data integrity for some elements
  Point p_out;

  DynamicArray_get(&arr, 0, &p_out);
  cr_assert_eq(p_out.id, 0);
  cr_assert_float_eq(p_out.y, 0.0f, 1e-5);

  DynamicArray_get(&arr, 500, &p_out);
  cr_assert_eq(p_out.id, 500);
  cr_assert_float_eq(p_out.y, 1000.0f, 1e-5);

  DynamicArray_get(&arr, 999, &p_out);
  cr_assert_eq(p_out.id, 999);
  cr_assert_float_eq(p_out.y, 1998.0f, 1e-5);

  DynamicArray_free(&arr);
}
