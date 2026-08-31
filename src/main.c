#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "core/cli/functions.h"
#include "core/renderer/app_renderer.h"

#include "macos/app.h"

void render_with(RenderingEngine engine) {
  switch (engine) {
  case Metal:
    run_macos_app();
    break;
  case Vulkan:
    break;
  }
}

int main(int argc, char *argv[]) {
  if (argc <= 1) {
    puts("Please specify a rendering engine. Use --help for more information.");
    return EXIT_FAILURE;
  }

  cli_parse_args(argc, argv);

  if (cli_find_arg("--macos", argc, argv)) {
    render_with(Metal);
    return EXIT_SUCCESS;
  }

  if (cli_find_arg("--vulkan", argc, argv)) {
    puts("Using Vulkan rendering engine.");
    render_with(Vulkan);
    return EXIT_SUCCESS;
  }

  puts("No rendering engine specified! Use --help for more information.");
  return EXIT_FAILURE;
}
