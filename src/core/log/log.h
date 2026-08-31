#ifndef LOG_H
#define LOG_H

#include <stdio.h>

#include "core/cli/functions.h"

#define LOG_DEBUG(format, ...)                                                 \
  do {                                                                         \
    if (cli_is_debug_mode()) {                                                 \
      fprintf(stdout, "[DEBUG] " format "\n", __VA_ARGS__);                    \
    }                                                                          \
  } while (0)

#define LOG_INFO(format, ...)                                                  \
  do {                                                                         \
    fprintf(stdout, "[INFO] " format "\n", __VA_ARGS__);                       \
  } while (0)

#define LOG_ERROR(format, ...)                                                 \
  do {                                                                         \
    fprintf(stderr, "[ERROR] " format "\n", __VA_ARGS__);                      \
    fprintf(stdout, "[ERROR] " format "\n", __VA_ARGS__);                      \
  } while (0)

#define LOG_WARN(format, ...)                                                  \
  do {                                                                         \
    fprintf(stdout, "[WARN] " format "\n", __VA_ARGS__);                       \
  } while (0)

#endif