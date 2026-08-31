#ifndef MACOS_SHADER_LOADER_H
#define MACOS_SHADER_LOADER_H

#include "core/log/log.h"
#include "macos/render_handler.h"

const char *load_shader_file(const char *shader_name);
void compile_grid_shader_lib(RenderState *state, const char *shader_name);

#endif