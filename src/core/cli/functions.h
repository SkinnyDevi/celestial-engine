#ifndef CLI_FUNCTIONS_H
#define CLI_FUNCTIONS_H

#include "core/data/dyn_array.h"
#include <stdbool.h>

bool cli_find_arg(const char *arg, int argc, char **args);
int cli_index_of_arg(const char *arg, int argc, char **args);
void cli_register_flags(void);
void cli_parse_args(int argc, char **args);
DynamicArray *cli_get_register_flags(void);

#endif
