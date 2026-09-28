#include "cli_flag.h"
#include "core/cli/functions.h"
#include "core/cli/instance_data.h"
#include "core/log/log.h"

#include <stdlib.h>

void cli_flag_time_scale(int argc, char **args) {
  CLIArgSimDate *sim_date = cli_get_sim_date();
  int arg_index = cli_index_of_arg(CLI_TIME_SCALE_FLAG.arg, argc, args);
  int arg_val_index = arg_index + 1;
  if (arg_val_index >= argc) {
    LOG_ERROR("Missing value for %s", CLI_TIME_SCALE_FLAG.arg);
    exit(EXIT_FAILURE);
  }

  sim_date->has_set_time_scale = true;
  char *endptr;
  sim_date->time_scale = strtod(args[arg_val_index], &endptr);
  if (*endptr != '\0') {
    LOG_ERROR("Invalid time scale: %s", args[arg_val_index]);
    exit(EXIT_FAILURE);
  }

  sim_date->time_scale *= 0.00001; // 1 real second = 1 time scale unit
  _cli_arg_set_sim_date(sim_date);
}
