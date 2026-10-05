#ifndef CLI_INSTANCE_DATA_H
#define CLI_INSTANCE_DATA_H

#include "args/cli_flag.h"
#include "core/data/loader/data_loader.h"
#include "core/renderer/app_renderer.h"
#include <stdbool.h>

bool cli_is_debug_mode(void);
bool cli_should_show_fps(void);
bool cli_should_show_advanced_fps(void);
CLIArgSimDate *cli_get_sim_date(void);
RenderingEngine cli_get_rendering_engine(void);
LoadedSimulationBodies *cli_get_sim_bodies(void);
bool cli_is_using_data_file(void);
bool cli_wants_save_state(void);
const char *cli_get_data_file_path(void);
const char *cli_get_save_state_file_path(void);

// ---

void _cli_arg_set_debug_mode(bool debug_mode);
void _cli_arg_set_sim_date(CLIArgSimDate *sim_date);
void _cli_arg_set_show_fps(bool show_fps);
void _cli_arg_set_show_advanced_fps(bool show_adv_fps);
void _cli_arg_set_wants_save_state(bool wants_save_state);
void _cli_arg_set_using_data_file(bool using_data_file);
void _cli_arg_set_data_file_path(const char *data_file_path);
void _cli_arg_set_save_state_file_path(const char *save_state_file_path);
void _cli_arg_set_rendering_engine(RenderingEngine engine);
void _cli_arg_set_sim_bodies(LoadedSimulationBodies *sim_bodies);

#endif