#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "core/cli/functions.h"
#include "core/cli/instance_data.h"
#include "core/data/loader/data_loader.h"

#include "macos/app.h"

int render_with(RenderingEngine engine) {
  switch (engine) {
  case Metal:
    run_macos_app();
    return EXIT_SUCCESS;
  case Vulkan:
    puts("Vulkan rendering engine not yet implemented.");
    return EXIT_SUCCESS;
  default:
    puts("No rendering engine specified! Use --help for more information.");
    return EXIT_FAILURE;
  }
}

int main(int argc, char *argv[]) {
  if (argc <= 1) {
    puts("Please specify a rendering engine. Use --help for more information.");
    return EXIT_FAILURE;
  }

  cli_register_flags();
  data_loader_register_loaders();

  cli_parse_args(argc, argv);

  return render_with(cli_get_rendering_engine());
}
