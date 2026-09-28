#include "cli_flag.h"

const CLIArg CLI_HELP_FLAG = {.arg = "--help", .func = cli_flag_help};
const CLIArg CLI_SIM_DATE_FLAG = {.arg = "--sim-date",
                                  .func = cli_flag_sim_date};
const CLIArg CLI_TIME_SCALE_FLAG = {.arg = "--time-scale",
                                    .func = cli_flag_time_scale};
const CLIArg CLI_SHOW_FPS_FLAG = {.arg = "--fps", .func = cli_flag_show_fps};
const CLIArg CLI_ENABLE_DEBUG_FLAG = {.arg = "--debug",
                                      .func = cli_flag_enable_debug};