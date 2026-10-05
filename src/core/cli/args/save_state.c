#include "cli_flag.h"
#include "core/cli/functions.h"
#include "core/cli/instance_data.h"
#include "core/data/loader/data_loader.h"
#include "core/log/log.h"

#include <stdlib.h>

void exec_flag_save_state() {
  const char *file_path = cli_get_save_state_file_path();

  const char *ext = get_file_ext(file_path);
  LOG_INFO("Saving data to file %s", file_path);
  LOG_DEBUG("Saving data to file with extension: %s", ext);

  if (ext == NULL) {
    LOG_ERROR("File extension not found for file %s", file_path);
    exit(EXIT_FAILURE);
  }

  const DataLoader *data_loader = data_loader_get_by_ext(ext);
  if (data_loader == NULL) {
    LOG_ERROR("Data loader not found for file extension: %s", ext);
    exit(EXIT_FAILURE);
  }

  LoadedSimulationBodies *bodies = cli_get_sim_bodies();
  bool success = data_loader->save(file_path, bodies);
  if (!success) {
    LOG_ERROR("Failed to save data to file %s", file_path);
    exit(EXIT_FAILURE);
  }

  LOG_INFO("Data saved successfully to file %s", file_path);
}

void cli_flag_save_state(int argc, char **argv) {
  int arg_idx = cli_index_of_arg(CLI_SAVE_STATE_FLAG.arg, argc, argv);
  const char *file_path = argv[arg_idx + 1];

  _cli_arg_set_save_state_file_path(file_path);
  _cli_arg_set_wants_save_state(true);
}