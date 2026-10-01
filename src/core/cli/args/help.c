#include "cli_flag.h"
#include "core/cli/functions.h"
#include "core/data/dyn_array.h"
#include "core/data/loader/data_loader.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int *get_idx_of_category(DynamicArray *flags, CLIHelpCategory category) {
  int *indices = (int *)malloc(sizeof(int) * flags->length);
  for (int i = 0; i < flags->length; i++)
    indices[i] = -1;

  int idx = 0;

  for (int i = 0; i < flags->length; i++) {
    CLIArg arg;
    DynamicArray_get(flags, i, &arg);
    if (arg.category == category)
      indices[idx++] = i;
  }

  return indices;
}

void print_category_help(DynamicArray *flags, CLIHelpCategory category) {
  int *indices = get_idx_of_category(flags, category);

  int max_len = 0;
  for (int i = 0; indices[i] != -1; i++) {
    CLIArg arg;
    DynamicArray_get(flags, indices[i], &arg);
    int len = strlen(arg.arg);
    if (len > max_len) {
      max_len = len;
    }
  }

  for (int i = 0; indices[i] != -1; i++) {
    CLIArg arg;
    DynamicArray_get(flags, indices[i], &arg);
    printf("%-*s | %s\n", max_len, arg.arg, arg.description);
  }

  free(indices);
}

void print_title(const char *title) { printf("[ %s ]\n\n", title); }

void print_rendering_engine_help(DynamicArray *flags) {
  print_title("RENDERING ENGINE");
  print_category_help(flags, CLI_HELP_CATEGORY_RENDERING_ENGINE);
  puts("");
}

void print_simulation_help(DynamicArray *flags) {
  print_title("SIMULATION");
  print_category_help(flags, CLI_HELP_CATEGORY_SIMULATION);
  puts("");
}

void print_data_file_help() {
  print_title("DATA FILE FORMATS");
  puts("Available data file formats (extensions):");
  DynamicArray *data_loaders = data_loader_get_registered_loaders();
  int num_loaders = DynamicArray_length(data_loaders);
  for (int i = 0; i < num_loaders; i++) {
    const DataLoader *loader;
    DynamicArray_get(data_loaders, i, &loader);
    printf("- %s\n", loader->format_ext);
  }

  puts("");
}

void print_other_help(DynamicArray *flags) {
  print_title("OTHER OPTIONS");
  print_category_help(flags, CLI_HELP_CATEGORY_OTHER);
  puts("");
}

void print_command_help() {
  DynamicArray *flags = cli_get_register_flags();
  print_rendering_engine_help(flags);
  print_simulation_help(flags);
  print_data_file_help();
  print_other_help(flags);
}

void cli_flag_help(int argc, char **args) {
  print_command_help();
  exit(EXIT_SUCCESS);
}