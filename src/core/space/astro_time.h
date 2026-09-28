#ifndef SPACE_ASTRO_TIME_H
#define SPACE_ASTRO_TIME_H

#include "core/cli/args/cli_flag.h"
#include <time.h>

typedef struct {
  double epoch_jd; // julian days
  double current_jd;
  double time_scale;
} AstronomicalTime;

void astro_time_init(AstronomicalTime *time, double start_jd,
                     double time_scale);
void astro_time_update(AstronomicalTime *time, double delta_seconds);
void astro_time_set_date_gregorian(AstronomicalTime *time, struct tm *date);
void astro_time_set_time_scale(AstronomicalTime *time, double time_scale);
double astro_time_get_jd_since_epoch(const AstronomicalTime *time);
double astro_time_get_days_since_epoch(const AstronomicalTime *time);
void jd_to_gregorian(double jd, int *out_year, int *out_month, int *out_day,
                     int *out_hour, int *out_minute, int *out_second);
double gregorian_to_jd(int year, int month, int day, int hour, int minute,
                       int second);
unsigned long astro_time_jd_to_timestamp(AstronomicalTime *time);
const char *astro_time_jd_to_datestring(AstronomicalTime *time);
void astro_time_from_cli_args(AstronomicalTime *time,
                              CLIArgSimDate *cli_sim_date);

#endif
