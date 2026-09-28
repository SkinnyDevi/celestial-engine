#ifndef CLI_INSTANCE_DATA_H
#define CLI_INSTANCE_DATA_H

#include "args/cli_flag.h"
#include <stdbool.h>

bool cli_is_debug_mode(void);
bool cli_should_show_fps(void);
bool cli_should_show_advanced_fps(void);
CLIArgSimDate *cli_get_sim_date(void);

void _cli_arg_set_debug_mode(bool debug_mode);
void _cli_arg_set_sim_date(CLIArgSimDate *sim_date);
void _cli_arg_set_show_fps(bool show_fps);
void _cli_arg_set_show_advanced_fps(bool show_adv_fps);

#endif