#include "core/space/astro_time.h"
#include <criterion/criterion.h>

Test(astro_time_suite, test_gregorian_to_jd) {
  // Standard J2000 epoch: 2000-01-01 12:00:00 -> JD 2451545.0
  double jd = gregorian_to_jd(2000, 1, 1, 12, 0, 0);
  cr_assert_float_eq(jd, 2451545.0, 1e-5,
                     "J2000 epoch should be exactly 2451545.0");
}

Test(astro_time_suite, test_jd_to_gregorian) {
  int year, month, day, hour, minute, second;
  jd_to_gregorian(2451545.0, &year, &month, &day, &hour, &minute, &second);

  cr_assert_eq(year, 2000);
  cr_assert_eq(month, 1);
  cr_assert_eq(day, 1);
  cr_assert_eq(hour, 12);
  cr_assert_eq(minute, 0);
  cr_assert_eq(second, 0);
}
