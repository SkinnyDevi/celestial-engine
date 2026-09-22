#include "orbit.h"
#include <math.h>
#include <stdlib.h>

Vector3 orbit_calculate_position(CelestialBody_Orbit *orbit,
                                 double time_in_days) {
  if (!orbit)
    return (Vector3){0.0, 0.0, 0.0};

  // Update mean anomaly based on time
  if (orbit->orbital_period_days > 0.0) {
    // Mean motion n = 2 * PI / orbital_period
    double mean_motion = (2.0 * M_PI) / orbit->orbital_period_days;
    orbit->mean_anomaly =
        orbit->mean_anomaly_at_epoch + mean_motion * time_in_days;

    // Normalize mean anomaly to [0, 2*PI]
    orbit->mean_anomaly = fmod(orbit->mean_anomaly, 2.0 * M_PI);
    if (orbit->mean_anomaly < 0.0) {
      orbit->mean_anomaly += 2.0 * M_PI;
    }
  }

  double M = orbit->mean_anomaly;
  double e = orbit->eccentricity;

  // Solve Kepler's Equation: M = E - e * sin(E)
  double E = M;
  if (e > 0.8) {
    E = M + e * sin(M); // Better initial guess for high eccentricity
  }

  // Newton-Raphson iteration to find Eccentric Anomaly
  for (int i = 0; i < 15; i++) {
    double f = E - e * sin(E) - M;
    double f_prime = 1.0 - e * cos(E);
    double dE = f / f_prime;
    E -= dE;
    if (fabs(dE) < 1e-7) {
      break;
    }
  }

  // Calculate True Anomaly
  double nu =
      2.0 * atan2(sqrt(1.0 + e) * sin(E / 2.0), sqrt(1.0 - e) * cos(E / 2.0));
  orbit->true_anomaly = nu;

  // Calculate distance r from the central body
  double a = orbit->semimajor_axis;
  double r = a * (1.0 - e * cos(E));

  // Position in the orbital plane (perifocal coordinates)
  double x_prime = r * cos(nu);
  double y_prime = r * sin(nu);

  // Orbital elements (angles in radians)
  double Omega = orbit->longitude_of_ascending_node;
  double w = orbit->argument_of_periapsis;
  double i_rad = orbit->inclination;

  double cos_Omega = cos(Omega);
  double sin_Omega = sin(Omega);
  double cos_w = cos(w);
  double sin_w = sin(w);
  double cos_i = cos(i_rad);
  double sin_i = sin(i_rad);

  // Transform to 3D astronomy coordinates (Z is up)
  double x_astronomy =
      (cos_Omega * cos_w - sin_Omega * sin_w * cos_i) * x_prime +
      (-cos_Omega * sin_w - sin_Omega * cos_w * cos_i) * y_prime;

  double y_astronomy =
      (sin_Omega * cos_w + cos_Omega * sin_w * cos_i) * x_prime +
      (-sin_Omega * sin_w + cos_Omega * cos_w * cos_i) * y_prime;

  double z_astronomy = (sin_w * sin_i) * x_prime + (cos_w * sin_i) * y_prime;

  // Map to Engine coordinates where Y is up (elevation), XZ is the ecliptic
  // plane
  Vector3 pos;
  pos.x = x_astronomy;
  pos.y = z_astronomy;
  pos.z = y_astronomy;

  // Offset by the parent's center position
  pos.x += orbit->center_position.x;
  pos.y += orbit->center_position.y;
  pos.z += orbit->center_position.z;

  return pos;
}

Vector3 orbit_get_ellipse_vector(CelestialBody_Orbit *orbit) {
  if (!orbit) {
    return (Vector3){0.0, 0.0, 0.0};
  }

  double a = orbit->semimajor_axis;
  double b = a * sqrt(1.0 - orbit->eccentricity * orbit->eccentricity);

  // Orbital elements (angles in radians)
  double Omega = orbit->longitude_of_ascending_node;
  double w = orbit->argument_of_periapsis;
  double i_rad = orbit->inclination;

  double cos_Omega = cos(Omega);
  double sin_Omega = sin(Omega);
  double cos_w = cos(w);
  double sin_w = sin(w);
  double cos_i = cos(i_rad);
  double sin_i = sin(i_rad);

  Vector3 pos;
  pos.x = a * cos_Omega;
  pos.y = b * sin_Omega;
  pos.z = 0.0;

  // Offset by the parent's center position
  pos.x += orbit->center_position.x;
  pos.y += orbit->center_position.y;
  pos.z += orbit->center_position.z;

  return pos;
}

Vector3 *orbit_get_all_positions(CelestialBody_Orbit *orbit) {
  if (!orbit)
    return NULL;

  int days = orbit->orbital_period_days;
  Vector3 *positions = malloc(sizeof(Vector3) * days);
  if (!positions)
    return NULL;

  for (int i = 0; i < days; i++)
    positions[i] = orbit_calculate_position(orbit, (double)i);

  return positions;
}