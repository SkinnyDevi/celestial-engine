#include "functions.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

static bool IS_DEBUG_MODE = false;

bool cli_find_arg(const char *arg, int argc, char **args) {
  for (int i = 1; i < argc; i++) {
    if (!strcmp(arg, args[i]))
      return true;
  }

  return false;
}

void cli_set_debug_mode(bool debug) { IS_DEBUG_MODE = debug; }
bool cli_is_debug_mode(void) { return IS_DEBUG_MODE; }

int cli_parse_args(int argc, char **args) {
	if (cli_find_arg("--help", argc, args)) {
    print_command_help();
    return EXIT_SUCCESS;
  }

	if (cli_find_arg("--debug", argc, args)) {
		cli_set_debug_mode(true);
		puts("[DEBUG] Debug mode enabled.");
	}

  if (cli_find_arg("--macos", argc, args)) {
    puts("Using Metal rendering engine.");
    render_with(Metal);
    return EXIT_SUCCESS;
  }

  if (cli_find_arg("--vulkan", argc, args)) {
    puts("Using Vulkan rendering engine.");
    render_with(Vulkan);
    return EXIT_SUCCESS;
  }

  return EXIT_FAILURE;
}