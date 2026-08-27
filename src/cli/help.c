#include "help.h"
#include <stdio.h>
#include <stdlib.h>

void print_command_help() {
  puts("-- RENDERING ENGINE --");
  puts("--macos  | Use Metal as a rendering engine.");
  puts("--vulkan | Use Vulkan as a rendering engine.");
}
