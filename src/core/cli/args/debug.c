#include "cli_flag.h"
#include "core/cli/instance_data.h"
#include "core/log/log.h"

void cli_flag_enable_debug(int argc, char **args) {
  _cli_arg_set_debug_mode(true);
  _cli_arg_set_show_advanced_fps(true);
  LOG_DEBUG("Debug mode enabled.", NULL);
}