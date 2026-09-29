#ifndef CLI_FLAG_H
#define CLI_FLAG_H

#include <stdbool.h>
#include <time.h>

typedef enum {
  CLI_HELP_CATEGORY_RENDERING_ENGINE,
  CLI_HELP_CATEGORY_SIMULATION,
  CLI_HELP_CATEGORY_OTHER,
} CLIHelpCategory;

typedef struct {
  const char *arg;
  const char *description;
  void (*func)(int argc, char **args);
  CLIHelpCategory category;
} CLIArg;

typedef struct {
  struct tm time;
  bool has_set_date;
  double time_scale;
  bool has_set_time_scale;
} CLIArgSimDate;

void cli_flag_macos(int argc, char **args);
void cli_flag_vulkan(int argc, char **args);
void cli_flag_help(int argc, char **args);
void cli_flag_sim_date(int argc, char **args);
void cli_flag_time_scale(int argc, char **args);
void cli_flag_show_fps(int argc, char **args);
void cli_flag_enable_debug(int argc, char **args);

#ifndef CLI_REGISTRY
#define CLI_REGISTRY
extern const CLIArg CLI_MACOS_FLAG;
extern const CLIArg CLI_VULKAN_FLAG;
extern const CLIArg CLI_HELP_FLAG;
extern const CLIArg CLI_SIM_DATE_FLAG;
extern const CLIArg CLI_TIME_SCALE_FLAG;
extern const CLIArg CLI_SHOW_FPS_FLAG;
extern const CLIArg CLI_ENABLE_DEBUG_FLAG;
#endif

#endif