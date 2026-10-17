#include "core/cli/functions.h"
#include "core/cli/instance_data.h"
#include <criterion/criterion.h>

Test(cli_args_suite, test_fps_flag) {
  char *argv[] = {"app", "--fps"};
  int argc = 2;

  cli_register_flags();
  cli_parse_args(argc, argv);

  cr_assert_eq(cli_should_show_fps(), true);
  cr_assert_eq(cli_should_show_advanced_fps(), false);
}

Test(cli_args_suite, test_debug_flag) {
  char *argv[] = {"app", "--debug"};
  int argc = 2;

  cli_register_flags();
  cli_parse_args(argc, argv);

  cr_assert_eq(cli_is_debug_mode(), true);
  cr_assert_eq(cli_should_show_advanced_fps(), true);
}

Test(cli_args_suite, test_sim_date_valid) {
  char *argv[] = {"app", "--sim-date", "2024-05-20T15:30:45Z"};
  int argc = 3;

  cli_register_flags();
  cli_parse_args(argc, argv);

  CLIArgSimDate *sim_date = cli_get_sim_date();
  cr_assert_eq(sim_date->has_set_date, true);
  cr_assert_eq(sim_date->time.tm_year, 2024 - 1900);
  cr_assert_eq(sim_date->time.tm_mon, 5 - 1);
  cr_assert_eq(sim_date->time.tm_mday, 20);
  cr_assert_eq(sim_date->time.tm_hour, 15);
  cr_assert_eq(sim_date->time.tm_min, 30);
  cr_assert_eq(sim_date->time.tm_sec, 45);
}

Test(cli_args_suite, test_time_scale_valid) {
  char *argv[] = {"app", "--time-scale", "1e5"};
  int argc = 3;

  cli_register_flags();
  cli_parse_args(argc, argv);

  CLIArgSimDate *sim_date = cli_get_sim_date();
  cr_assert_eq(sim_date->has_set_time_scale, true);
  cr_assert_float_eq(sim_date->time_scale, 1e5 * 0.00001, 1e-6);
}

Test(cli_args_suite, test_combined_flags) {
  char *argv[] = {"app", "--fps",      "--time-scale",
                  "50",  "--sim-date", "2000-01-01T00:00:00Z"};
  int argc = 6;

  cli_register_flags();
  cli_parse_args(argc, argv);

  cr_assert_eq(cli_should_show_fps(), true);

  CLIArgSimDate *sim_date = cli_get_sim_date();
  cr_assert_eq(sim_date->has_set_time_scale, true);
  cr_assert_float_eq(sim_date->time_scale, 50 * 0.00001, 1e-6);

  cr_assert_eq(sim_date->has_set_date, true);
  cr_assert_eq(sim_date->time.tm_year, 2000 - 1900);
}

Test(cli_args_suite, test_multi_data_file_loading_with_deduplication) {
  const char *file1 = "test_multi_1.json";
  const char *file2 = "test_multi_2.json";

  FILE *f1 = fopen(file1, "w");
  fputs("{ \"stars\": [ { \"name\": \"Sun Alpha\", \"body_id\": \"SOL\" } ], "
        "  \"planets\": [ { \"name\": \"Earth\", \"body_id\": \"EARTH\" } ] }",
        f1);
  fclose(f1);

  FILE *f2 = fopen(file2, "w");
  fputs("{ \"stars\": [ { \"name\": \"Sun Beta\", \"body_id\": \"SOL\" }, "
        "               { \"name\": \"Proxima\", \"body_id\": \"PROXIMA\" } ], "
        "  \"planets\": [ { \"name\": \"Mars\", \"body_id\": \"MARS\" } ] }",
        f2);
  fclose(f2);

  data_loader_register_loaders();

  char *argv[] = {"app", "--data-file", (char *)file1, (char *)file2};
  int argc = 4;

  cli_register_flags();
  cli_parse_args(argc, argv);

  LoadedSimulationBodies *bodies = cli_get_sim_bodies();
  cr_assert_not_null(bodies);
  // Expect 2 stars (SOL deduplicated, PROXIMA kept)
  cr_assert_eq(DynamicArray_length(&bodies->stars), 2);
  // Expect 2 planets (EARTH, MARS)
  cr_assert_eq(DynamicArray_length(&bodies->planets), 2);

  remove(file1);
  remove(file2);
}
