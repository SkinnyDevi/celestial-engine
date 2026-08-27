#include "functions.h"
#include <string.h>

bool cli_find_arg(const char *arg, int argc, char **args) {
  for (int i = 1; i < argc; i++) {
    if (!strcmp(arg, args[i]))
      return true;
  }

  return false;
}
