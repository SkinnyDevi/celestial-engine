#include "instance_data.h"

static bool IS_DEBUG_MODE = false;
static bool SHOW_FPS = false;
static bool SHOW_ADVANCED_FPS = false;
static RenderingEngine USED_RENDERING_ENGINE = NullEngine;
static bool IS_USING_DATA_FILE = false;
static const char *DATA_FILE_PATH = NULL;

static LoadedSimulationBodies LOADED_SIM_BODIES = {
    .num_orbits = 0,
    .orbits = NULL,
    .num_planets = 0,
    .planets = NULL,
    .num_moons = 0,
    .moons = NULL,
    .num_stars = 0,
    .stars = NULL,
};

static CLIArgSimDate SIM_DATE = {.time = {.tm_sec = 0,
                                          .tm_min = 0,
                                          .tm_hour = 0,
                                          .tm_mday = 1,
                                          .tm_mon = 0,
                                          .tm_year = 2000 - 1900},
                                 .has_set_date = false,
                                 .time_scale = 1.0,
                                 .has_set_time_scale = false};

bool cli_is_debug_mode(void) { return IS_DEBUG_MODE; }
bool cli_should_show_fps(void) { return SHOW_FPS; }
bool cli_should_show_advanced_fps(void) { return SHOW_ADVANCED_FPS; }
bool cli_is_using_data_file(void) { return IS_USING_DATA_FILE; }
const char *cli_get_data_file_path(void) { return DATA_FILE_PATH; }

CLIArgSimDate *cli_get_sim_date(void) { return &SIM_DATE; }
RenderingEngine cli_get_rendering_engine(void) { return USED_RENDERING_ENGINE; }
LoadedSimulationBodies *cli_get_sim_bodies(void) { return &LOADED_SIM_BODIES; }

// ---

void _cli_arg_set_debug_mode(bool debug_mode) { IS_DEBUG_MODE = debug_mode; }
void _cli_arg_set_sim_date(CLIArgSimDate *sim_date) { SIM_DATE = *sim_date; }
void _cli_arg_set_show_fps(bool show_fps) { SHOW_FPS = show_fps; }
void _cli_arg_set_show_advanced_fps(bool show_adv_fps) {
  SHOW_ADVANCED_FPS = show_adv_fps;
}
void _cli_arg_set_rendering_engine(RenderingEngine engine) {
  USED_RENDERING_ENGINE = engine;
}
void _cli_arg_set_using_data_file(bool using_data_file) {
  IS_USING_DATA_FILE = using_data_file;
}
void _cli_arg_set_data_file_path(const char *data_file_path) {
  DATA_FILE_PATH = data_file_path;
}
void _cli_arg_set_sim_bodies(LoadedSimulationBodies *sim_bodies) {
  LOADED_SIM_BODIES = *sim_bodies;
}