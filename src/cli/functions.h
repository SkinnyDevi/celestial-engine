#ifndef CLI_FUNCTIONS_H
#define CLI_FUNCTIONS_H

#include <stdbool.h>
#include "help.h"
#include "../renderer/app_renderer.h"

int cli_parse_args(int argc, char **args);
bool cli_find_arg(const char *arg, int argc, char **args);
void cli_set_debug_mode(bool debug);
bool cli_is_debug_mode(void);

#endif
