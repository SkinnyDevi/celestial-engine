#include "instance_data.h"
#include "core/cli/args/cli_flag.h"

static bool IS_DEBUG_MODE = false;
static bool SHOW_FPS = false;
static bool SHOW_ADVANCED_FPS = false;

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
CLIArgSimDate *cli_get_sim_date(void) { return &SIM_DATE; }

void _cli_arg_set_debug_mode(bool debug_mode) { IS_DEBUG_MODE = debug_mode; }
void _cli_arg_set_sim_date(CLIArgSimDate *sim_date) { SIM_DATE = *sim_date; }
void _cli_arg_set_show_fps(bool show_fps) { SHOW_FPS = show_fps; }
void _cli_arg_set_show_advanced_fps(bool show_adv_fps) {
  SHOW_ADVANCED_FPS = show_adv_fps;
}
