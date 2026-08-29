#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cli/functions.h"

int main(int argc, char *argv[]) {
  if (argc <= 1) {
    puts("Please specify a rendering engine. Use --help for more information.");
    return EXIT_FAILURE;
  }

  if (cli_parse_args(argc, argv) == EXIT_SUCCESS) {
    return EXIT_SUCCESS;
  }

  puts("No rendering engine specified! Use --help for more information.");
  return EXIT_FAILURE;
}
