#include "cli_flag.h"
#include "core/cli/functions.h"
#include "core/cli/instance_data.h"
#include "core/log/log.h"
#include <stdio.h>
#include <stdlib.h>

void cli_flag_sim_date(int argc, char **args) {
  CLIArgSimDate *sim_date = cli_get_sim_date();
  int arg_index = cli_index_of_arg(CLI_SIM_DATE_FLAG.arg, argc, args);
  int arg_val_index = arg_index + 1;

  if (arg_val_index >= argc) {
    LOG_ERROR("Missing value for %s. Expected format: YYYY-MM-DDTHH:mm:ssZ",
              CLI_SIM_DATE_FLAG.arg);
    exit(EXIT_FAILURE);
  }

  int year, month, day, hour, min, sec;
  if (sscanf(args[arg_val_index], "%d-%d-%dT%d:%d:%dZ", &year, &month, &day,
             &hour, &min, &sec) != 6) {
    LOG_ERROR("Invalid format for %s: %s. Expected YYYY-MM-DDTHH:mm:ssZ",
              CLI_SIM_DATE_FLAG.arg, args[arg_val_index]);
    exit(EXIT_FAILURE);
  }

  if (year < -4713 || year > 9999 || month < 1 || month > 12 || day < 1 ||
      day > 31 || hour < 0 || hour > 23 || min < 0 || min > 59 || sec < 0 ||
      sec > 60) {
    LOG_ERROR("Date components out of range for %s: %s", CLI_SIM_DATE_FLAG.arg,
              args[arg_val_index]);
    exit(EXIT_FAILURE);
  }

  sim_date->has_set_date = true;
  sim_date->time.tm_year = year - 1900;
  sim_date->time.tm_mon = month - 1;
  sim_date->time.tm_mday = day;
  sim_date->time.tm_hour = hour;
  sim_date->time.tm_min = min;
  sim_date->time.tm_sec = sec;

  _cli_arg_set_sim_date(sim_date);
}