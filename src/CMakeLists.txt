cmake_minimum_required(VERSION 3.23)

project(CelestialBodyEngine)

add_executable(celengine
  main.c
  cli/help.c
  cli/functions.c
  renderer/app_renderer.c
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

set_source_files_properties(renderer/macos/renderer.m PROPERTIES
    COMPILE_OPTIONS "-fobjc-arc"
)


