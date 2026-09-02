#include "functions.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "core/log/log.h"
#include "help.h"

static bool IS_DEBUG_MODE = false;
static bool SHOW_FPS = false;
static bool SHOW_ADVANCED_FPS = false;

bool cli_find_arg(const char *arg, int argc, char **args) {
  for (int i = 1; i < argc; i++) {
    if (!strcmp(arg, args[i]))
      return true;
  }

  return false;
}

bool cli_is_debug_mode(void) { return IS_DEBUG_MODE; }
bool cli_should_show_fps(void) { return SHOW_FPS; }
bool cli_should_show_advanced_fps(void) { return SHOW_ADVANCED_FPS; }

void cli_parse_args(int argc, char **args) {
  if (cli_find_arg("--help", argc, args)) {
    print_command_help();
    exit(EXIT_SUCCESS);
  }

  if (cli_find_arg("--fps", argc, args)) {
    SHOW_FPS = true;
    SHOW_ADVANCED_FPS = false;
    LOG_INFO("FPS counter enabled.", NULL);
  }

  if (cli_find_arg("--debug", argc, args)) {
    IS_DEBUG_MODE = true;
    SHOW_ADVANCED_FPS = true;
    LOG_DEBUG("Debug mode enabled.", NULL);
  }
}