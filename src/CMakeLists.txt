cmake_minimum_required(VERSION 3.23)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

project(CelestialBodyEngine)

set(CMAKE_OSX_DEPLOYMENT_TARGET "26.5" CACHE STRING "Minimum macOS version")

add_executable(celengine
  main.c
  core/cli/help.c
  core/cli/functions.c
  core/renderer/camera/camera.h
  macos/app.m
  macos/camera.m
  macos/render_handler.m
  macos/grid/spatial_grid.m
  macos/grid/displaced_mesh.m
  macos/shaders/shader_loader.m
  macos/event/mouse.m
  macos/debug/overlay.m
  macos/debug/sphere_wireframe.m
  macos/renderer.m
)

target_include_directories(celengine PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

target_sources(celengine
  PRIVATE
    main.c
)

target_link_libraries(celengine PRIVATE
    "-framework Cocoa"          # AppKit + Foundation
    "-framework Metal"          # MTLCreateSystemDefaultDevice, etc.
    "-framework QuartzCore"     # CAMetalLayer
)

target_compile_definitions(celengine PRIVATE
    SHADER_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}/macos/shaders"
)

set_source_files_properties(
    macos/app.m
    macos/camera.m
    macos/render_handler.m
    macos/grid/spatial_grid.m
    macos/grid/displaced_mesh.m
    macos/shaders/shader_loader.m
    macos/event/mouse.m
    macos/debug/overlay.m
    macos/debug/sphere_wireframe.m
    macos/renderer.m
    PROPERTIES
    COMPILE_OPTIONS "-fobjc-arc"
)

