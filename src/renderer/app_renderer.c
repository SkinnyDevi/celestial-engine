#include "app_renderer.h"
#include "macos/renderer.h"
#include <stdio.h>
#include <stdlib.h>

void render_with_metal() {
  RendererHandle handler =
      init_metal_window(1280, 720, "Celestial Body Engine");

  if (!handler) {
    puts("Failed to initialize Metal window.");
    exit(EXIT_FAILURE);
  }

  // Main Game/Render Loop
  while (1) {
    pump_os_events();    // Keep the window responsive
    draw_frame(handler); // Issue GPU commands
  }
}

void render_with(RenderingEngine engine) {
  switch (engine) {
  case Metal:
    render_with_metal();
    break;
  case Vulkan:
    break;
  }
}
