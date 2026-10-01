#include "cli_flag.h"
#include "core/cli/functions.h"
#include "core/cli/instance_data.h"
#include "core/data/loader/data_loader.h"
#include "core/log/log.h"

#include <stdlib.h>
#include <string.h>

static const char *get_file_ext(const char *filename) {
  return strrchr(filename, '.');
}

void cli_flag_load_data_file(int argc, char **argv) {
  int arg_idx = cli_index_of_arg("--data-file", argc, argv);
  const char *file_path = argv[arg_idx + 1];

  const char *ext = get_file_ext(file_path);
  LOG_INFO("Loading data from file %s", file_path);
  LOG_DEBUG("Loading data from file extension: %s", ext);

  if (ext == NULL) {
    LOG_ERROR("File extension not found for file %s", file_path);
    exit(EXIT_FAILURE);
  }

  const DataLoader *data_loader = data_loader_get_by_ext(ext);
  if (data_loader == NULL) {
    LOG_ERROR("Data loader not found for file extension: %s", ext);
    exit(EXIT_FAILURE);
  }

  LoadedSimulationBodies *bodies = data_loader->load(file_path);
  if (bodies == NULL) {
    LOG_ERROR("Failed to load data from file %s", file_path);
    exit(EXIT_FAILURE);
  }

  _cli_arg_set_using_data_file(true);
  _cli_arg_set_data_file_path(file_path);
  _cli_arg_set_sim_bodies(bodies);
}