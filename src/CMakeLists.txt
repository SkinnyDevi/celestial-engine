cmake_minimum_required(VERSION 3.23)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

project(CelestialBodyEngine)

set(CMAKE_OSX_DEPLOYMENT_TARGET "26.5" CACHE STRING "Minimum macOS version")

add_executable(celengine
  main.c
  core/data/dyn_array.c
  core/data/raycast.c
  core/data/math.c
  core/cli/functions.c
  core/cli/instance_data.c
  core/cli/args/debug.c
  core/cli/args/fps.c
  core/cli/args/help.c
  core/cli/args/rendering_engine.c
  core/cli/args/registry.c
  core/cli/args/sim_date.c
  core/cli/args/time_scale.c
  core/space/orbit.c
  core/space/astro_time.c
  macos/app.m
  macos/menu/menu.m
  macos/render/camera/camera.m
  macos/render/grid/displaced_mesh.m
  macos/render/renderer.m
  macos/render/state/render_state.m
  macos/render/shape/solid_sphere.m
  macos/render/shape/orbit_ellipse.m
  macos/render/space/star.m
  macos/render/space/planet.m
  macos/render/space/moon.m
  macos/render/space/graphics.m
  macos/shaders/shader_loader.m
  macos/event/input_registry.m
  macos/event/mouse.m
  macos/debug/graphics.m
  macos/debug/overlay.m
  macos/debug/sphere_wireframe.m
  macos/debug/camera_properties.m
  macos/debug/fps_counter.m
  macos/debug/time_overlay.m
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
    macos/menu/menu.m
    macos/render/camera/camera.m
    macos/render/state/render_state.m
    macos/render/grid/displaced_mesh.m
    macos/render/renderer.m
    macos/render/space/graphics.m
    macos/render/space/star.m
    macos/render/space/planet.m
    macos/render/space/moon.m
    macos/render/shape/solid_sphere.m
    macos/render/shape/orbit_ellipse.m
    macos/shaders/shader_loader.m
    macos/event/input_registry.m
    macos/event/mouse.m
    macos/debug/graphics.m
    macos/debug/overlay.m
    macos/debug/sphere_wireframe.m
    macos/debug/camera_properties.m
    macos/debug/fps_counter.m
    macos/debug/time_overlay.m
    PROPERTIES
    COMPILE_OPTIONS "-fobjc-arc"
)

