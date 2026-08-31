cmake_minimum_required(VERSION 3.23)

project(CelestialBodyEngine)

set(CMAKE_OSX_DEPLOYMENT_TARGET "26.5" CACHE STRING "Minimum macOS version")

add_executable(celengine
  main.c
  cli/help.c
  cli/functions.c
  renderer/app_renderer.c
  renderer/camera/camera.h
  renderer/macos/app.m
  renderer/macos/camera.m
  renderer/macos/render_handler.m
  renderer/macos/grid/spatial_grid.m
  renderer/macos/grid/displaced_mesh.m
  renderer/macos/event/mouse.m
  renderer/macos/debug/debug_overlay.m
  renderer/macos/debug/debug_gizmos.m
  renderer/macos/renderer.m
)

target_sources(celengine
  PRIVATE
    main.c
)

target_link_libraries(celengine PRIVATE
    "-framework Cocoa"          # AppKit + Foundation
    "-framework Metal"          # MTLCreateSystemDefaultDevice, etc.
    "-framework QuartzCore"     # CAMetalLayer
)

set_source_files_properties(
    renderer/macos/app.m
    renderer/macos/render_handler.m
    renderer/macos/grid/spatial_grid.m
    renderer/macos/grid/displaced_mesh.m
    renderer/macos/event/mouse.m
    renderer/macos/debug/debug_overlay.m
    renderer/macos/debug/debug_gizmos.m
    renderer/macos/renderer.m
    PROPERTIES
    COMPILE_OPTIONS "-fobjc-arc"
)

