#ifndef CLI_FLAG_H
#define CLI_FLAG_H

#include <stdbool.h>
#include <time.h>

typedef struct {
  const char *arg;
  void (*func)(int argc, char **args);
} CLIArg;

typedef struct {
  struct tm time;
  bool has_set_date;
  double time_scale;
  bool has_set_time_scale;
} CLIArgSimDate;

void cli_flag_help(int argc, char **args);
void cli_flag_sim_date(int argc, char **args);
void cli_flag_time_scale(int argc, char **args);
void cli_flag_show_fps(int argc, char **args);
void cli_flag_enable_debug(int argc, char **args);

#ifndef CLI_REGISTRY
#define CLI_REGISTRY
extern const CLIArg CLI_HELP_FLAG;
extern const CLIArg CLI_SIM_DATE_FLAG;
extern const CLIArg CLI_TIME_SCALE_FLAG;
extern const CLIArg CLI_SHOW_FPS_FLAG;
extern const CLIArg CLI_ENABLE_DEBUG_FLAG;
#endif

#endif