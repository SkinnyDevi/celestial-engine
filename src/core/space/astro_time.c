#include "astro_time.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

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
  return astro_time_get_jd_since_epoch(time);
}

// https://aa.usno.navy.mil/faq/JD_formula using long for date calculations
void jd_to_gregorian(double jd, int *out_year, int *out_month, int *out_day,
                     int *out_hour, int *out_minute, int *out_second) {
  long Z = (long)(jd + 0.5);
  double F = (jd + 0.5) - Z;

  long L = Z + 68569;
  long N = 4 * L / 146097;
  L = L - (146097 * N + 3) / 4;
  long I = 4000 * (L + 1) / 1461001;
  L = L - 1461 * I / 4 + 31;
  long J = 80 * L / 2447;
  long K = L - 2447 * J / 80;
  L = J / 11;
  J = J + 2 - 12 * L;
  I = 100 * (N - 49) + I + L;

  *out_year = (int)I;
  *out_month = (int)J;
  *out_day = (int)K;

  double total_hours = F * 24.0;
  *out_hour = (int)total_hours;
  double total_minutes = (total_hours - *out_hour) * 60.0;
  *out_minute = (int)total_minutes;
  *out_second = (int)((total_minutes - *out_minute) * 60.0);
}

// https://aa.usno.navy.mil/faq/JD_formula
double gregorian_to_jd(int year, int month, int day, int hour, int minute,
                       int second) {

  double I = year;
  double J = month;
  double K = day;

  return K - 32075 + 1461 * (I + 4800 + (J - 14) / 12) / 4 +
         367 * (J - 2 - (J - 14) / 12 * 12) / 12 -
         3 * ((I + 4900 + (J - 14) / 12) / 100) / 4;
}

unsigned long astro_time_jd_to_timestamp(AstronomicalTime *time) {
  if (!time)
    return 0ULL;

  int year, month, day, hour, minute, second;
  jd_to_gregorian(time->current_jd, &year, &month, &day, &hour, &minute,
                  &second);

  struct tm t = {0};
  t.tm_year = year - 1900;
  t.tm_mon = month - 1;
  t.tm_mday = day;
  t.tm_hour = hour;
  t.tm_min = minute;
  t.tm_sec = second;
  t.tm_isdst = -1;

  return (unsigned long)mktime(&t);
}

const char *astro_time_jd_to_datestring(AstronomicalTime *time) {
  if (!time)
    return NULL;

  unsigned long timestamp = astro_time_jd_to_timestamp(time);
  struct tm *t = localtime((time_t *)&timestamp);

  char buffer[100];
  snprintf(buffer, sizeof(buffer), "%s", asctime(t));
  return strdup(buffer);
}