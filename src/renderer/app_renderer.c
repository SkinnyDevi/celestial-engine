#include "app_renderer.h"
#include <stdio.h>
#include <stdlib.h>

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
