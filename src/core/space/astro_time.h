#ifndef SPACE_ASTRO_TIME_H
#define SPACE_ASTRO_TIME_H

typedef struct {
  double epoch_jd; // julian days
  double current_jd;
  double time_scale;
} AstronomicalTime;

void astro_time_init(AstronomicalTime *time, double start_jd,
                     double time_scale);
void astro_time_update(AstronomicalTime *time, double delta_seconds);
double astro_time_get_jd_since_epoch(const AstronomicalTime *time);
double astro_time_get_days_since_epoch(const AstronomicalTime *time);

#endif
