#include "cli_flag.h"

const CLIArg CLI_MACOS_FLAG = {.arg = "--macos",
                               .func = cli_flag_macos,
                               .description = "Use the Metal rendering engine.",
                               .category = CLI_HELP_CATEGORY_RENDERING_ENGINE};
const CLIArg CLI_VULKAN_FLAG = {.arg = "--vulkan",
                                .func = cli_flag_vulkan,
                                .description =
                                    "Use the Vulkan rendering engine.",
                                .category = CLI_HELP_CATEGORY_RENDERING_ENGINE};

const CLIArg CLI_SIM_DATE_FLAG = {
    .arg = "--sim-date",
    .func = cli_flag_sim_date,
    .description = "Set the simulation date in UTC (YYYY-MM-DDTHH:mm:ss).",
    .category = CLI_HELP_CATEGORY_SIMULATION};
const CLIArg CLI_TIME_SCALE_FLAG = {
    .arg = "--time-scale",
    .func = cli_flag_time_scale,
    .description = "Set the time scale (e.g: 1, 5, 1e5, including negatives).",
    .category = CLI_HELP_CATEGORY_SIMULATION};
const CLIArg CLI_DATA_FILE_FLAG = {.arg = "--data-file",
                                   .func = cli_flag_load_data_file,
                                   .description =
                                       "Load simulation data from a file.",
                                   .category = CLI_HELP_CATEGORY_SIMULATION};

const CLIArg CLI_ENABLE_DEBUG_FLAG = {.arg = "--debug",
                                      .func = cli_flag_enable_debug,
                                      .description = "Enable debug mode.",
                                      .category = CLI_HELP_CATEGORY_OTHER};
const CLIArg CLI_HELP_FLAG = {.arg = "--help",
                              .func = cli_flag_help,
                              .description = "Show this help message.",
                              .category = CLI_HELP_CATEGORY_OTHER};
const CLIArg CLI_SHOW_FPS_FLAG = {.arg = "--fps",
                                  .func = cli_flag_show_fps,
                                  .description = "Show the FPS counter.",
                                  .category = CLI_HELP_CATEGORY_OTHER};