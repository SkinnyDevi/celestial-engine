#ifndef SPACE_UNITS_H
#define SPACE_UNITS_H

#define METERS_TO_RENDER_UNITS (1.0 / 1e9)
#define AU_TO_METERS (1.495978707e11)
#define LY_TO_METERS (9.46073047258e15)
#define PARSECS_TO_METERS (3.085677581e16)

static inline double parsec_to_meter(double parsec) {
  return parsec * PARSECS_TO_METERS;
}

static inline double meter_to_parsec(double meter) {
  return meter / PARSECS_TO_METERS;
}

static inline double ly_to_meter(double ly) { return ly * LY_TO_METERS; }

static inline double meter_to_ly(double meter) { return meter / LY_TO_METERS; }

static inline double au_to_meter(double au) { return au * AU_TO_METERS; }

static inline double meter_to_au(double meter) { return meter / AU_TO_METERS; }

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