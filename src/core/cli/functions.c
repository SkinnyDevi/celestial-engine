#include "functions.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "core/cli/args/cli_flag.h"
#include "core/data/dyn_array.h"

static DynamicArray REGISTERED_CLI_FLAGS;
DynamicArray *cli_get_register_flags(void) { return &REGISTERED_CLI_FLAGS; }

int cli_index_of_arg(const char *arg, int argc, char **args) {
  for (int i = 1; i < argc; i++) {
    if (!strcmp(arg, args[i]))
      return i;
  }

  return -1;
}

bool cli_find_arg(const char *arg, int argc, char **args) {
  return cli_index_of_arg(arg, argc, args) != -1;
}

void cli_parse_args(int argc, char **args) {
  int registered_flags = DynamicArray_length(&REGISTERED_CLI_FLAGS);
  for (int i = 1; i < argc; i++) {
    for (int j = 0; j < registered_flags; j++) {
      CLIArg arg;
      DynamicArray_get(&REGISTERED_CLI_FLAGS, j, &arg);
      if (!strcmp(arg.arg, args[i]))
        arg.func(argc, args);
    }
  }
}

void cli_register_flags(void) {
  DynamicArray_init(&REGISTERED_CLI_FLAGS, sizeof(CLIArg));

  DynamicArray_push(&REGISTERED_CLI_FLAGS, (void *)&CLI_HELP_FLAG);
  DynamicArray_push(&REGISTERED_CLI_FLAGS, (void *)&CLI_MACOS_FLAG);
  DynamicArray_push(&REGISTERED_CLI_FLAGS, (void *)&CLI_VULKAN_FLAG);
  DynamicArray_push(&REGISTERED_CLI_FLAGS, (void *)&CLI_SIM_DATE_FLAG);
  DynamicArray_push(&REGISTERED_CLI_FLAGS, (void *)&CLI_TIME_SCALE_FLAG);
  DynamicArray_push(&REGISTERED_CLI_FLAGS, (void *)&CLI_SHOW_FPS_FLAG);
  DynamicArray_push(&REGISTERED_CLI_FLAGS, (void *)&CLI_ENABLE_DEBUG_FLAG);
}