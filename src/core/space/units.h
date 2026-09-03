#ifndef SPACE_UNITS_H
#define SPACE_UNITS_H

#define METERS_TO_RENDER_UNITS (1.0 / 1e9)
#define PARSECS_TO_METERS (3.0857e16)

static inline double parsec_to_meter(double parsec) {
  return (double)(parsec * PARSECS_TO_METERS);
}

static inline double meter_to_render_unit(double meter) {
  return (double)(meter * METERS_TO_RENDER_UNITS);
}

static inline double render_unit_to_meter(double render_unit) {
  return (double)(render_unit / METERS_TO_RENDER_UNITS);
}

static inline float render_unit(double value) {
  return (float)(value * METERS_TO_RENDER_UNITS);
}

#endif