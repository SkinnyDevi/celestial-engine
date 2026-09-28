#include "cli_flag.h"
#include "core/cli/instance_data.h"
#include "core/log/log.h"

void cli_flag_show_fps(int argc, char **args) {
  _cli_arg_set_show_fps(true);
  _cli_arg_set_show_advanced_fps(false);
  LOG_INFO("FPS counter enabled.", NULL);
}