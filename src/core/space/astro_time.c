#include "astro_time.h"

void astro_time_init(AstronomicalTime *time, double start_jd,
                     double time_scale) {
  if (!time)
    return;
  time->epoch_jd = start_jd;
  time->current_jd = start_jd;
  time->time_scale = time_scale;
}

void astro_time_update(AstronomicalTime *time, double delta_seconds) {
  if (!time)
    return;
  time->current_jd += delta_seconds * time->time_scale;
}

double astro_time_get_jd_since_epoch(const AstronomicalTime *time) {
  if (!time)
    return 0.0;
  return time->current_jd - time->epoch_jd;
}

double astro_time_get_days_since_epoch(const AstronomicalTime *time) {
  if (!time)
    return 0.0;
  return astro_time_get_jd_since_epoch(time) / time->time_scale;
}
