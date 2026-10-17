#import "render_state.h"

#import "core/cli/instance_data.h"
#import "core/data/dyn_array.h"
#import "core/data/loader/data_loader.h"
#import "core/log/log.h"
#import "core/space/astro_time.h"
#import "core/space/star.h"

#import "macos/debug/overlay.h"
#import "macos/event/input_registry.h"
#import "macos/render/space/moon.h"
#import "macos/render/space/planet.h"
#import "macos/render/space/star.h"

#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>

typedef struct {
  NSWindow *window;
  CAMetalLayer *metalLayer;
  id<MTLCommandQueue> commandQueue;
  id<MTLBuffer> vec3Buffer;
  id<MTLBuffer> uniformBuffer;
  id<MTLLibrary> grid_shader_lib;
  id<MTLRenderPipelineState> pipelineState;
  id<MTLTexture> depthTexture;
  id<MTLDepthStencilState> depthStencilState;
  DebugOverlay *camera_debug_overlay;
  DebugOverlay *fps_counter_overlay;
  DebugOverlay *time_overlay;
  DebugOverlay *celestial_bodies_overlay;
  size_t rendered_star_count;
  size_t rendered_planet_count;
  size_t rendered_moon_count;
  Camera camera;
  bool dragging;
  NSPoint lastMouse;
  NSUInteger gridVertexCount;
  id<MTLRenderPipelineState> starPipelineState;
  id<MTLDepthStencilState> starDepthState;
  id<MTLBuffer> starInstanceBuffer;
  size_t starInstanceCount;
  DynamicArray stars;
  DynamicArray planets;
  DynamicArray moons;
  InputRegistry *input_registry;
  bool gridVisible;
  bool bodyLabelsVisible;
  AstronomicalTime sim_time;
  FollowType followed_type;
  void *followed_body;
  FollowType grid_followed_type;
  void *grid_followed_body;
} RenderStateImpl;

RenderState *RenderState_Create(void) {
  RenderStateImpl *impl = calloc(1, sizeof(RenderStateImpl));
  if (!impl)
    return NULL;

  impl->dragging = false;
  impl->lastMouse = NSZeroPoint;
  impl->gridVertexCount = 0;
  impl->gridVisible = true;
  impl->bodyLabelsVisible = true;
  impl->window = nil;
  impl->metalLayer = nil;
  impl->commandQueue = nil;
  impl->vec3Buffer = nil;
  impl->uniformBuffer = nil;
  impl->grid_shader_lib = nil;
  impl->pipelineState = nil;
  impl->starPipelineState = nil;
  impl->starDepthState = nil;
  impl->starInstanceBuffer = nil;
  impl->starInstanceCount = 0;
  impl->depthTexture = nil;
  impl->depthStencilState = nil;
  impl->camera_debug_overlay = nil;
  impl->fps_counter_overlay = nil;
  impl->time_overlay = nil;
  impl->celestial_bodies_overlay = nil;
  impl->rendered_star_count = 0;
  impl->rendered_planet_count = 0;
  impl->rendered_moon_count = 0;
  impl->input_registry = nil;
  impl->sim_time = (AstronomicalTime){0, 0, 0};
  impl->followed_type = FOLLOW_NONE;
  impl->followed_body = NULL;
  impl->grid_followed_type = FOLLOW_NONE;
  impl->grid_followed_body = NULL;
  camera_init(&impl->camera);

  return (RenderState *)impl;
}

void RenderState_Init(RenderState *state, void *window) {
  if (!state || !window)
    return;

  RenderStateImpl *impl = (RenderStateImpl *)state;
  impl->window = (__bridge NSWindow *)window;
  impl->metalLayer = [CAMetalLayer layer];
  impl->metalLayer.device = MTLCreateSystemDefaultDevice();
  impl->metalLayer.pixelFormat = MTLPixelFormatBGRA8Unorm;
  impl->metalLayer.framebufferOnly = YES;
  [impl->window.contentView.layer addSublayer:impl->metalLayer];

  impl->commandQueue = [impl->metalLayer.device newCommandQueue];
  impl->grid_shader_lib = [impl->metalLayer.device newDefaultLibrary];
  impl->camera_debug_overlay = NULL;
  impl->fps_counter_overlay = NULL;
  impl->time_overlay = NULL;
  impl->celestial_bodies_overlay = NULL;
  impl->rendered_star_count = 0;
  impl->rendered_planet_count = 0;
  impl->rendered_moon_count = 0;
  camera_init(&impl->camera);
  impl->dragging = false;
  impl->lastMouse = NSZeroPoint;
  impl->gridVertexCount = 0;
  DynamicArray_init(&impl->stars, sizeof(void *));
  DynamicArray_init(&impl->planets, sizeof(void *));
  DynamicArray_init(&impl->moons, sizeof(void *));
  impl->input_registry = InputRegistry_Create();
}

void RenderState_Destroy(RenderState *state) {
  if (!state)
    return;

  RenderStateImpl *impl = (RenderStateImpl *)state;
  impl->vec3Buffer = nil;
  impl->uniformBuffer = nil;
  impl->grid_shader_lib = nil;
  impl->pipelineState = nil;
  impl->starPipelineState = nil;
  impl->starDepthState = nil;
  impl->starInstanceBuffer = nil;
  impl->depthTexture = nil;
  impl->depthStencilState = nil;
  impl->commandQueue = nil;
  impl->metalLayer = nil;
  impl->window = nil;
  debug_overlay_destroy(impl->camera_debug_overlay);
  impl->camera_debug_overlay = nil;
  debug_overlay_destroy(impl->fps_counter_overlay);
  impl->fps_counter_overlay = nil;
  debug_overlay_destroy(impl->time_overlay);
  impl->time_overlay = nil;
  debug_overlay_destroy(impl->celestial_bodies_overlay);
  impl->celestial_bodies_overlay = nil;
  DynamicArray_free(&impl->stars);
  DynamicArray_free(&impl->planets);
  DynamicArray_free(&impl->moons);
  InputRegistry_Destroy(impl->input_registry);
  free(state);
}

void *RenderState_GetWindow(RenderState *state) {
  if (!state)
    return NULL;

  return (__bridge void *)((RenderStateImpl *)state)->window;
}

void *RenderState_GetMetalLayer(RenderState *state) {
  if (!state)
    return NULL;

  return (__bridge void *)((RenderStateImpl *)state)->metalLayer;
}

void *RenderState_GetCommandQueue(RenderState *state) {
  if (!state)
    return NULL;

  return (__bridge void *)((RenderStateImpl *)state)->commandQueue;
}

void *RenderState_GetVec3Buffer(RenderState *state) {
  if (!state)
    return NULL;

  return (__bridge void *)((RenderStateImpl *)state)->vec3Buffer;
}

void *RenderState_GetUniformBuffer(RenderState *state) {
  if (!state)
    return NULL;

  return (__bridge void *)((RenderStateImpl *)state)->uniformBuffer;
}

void *RenderState_GetGridShaderLib(RenderState *state) {
  if (!state)
    return NULL;

  return (__bridge void *)((RenderStateImpl *)state)->grid_shader_lib;
}

void *RenderState_GetPipelineState(RenderState *state) {
  if (!state)
    return NULL;

  return (__bridge void *)((RenderStateImpl *)state)->pipelineState;
}

void *RenderState_GetDepthTexture(RenderState *state) {
  if (!state)
    return NULL;

  return (__bridge void *)((RenderStateImpl *)state)->depthTexture;
}

void *RenderState_GetDepthStencilState(RenderState *state) {
  if (!state)
    return NULL;

  return (__bridge void *)((RenderStateImpl *)state)->depthStencilState;
}

void *RenderState_GetStarPipelineState(RenderState *state) {
  if (!state)
    return NULL;

  return (__bridge void *)((RenderStateImpl *)state)->starPipelineState;
}

void RenderState_SetStarPipelineState(RenderState *state, void *pipelineState) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->starPipelineState =
      (__bridge id<MTLRenderPipelineState>)pipelineState;
}

void *RenderState_GetStarDepthState(RenderState *state) {
  if (!state)
    return NULL;

  return (__bridge void *)((RenderStateImpl *)state)->starDepthState;
}

void RenderState_SetStarDepthState(RenderState *state, void *depthState) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->starDepthState =
      (__bridge id<MTLDepthStencilState>)depthState;
}

void *RenderState_GetStarInstanceBuffer(RenderState *state) {
  if (!state)
    return NULL;

  return (__bridge void *)((RenderStateImpl *)state)->starInstanceBuffer;
}

void RenderState_SetStarInstanceBuffer(RenderState *state, void *buffer) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->starInstanceBuffer =
      (__bridge id<MTLBuffer>)buffer;
}

size_t RenderState_GetStarInstanceCount(RenderState *state) {
  if (!state)
    return 0;

  return ((RenderStateImpl *)state)->starInstanceCount;
}

void RenderState_SetStarInstanceCount(RenderState *state, size_t count) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->starInstanceCount = count;
}

DynamicArray *RenderState_GetStars(RenderState *state) {
  if (!state)
    return NULL;

  return &((RenderStateImpl *)state)->stars;
}

DynamicArray *RenderState_GetPlanets(RenderState *state) {
  if (!state)
    return NULL;

  return &((RenderStateImpl *)state)->planets;
}

DynamicArray *RenderState_GetMoons(RenderState *state) {
  if (!state)
    return NULL;

  return &((RenderStateImpl *)state)->moons;
}

InputRegistry *RenderState_GetInputRegistry(RenderState *state) {
  if (!state)
    return NULL;

  return ((RenderStateImpl *)state)->input_registry;
}

AstronomicalTime *RenderState_GetSimTime(RenderState *state) {
  if (!state)
    return NULL;

  return &((RenderStateImpl *)state)->sim_time;
}

DebugOverlay *RenderState_GetCameraDebugOverlay(RenderState *state) {
  if (!state)
    return NULL;

  return ((RenderStateImpl *)state)->camera_debug_overlay;
}

DebugOverlay *RenderState_GetFPSCounterOverlay(RenderState *state) {
  if (!state)
    return NULL;

  return ((RenderStateImpl *)state)->fps_counter_overlay;
}

DebugOverlay *RenderState_GetTimeOverlay(RenderState *state) {
  if (!state)
    return NULL;

  return ((RenderStateImpl *)state)->time_overlay;
}

DebugOverlay *RenderState_GetCelestialBodiesOverlay(RenderState *state) {
  if (!state)
    return NULL;

  return ((RenderStateImpl *)state)->celestial_bodies_overlay;
}

size_t RenderState_GetRenderedStarCount(const RenderState *state) {
  if (!state)
    return 0;
  return ((const RenderStateImpl *)state)->rendered_star_count;
}

void RenderState_SetRenderedStarCount(RenderState *state, size_t count) {
  if (!state)
    return;
  ((RenderStateImpl *)state)->rendered_star_count = count;
}

size_t RenderState_GetRenderedPlanetCount(const RenderState *state) {
  if (!state)
    return 0;
  return ((const RenderStateImpl *)state)->rendered_planet_count;
}

void RenderState_SetRenderedPlanetCount(RenderState *state, size_t count) {
  if (!state)
    return;
  ((RenderStateImpl *)state)->rendered_planet_count = count;
}

size_t RenderState_GetRenderedMoonCount(const RenderState *state) {
  if (!state)
    return 0;
  return ((const RenderStateImpl *)state)->rendered_moon_count;
}

void RenderState_SetRenderedMoonCount(RenderState *state, size_t count) {
  if (!state)
    return;
  ((RenderStateImpl *)state)->rendered_moon_count = count;
}

Camera *RenderState_GetCamera(RenderState *state) {
  if (!state)
    return NULL;

  return &((RenderStateImpl *)state)->camera;
}

void RenderState_SetVec3Buffer(RenderState *state, void *buffer) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->vec3Buffer = (__bridge id<MTLBuffer>)buffer;
}

void RenderState_SetUniformBuffer(RenderState *state, void *buffer) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->uniformBuffer = (__bridge id<MTLBuffer>)buffer;
}

void RenderState_SetGridShaderLib(RenderState *state, void *library) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->grid_shader_lib =
      (__bridge id<MTLLibrary>)library;
}

void RenderState_SetPipelineState(RenderState *state, void *pipelineState) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->pipelineState =
      (__bridge id<MTLRenderPipelineState>)pipelineState;
}

void RenderState_SetDepthTexture(RenderState *state, void *texture) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->depthTexture = (__bridge id<MTLTexture>)texture;
}

void RenderState_SetDepthStencilState(RenderState *state,
                                      void *depthStencilState) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->depthStencilState =
      (__bridge id<MTLDepthStencilState>)depthStencilState;
}

void RenderState_SetSimTime(RenderState *state, AstronomicalTime *time) {
  if (!state || !time)
    return;

  ((RenderStateImpl *)state)->sim_time = *time;
}

void RenderState_SetCameraDebugOverlay(RenderState *state,
                                       DebugOverlay *overlay) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->camera_debug_overlay = overlay;
}

void RenderState_SetFPSCounterOverlay(RenderState *state,
                                      DebugOverlay *overlay) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->fps_counter_overlay = overlay;
}

void RenderState_SetTimeOverlay(RenderState *state, DebugOverlay *overlay) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->time_overlay = overlay;
}

void RenderState_SetCelestialBodiesOverlay(RenderState *state,
                                           DebugOverlay *overlay) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->celestial_bodies_overlay = overlay;
}

void RenderState_SetVertexCount(RenderState *state, unsigned long count) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->gridVertexCount = (NSUInteger)count;
}

unsigned long RenderState_GetVertexCount(const RenderState *state) {
  if (!state)
    return 0;

  return (unsigned long)((const RenderStateImpl *)state)->gridVertexCount;
}

void RenderState_SetDragging(RenderState *state, bool dragging) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->dragging = dragging;
}

bool RenderState_IsDragging(const RenderState *state) {
  if (!state)
    return false;

  return ((const RenderStateImpl *)state)->dragging;
}

void RenderState_SetLastMouse(RenderState *state, double x, double y) {
  if (!state)
    return;

  ((RenderStateImpl *)state)->lastMouse = NSMakePoint(x, y);
}

void RenderState_GetLastMouse(const RenderState *state, double *x, double *y) {
  if (!state || !x || !y)
    return;

  *x = ((const RenderStateImpl *)state)->lastMouse.x;
  *y = ((const RenderStateImpl *)state)->lastMouse.y;
}

void RenderState_SetGridVisible(RenderState *state, bool visible) {
  if (!state)
    return;
  ((RenderStateImpl *)state)->gridVisible = visible;
}

bool RenderState_IsGridVisible(const RenderState *state) {
  if (!state)
    return false;
  return ((const RenderStateImpl *)state)->gridVisible;
}

void RenderState_SetBodyLabelsVisible(RenderState *state, bool visible) {
  if (!state)
    return;
  ((RenderStateImpl *)state)->bodyLabelsVisible = visible;
}

bool RenderState_AreBodyLabelsVisible(const RenderState *state) {
  if (!state)
    return false;
  return ((const RenderStateImpl *)state)->bodyLabelsVisible;
}

void RenderState_SetFollowedBody(RenderState *state, FollowType type,
                                 void *body) {
  if (!state)
    return;
  RenderStateImpl *impl = (RenderStateImpl *)state;
  impl->followed_type = type;
  impl->followed_body = body;
  const char *name = "Unknown";
  const char *id_str = "Unknown";
  if (type == FOLLOW_STAR) {
    MTLStarGraphicsClass *star = (MTLStarGraphicsClass *)body;
    if (star && star->body) {
      name = star->body->name;
      id_str = star->body->body_id;
    }
  } else if (type == FOLLOW_PLANET) {
    MTLPlanetGraphicsClass *planet = (MTLPlanetGraphicsClass *)body;
    if (planet && planet->body) {
      name = planet->body->name;
      id_str = planet->body->body_id;
    }
  } else if (type == FOLLOW_MOON) {
    MTLMoonGraphicsClass *moon = (MTLMoonGraphicsClass *)body;
    if (moon && moon->body) {
      name = moon->body->name;
      id_str = moon->body->body_id;
    }
  }
  LOG_DEBUG("Body followed: %s (%s)", name, id_str);
}

void RenderState_ClearFollowedBody(RenderState *state) {
  if (!state)
    return;
  RenderStateImpl *impl = (RenderStateImpl *)state;
  impl->followed_type = FOLLOW_NONE;
  impl->followed_body = NULL;
}

bool RenderState_IsFollowing(const RenderState *state) {
  if (!state)
    return false;
  return ((const RenderStateImpl *)state)->followed_type != FOLLOW_NONE &&
         ((const RenderStateImpl *)state)->followed_body != NULL;
}

FollowType RenderState_GetFollowedType(const RenderState *state) {
  if (!state)
    return FOLLOW_NONE;
  return ((const RenderStateImpl *)state)->followed_type;
}

void *RenderState_GetFollowedBody(const RenderState *state) {
  if (!state)
    return NULL;
  return ((const RenderStateImpl *)state)->followed_body;
}

void RenderState_SetGridFollowedBody(RenderState *state, FollowType type,
                                     void *body) {
  if (!state)
    return;
  RenderStateImpl *impl = (RenderStateImpl *)state;
  impl->grid_followed_type = type;
  impl->grid_followed_body = body;
}

void RenderState_ClearGridFollowedBody(RenderState *state) {
  if (!state)
    return;
  RenderStateImpl *impl = (RenderStateImpl *)state;
  impl->grid_followed_type = FOLLOW_NONE;
  impl->grid_followed_body = NULL;
}

FollowType RenderState_GetGridFollowedType(const RenderState *state) {
  if (!state)
    return FOLLOW_NONE;
  return ((const RenderStateImpl *)state)->grid_followed_type;
}

void *RenderState_GetGridFollowedBody(const RenderState *state) {
  if (!state)
    return NULL;
  return ((const RenderStateImpl *)state)->grid_followed_body;
}

void renderer_save_orbits_state(RenderState *state, DynamicArray *planets,
                                DynamicArray *moons, DynamicArray *orbits_arr,
                                LoadedSimulationBodies *bodies,
                                void (^add_orbit)(CelestialBody_Orbit *)) {
  for (size_t i = 0; i < DynamicArray_length(planets); i++) {
    MTLPlanetGraphicsClass *p;
    DynamicArray_get(planets, i, &p);
    add_orbit(p->body->orbit);
  }

  for (size_t i = 0; i < DynamicArray_length(moons); i++) {
    MTLMoonGraphicsClass *m;
    DynamicArray_get(moons, i, &m);
    add_orbit(m->body->orbit);
  }

  size_t count = DynamicArray_length(orbits_arr);
  for (size_t i = 0; i < count; i++) {
    CelestialBody_Orbit *o;
    DynamicArray_get(orbits_arr, i, &o);
    CelestialBody_Orbit *orb_copy = calloc(1, sizeof(CelestialBody_Orbit));
    *orb_copy = *o;
    DynamicArray_push(&bodies->orbits, &orb_copy);
  }
}

void renderer_save_stars_state(RenderState *state,
                               LoadedSimulationBodies *bodies,
                               DynamicArray *stars) {
  size_t count = DynamicArray_length(stars);
  for (size_t i = 0; i < count; i++) {
    MTLStarGraphicsClass *s;
    DynamicArray_get(stars, i, &s);
    CelestialBody_Star *star_copy = calloc(1, sizeof(CelestialBody_Star));
    *star_copy = *(s->body);
    DynamicArray_push(&bodies->stars, &star_copy);
  }
}

void renderer_save_planets_state(RenderState *state,
                                 LoadedSimulationBodies *bodies,
                                 DynamicArray *orbits_arr,
                                 DynamicArray *planets) {
  size_t count = DynamicArray_length(planets);
  for (size_t i = 0; i < count; i++) {
    MTLPlanetGraphicsClass *p;
    DynamicArray_get(planets, i, &p);
    CelestialBody_Planet *planet_copy = calloc(1, sizeof(CelestialBody_Planet));
    *planet_copy = *(p->body);

    if (p->body->orbit) {
      for (size_t j = 0; j < DynamicArray_length(orbits_arr); j++) {
        CelestialBody_Orbit *o;
        DynamicArray_get(orbits_arr, j, &o);

        if (o == p->body->orbit) {
          CelestialBody_Orbit *body_orb;
          DynamicArray_get(&bodies->orbits, j, &body_orb);
          planet_copy->orbit = body_orb;
          break;
        }
      }
    }
    DynamicArray_push(&bodies->planets, &planet_copy);
  }
}

void renderer_save_moons_state(RenderState *state,
                               LoadedSimulationBodies *bodies,
                               DynamicArray *orbits_arr, DynamicArray *moons) {
  size_t count = DynamicArray_length(moons);
  for (size_t i = 0; i < count; i++) {
    MTLMoonGraphicsClass *m;
    DynamicArray_get(moons, i, &m);
    CelestialBody_Moon *moon_copy = calloc(1, sizeof(CelestialBody_Moon));
    *moon_copy = *(m->body);

    if (m->body->orbit) {
      for (size_t j = 0; j < DynamicArray_length(orbits_arr); j++) {
        CelestialBody_Orbit *o;
        DynamicArray_get(orbits_arr, j, &o);

        if (o == m->body->orbit) {
          CelestialBody_Orbit *body_orb;
          DynamicArray_get(&bodies->orbits, j, &body_orb);
          moon_copy->orbit = body_orb;
          break;
        }
      }
    }
    DynamicArray_push(&bodies->moons, &moon_copy);
  }
}

void renderer_save_astro_time_state(RenderState *state,
                                    LoadedSimulationBodies *bodies) {
  AstronomicalTime *sim_time = RenderState_GetSimTime(state);
  int year, month, day, hour, minute, second;
  jd_to_gregorian(sim_time->current_jd, &year, &month, &day, &hour, &minute,
                  &second);

  bodies->sim_date.time.tm_year = year - 1900;
  bodies->sim_date.time.tm_mon = month - 1;
  bodies->sim_date.time.tm_mday = day;
  bodies->sim_date.time.tm_hour = hour;
  bodies->sim_date.time.tm_min = minute;
  bodies->sim_date.time.tm_sec = second;
  bodies->sim_date.has_set_date = true;
}

void RenderHandler_SaveStateToInstanceData(RendererHandle handle) {
  RenderState *state = (RenderState *)handle;
  if (!state)
    return;

  DynamicArray *stars = RenderState_GetStars(state);
  DynamicArray *planets = RenderState_GetPlanets(state);
  DynamicArray *moons = RenderState_GetMoons(state);

  LoadedSimulationBodies bodies;
  loaded_simulation_bodies_init(&bodies);
  renderer_save_astro_time_state(state, &bodies);

  __block DynamicArray orbits_arr;
  DynamicArray_init(&orbits_arr, sizeof(CelestialBody_Orbit *));

  // Add all unique orbits
  void (^add_orbit)(CelestialBody_Orbit *) = ^(CelestialBody_Orbit *orbit) {
    if (!orbit)
      return;

    for (size_t i = 0; i < DynamicArray_length(&orbits_arr); i++) {
      CelestialBody_Orbit *o;
      DynamicArray_get(&orbits_arr, i, &o);

      if (o == orbit)
        return;
    }

    DynamicArray_push(&orbits_arr, &orbit);
  };

  renderer_save_orbits_state(state, planets, moons, &orbits_arr, &bodies,
                             add_orbit);
  renderer_save_stars_state(state, &bodies, stars);
  renderer_save_planets_state(state, &bodies, &orbits_arr, planets);
  renderer_save_moons_state(state, &bodies, &orbits_arr, moons);

  DynamicArray_free(&orbits_arr);

  _cli_arg_set_sim_bodies(&bodies);
}