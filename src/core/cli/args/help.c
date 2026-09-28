#include "cli_flag.h"
#include <stdio.h>
#include <stdlib.h>

void print_command_help() {
  puts("-- RENDERING ENGINE --");
  puts("--macos  | Use Metal as a rendering engine.");
  puts("--vulkan | Use Vulkan as a rendering engine.");
  puts("--   OTHER OPTIONS  --");
  puts("--debug  | Enable debug mode.");
  puts("--help   | Show this help message.");
}

void cli_flag_help(int argc, char **args) {
  print_command_help();
  exit(EXIT_SUCCESS);
}