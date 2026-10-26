#ifndef MACOS_RENDER_SPACE_STAR_H
#define MACOS_RENDER_SPACE_STAR_H

#include "core/data/loader/data_loader.h"
#include "core/data/math.h"
#include "core/space/star.h"

#include "macos/render/state/render_state.h"

#include "macos/render/shape/vertex.h"
#include "macos/shaders/generic_star_texture.h"
#include <simd/simd.h>

typedef struct {
  PackedFloat3 position; // 12 bytes: camera-relative pos in render units
  float radius;          // 4 bytes: base physical radius in render units
  simd_float4 color;     // 16 bytes: spectral RGBA color
} StarInstance;

typedef struct {
  simd_float4x4 viewMatrix;
  simd_float4x4 projectionMatrix;
  float minSizeFactor;
  float time;
  float _pad[2];
} StarUniforms;

typedef struct MTLStarGraphicsClass {
  CelestialBody_Star *body;

  void *vertex_buffer;
  void *index_buffer;
  int index_count;

  void *pipeline_state;
} MTLStarGraphicsClass;

MTLStarGraphicsClass *MTLStarGraphics_Create(CelestialBody_Star *body);
void MTLStarGraphicsClass_draw(MTLStarGraphicsClass *star,
                               RenderState *render_state, void *encoder_ptr);
void MTLStarGraphicsClass_init(MTLStarGraphicsClass *star,
                               RenderState *render_state);
void MTLStarGraphics_Destroy(MTLStarGraphicsClass *star_graphics);

void init_celestial_body_stars(RenderState *render_state);
void load_celestial_body_stars_from_file(RenderState *render_state,
                                         LoadedSimulationBodies *bodies);

void create_star_render_pipeline(RenderState *state);
void init_star_instance_buffer(RenderState *state);
void draw_stars_instanced(RenderState *state, void *encoder_ptr);
uint32_t get_rendered_stars_count(void);

void star_get_candidate_labels(
    RenderState *state, simd_double3 cam_world_pos,
    void (^callback)(MTLStarGraphicsClass *star, simd_double3 world_pos,
                     float radius_m, const char *name, simd_float4 color));
void star_check_intersect(
    RenderState *state, simd_float3 ray_origin,
    void (^check_intersect)(simd_float3 pos, float base_radius,
                            float click_radius, void *star, FollowType type));

#endif