#include "cli_flag.h"
#include "core/cli/instance_data.h"
#include "core/renderer/app_renderer.h"

void cli_flag_macos(int argc, char **args) {
  _cli_arg_set_rendering_engine(Metal);
}

void cli_flag_vulkan(int argc, char **args) {
  _cli_arg_set_rendering_engine(Vulkan);
}