cmake_minimum_required(VERSION 3.23)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

project(CelestialBodyEngine)

set(CMAKE_OSX_DEPLOYMENT_TARGET "26.5" CACHE STRING "Minimum macOS version")

add_executable(celengine
  main.c
  core/cli/help.c
  core/cli/functions.c
  core/data/dyn_array.c
  macos/app.m
  macos/render/camera.m
  macos/render/grid/spatial_grid.m
  macos/render/grid/displaced_mesh.m
  macos/render/renderer.m
  macos/render/state/render_handler.m
  macos/render/shape/solid_sphere.m
  macos/render/space/star.m
  macos/shaders/shader_loader.m
  macos/event/mouse.m
  macos/debug/overlay.m
  macos/debug/sphere_wireframe.m
  macos/debug/camera_properties.m
  macos/debug/fps_counter.m
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
    macos/render/camera.m
    macos/render/state/render_handler.m
    macos/render/grid/spatial_grid.m
    macos/render/grid/displaced_mesh.m
    macos/render/renderer.m
    macos/render/space/star.m
    macos/render/shape/solid_sphere.m
    macos/shaders/shader_loader.m
    macos/event/mouse.m
    macos/debug/overlay.m
    macos/debug/sphere_wireframe.m
    macos/debug/camera_properties.m
    macos/debug/fps_counter.m
    PROPERTIES
    COMPILE_OPTIONS "-fobjc-arc"
)

