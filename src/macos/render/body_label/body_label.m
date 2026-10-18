#import "body_label.h"
#import <Cocoa/Cocoa.h>
#import <simd/simd.h>

#import "core/data/math.h"
#import "core/log/log.h"
#import "core/space/units.h"

#import "macos/render/camera/camera.h"
#import "macos/render/space/moon.h"
#import "macos/render/space/planet.h"
#import "macos/render/space/star.h"

#define MAX_ACTIVE_LABELS 1024
#define LABEL_DISAPPEAR_DIST_FACTOR 10000.0f
#define LABEL_FULL_OPACITY_DIST_FACTOR 400.0f
#define LABEL_MIN_DIST_FACTOR 1e-4f // distance before label is hidden
#define LABEL_MIN_VISUAL_SIZE_FACTOR 0.0018f

simd_float4 get_planet_color(PlanetClass planet_class);
simd_float4 get_star_color(StarSpectralType spectral_type);
simd_float4 get_moon_color(MoonClass moon_class);

typedef struct {
  char name[48];
  float screen_x;
  float screen_y_top;
  float alpha;
  simd_float4 color;
  float depth;
  void *body_ptr;
  FollowType type;
  float base_radius;
  simd_float3 body_pos;
  NSRect badge_rect;
} BodyLabelItem;

@interface BodyLabelView : NSView
@property(nonatomic, assign) BOOL visible;
@property(nonatomic, readonly) const BodyLabelItem *labels;
@property(nonatomic, readonly) size_t labelCount;
- (void)updateLabels:(const BodyLabelItem *)items count:(size_t)count;
@end

@implementation BodyLabelView {
  BodyLabelItem _labels[MAX_ACTIVE_LABELS];
  size_t _labelCount;
}

- (instancetype)initWithFrame:(NSRect)frame {
  self = [super initWithFrame:frame];
  if (self) {
    self.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
    self.wantsLayer = YES;
    self.layer.backgroundColor = CGColorGetConstantColor(kCGColorClear);
    self.layer.zPosition = 900.0f;
    self.layer.masksToBounds = NO;
    self.layer.opaque = NO;
    self.visible = YES;
    _labelCount = 0;
  }
  return self;
}

- (NSView *)hitTest:(NSPoint)point {
  // Pass all mouse clicks through so overlay never interferes with Cocoa event
  // dispatch
  return nil;
}

- (const BodyLabelItem *)labels {
  return _labels;
}

- (size_t)labelCount {
  return _labelCount;
}

- (void)updateLabels:(const BodyLabelItem *)items count:(size_t)count {
  size_t toCopy = MIN(count, (size_t)MAX_ACTIVE_LABELS);
  if (toCopy > 0 && items) {
    memcpy(_labels, items, toCopy * sizeof(BodyLabelItem));
  }
  _labelCount = toCopy;
  [self setNeedsDisplay:YES];
}

- (void)drawRect:(NSRect)dirtyRect {
  [super drawRect:dirtyRect];

  if (!self.visible || _labelCount == 0)
    return;

  NSFont *font = [NSFont systemFontOfSize:11.0 weight:NSFontWeightMedium];
  CGFloat dotRadius = 3.0;
  CGFloat dotDiameter = dotRadius * 2.0;
  CGFloat paddingH = 8.0;
  CGFloat dotSpacing = 5.0;

  for (size_t i = 0; i < _labelCount; i++) {
    const BodyLabelItem *item = &_labels[i];
    if (item->alpha <= 0.01f)
      continue;

    NSString *nameStr = [NSString stringWithUTF8String:item->name];
    if (!nameStr || [nameStr length] == 0)
      continue;

    NSColor *textColor = [NSColor colorWithCalibratedWhite:0.95f
                                                     alpha:item->alpha];
    NSDictionary *attrs = @{
      NSFontAttributeName : font,
      NSForegroundColorAttributeName : textColor
    };

    NSSize textSize = [nameStr sizeWithAttributes:attrs];
    NSRect badgeRect = item->badge_rect;
    CGFloat originX = badgeRect.origin.x;
    CGFloat originY = badgeRect.origin.y;
    CGFloat badgeHeight = badgeRect.size.height;

    // Frosted dark pill background
    NSBezierPath *bgPath =
        [NSBezierPath bezierPathWithRoundedRect:badgeRect
                                        xRadius:badgeHeight * 0.5
                                        yRadius:badgeHeight * 0.5];
    NSColor *bgColor = [NSColor colorWithCalibratedRed:0.06f
                                                 green:0.08f
                                                  blue:0.12f
                                                 alpha:0.78f * item->alpha];
    [bgColor setFill];
    [bgPath fill];

    // Subtle crisp border
    NSColor *borderColor =
        [NSColor colorWithCalibratedWhite:1.0f alpha:0.18f * item->alpha];
    [borderColor setStroke];
    bgPath.lineWidth = 1.0;
    [bgPath stroke];

    // Colored celestial indicator dot
    CGFloat dotX = originX + paddingH;
    CGFloat dotY = originY + (badgeHeight - dotDiameter) * 0.5;
    NSRect dotRect = NSMakeRect(dotX, dotY, dotDiameter, dotDiameter);
    NSBezierPath *dotPath = [NSBezierPath bezierPathWithOvalInRect:dotRect];
    NSColor *dotColor = [NSColor colorWithCalibratedRed:item->color.x
                                                  green:item->color.y
                                                   blue:item->color.z
                                                  alpha:item->alpha];
    [dotColor setFill];
    [dotPath fill];

    // Name text
    CGFloat textX = dotX + dotDiameter + dotSpacing;
    CGFloat textY = originY + (badgeHeight - textSize.height) * 0.5;
    NSRect textRect = NSMakeRect(textX, textY, textSize.width, textSize.height);
    [nameStr drawInRect:textRect withAttributes:attrs];
  }
}
@end

static BodyLabelView *g_body_label_view = nil;

void create_body_labels(void *window_ptr) {
  NSWindow *window = (__bridge NSWindow *)window_ptr;
  if (!window || !window.contentView)
    return;

  g_body_label_view =
      [[BodyLabelView alloc] initWithFrame:window.contentView.bounds];
  [window.contentView addSubview:g_body_label_view];
}

void destroy_body_labels(void) {
  if (g_body_label_view) {
    [g_body_label_view removeFromSuperview];
    g_body_label_view = nil;
  }
}

void toggle_body_labels_visibility(RenderState *state) {
  if (!state)
    return;
  bool visible = !RenderState_AreBodyLabelsVisible(state);
  RenderState_SetBodyLabelsVisible(state, visible);
  if (g_body_label_view) {
    g_body_label_view.visible = visible;
    [g_body_label_view setNeedsDisplay:YES];
  }
}

bool body_label_find_at_point(MousePoint mouse, void **out_obj,
                              FollowType *out_type, float *out_radius,
                              simd_float3 *out_center) {
  if (!g_body_label_view || !g_body_label_view.visible)
    return false;

  NSPoint pt = NSMakePoint(mouse.x, mouse.y);
  float best_depth = INFINITY;
  int best_idx = -1;

  for (size_t i = 0; i < g_body_label_view.labelCount; i++) {
    const BodyLabelItem *item = &g_body_label_view.labels[i];
    if (item->alpha < 0.15f || !item->body_ptr)
      continue;

    // Expand badge rect by 8 points on all sides for forgiving clicks
    NSRect hit_rect = NSInsetRect(item->badge_rect, -8.0, -8.0);
    if (NSPointInRect(pt, hit_rect)) {
      if (item->depth < best_depth) {
        best_depth = item->depth;
        best_idx = (int)i;
      }
    }
  }

  if (best_idx >= 0) {
    const BodyLabelItem *best = &g_body_label_view.labels[best_idx];
    if (out_obj)
      *out_obj = best->body_ptr;
    if (out_type)
      *out_type = best->type;
    if (out_radius)
      *out_radius = best->base_radius;
    if (out_center)
      *out_center = best->body_pos;
    return true;
  }

  return false;
}

static void process_body(RenderState *state, const Camera *camera,
                         simd_float3 cam_pos, simd_float4x4 view,
                         simd_float4x4 projection, float near_plane,
                         float view_width, float view_height,
                         simd_double3 world_pos, float radius_m,
                         const char *name, simd_float4 color, void *body_ptr,
                         FollowType type, BodyLabelItem *out_items,
                         size_t *item_count, size_t max_items) {
  if (!name || name[0] == '\0')
    return;

  double rel_x = world_pos.x - camera->center.x;
  double rel_y = world_pos.y - camera->center.y;
  double rel_z = world_pos.z - camera->center.z;
  simd_float3 body_pos =
      simd_make_float3((float)rel_x, (float)rel_y, (float)rel_z);

  double dx = (double)cam_pos.x - rel_x;
  double dy = (double)cam_pos.y - rel_y;
  double dz = (double)cam_pos.z - rel_z;
  double dist_sq = dx * dx + dy * dy + dz * dz;

  float base_scale = radius_m * METERS_TO_RENDER_UNITS;
  bool is_followed = (RenderState_GetFollowedBody(state) == body_ptr);

  // Quick distance rejection: if camera distance exceeds disappear threshold
  // and body is not followed
  float max_dist = LABEL_DISAPPEAR_DIST_FACTOR * base_scale;
  if (!is_followed && dist_sq > (double)(max_dist * max_dist))
    return;

  float dist = sqrtf((float)dist_sq);
  if (dist < LABEL_MIN_DIST_FACTOR * base_scale)
    return;

  float alpha = calculate_body_label_alpha(
      base_scale, dist, is_followed, camera->zoom, LABEL_DISAPPEAR_DIST_FACTOR,
      LABEL_FULL_OPACITY_DIST_FACTOR);
  if (alpha <= 0.01f)
    return;

  float min_visual_size = dist * LABEL_MIN_VISUAL_SIZE_FACTOR;
  float render_scale = fmaxf(base_scale, min_visual_size);

  float screen_x = 0.0f;
  float screen_y_top = 0.0f;
  float depth = 0.0f;

  if (!project_sphere_top(body_pos, render_scale, view, projection, near_plane,
                          view_width, view_height, &screen_x, &screen_y_top,
                          &depth))
    return;

  if (*item_count < max_items) {
    BodyLabelItem *item = &out_items[*item_count];
    const char *clean_name = name;
    if (strncmp(clean_name, "NAME ", 5) == 0)
      clean_name += 5;
    strncpy(item->name, clean_name, sizeof(item->name) - 1);
    item->name[sizeof(item->name) - 1] = '\0';
    item->screen_x = screen_x;
    item->screen_y_top = screen_y_top;
    item->alpha = alpha;
    item->color = color;
    item->depth = depth;
    item->body_ptr = body_ptr;
    item->type = type;
    item->base_radius = base_scale;
    item->body_pos = body_pos;

    // Calculate badge rectangle for both drawing and click hit testing
    NSFont *font = [NSFont systemFontOfSize:11.0 weight:NSFontWeightMedium];
    NSDictionary *attrs = @{NSFontAttributeName : font};
    NSString *nsName = [NSString stringWithUTF8String:clean_name];
    NSSize textSize = [nsName sizeWithAttributes:attrs];

    CGFloat dotRadius = 3.0;
    CGFloat dotDiameter = dotRadius * 2.0;
    CGFloat paddingH = 8.0;
    CGFloat paddingV = 4.0;
    CGFloat dotSpacing = 5.0;

    CGFloat badgeWidth =
        paddingH + dotDiameter + dotSpacing + textSize.width + paddingH;
    CGFloat badgeHeight = textSize.height + paddingV * 2.0;

    CGFloat originX = screen_x - (badgeWidth * 0.5);
    CGFloat originY = screen_y_top + 6.0;

    CGFloat margin = 6.0;
    if (originX < margin)
      originX = margin;
    if (originX + badgeWidth > view_width - margin)
      originX = view_width - badgeWidth - margin;
    if (originY + badgeHeight > view_height - margin)
      originY = view_height - badgeHeight - margin;
    if (originY < margin)
      originY = margin;

    item->badge_rect = NSMakeRect(originX, originY, badgeWidth, badgeHeight);

    (*item_count)++;
  }
}

static int compare_labels_by_depth(const void *a, const void *b) {
  const BodyLabelItem *itemA = (const BodyLabelItem *)a;
  const BodyLabelItem *itemB = (const BodyLabelItem *)b;
  if (itemA->depth > itemB->depth)
    return -1;
  if (itemA->depth < itemB->depth)
    return 1;
  return 0;
}

void update_body_labels(RenderState *state) {
  if (!g_body_label_view || !state)
    return;

  if (!RenderState_AreBodyLabelsVisible(state)) {
    if (g_body_label_view.visible) {
      g_body_label_view.visible = NO;
      [g_body_label_view setNeedsDisplay:YES];
    }
    return;
  }
  g_body_label_view.visible = YES;

  Camera *camera = RenderState_GetCamera(state);
  if (!camera)
    return;

  CGFloat view_width = g_body_label_view.bounds.size.width;
  CGFloat view_height = g_body_label_view.bounds.size.height;
  if (view_width <= 0 || view_height <= 0)
    return;

  float aspect = (float)(view_width / fmaxf(view_height, 1.0f));
  simd_float4x4 view = camera_view_matrix(camera);
  float near_plane, far_plane;
  camera_get_clipping_planes(camera, &near_plane, &far_plane);
  simd_float4x4 projection = camera_perspective(70.0f * (float)M_PI / 180.0f,
                                                aspect, near_plane, far_plane);

  simd_float3 cam_pos = camera_orbit_position(camera);

  BodyLabelItem items[MAX_ACTIVE_LABELS];
  __block size_t item_count = 0;
  BodyLabelItem *items_ptr = items;

  // Process Stars (fast candidate querying with cluster & distance pruning)
  simd_double3 cam_world_pos = simd_make_double3(
      camera->center.x + (double)cam_pos.x,
      camera->center.y + (double)cam_pos.y,
      camera->center.z + (double)cam_pos.z);

  star_get_candidate_labels(
      state, cam_world_pos,
      ^(MTLStarGraphicsClass *star, simd_double3 world_pos, float radius_m,
        const char *name, simd_float4 color) {
        process_body(state, camera, cam_pos, view, projection, near_plane,
                     (float)view_width, (float)view_height, world_pos, radius_m,
                     name, color, star, FOLLOW_STAR, items_ptr, &item_count,
                     MAX_ACTIVE_LABELS);
      });

  // Process Planets
  DynamicArray *planets = RenderState_GetPlanets(state);
  if (planets) {
    size_t planet_count = DynamicArray_length(planets);
    for (size_t i = 0; i < planet_count; i++) {
      MTLPlanetGraphicsClass *planet;
      DynamicArray_get(planets, i, &planet);
      if (!planet || !planet->body)
        continue;

      double ax = planet->body->position.x;
      double ay = planet->body->position.y;
      double az = planet->body->position.z;
      if (planet->host_star) {
        ax += planet->host_star->body->position.x;
        ay += planet->host_star->body->position.y;
        az += planet->host_star->body->position.z;
      }

      simd_double3 world_pos = simd_make_double3(ax * METERS_TO_RENDER_UNITS,
                                                 ay * METERS_TO_RENDER_UNITS,
                                                 az * METERS_TO_RENDER_UNITS);

      simd_float4 color = get_planet_color(planet->body->planet_class);
      process_body(state, camera, cam_pos, view, projection, near_plane,
                   (float)view_width, (float)view_height, world_pos,
                   (float)planet->body->radius_m, planet->body->name, color,
                   planet, FOLLOW_PLANET, items, &item_count,
                   MAX_ACTIVE_LABELS);
    }
  }

  // Process Moons
  DynamicArray *moons = RenderState_GetMoons(state);
  if (moons) {
    size_t moon_count = DynamicArray_length(moons);
    for (size_t i = 0; i < moon_count; i++) {
      MTLMoonGraphicsClass *moon;
      DynamicArray_get(moons, i, &moon);
      if (!moon || !moon->body)
        continue;

      double ax = moon->body->position.x;
      double ay = moon->body->position.y;
      double az = moon->body->position.z;
      if (moon->host_planet) {
        ax += moon->host_planet->body->position.x;
        ay += moon->host_planet->body->position.y;
        az += moon->host_planet->body->position.z;
        if (moon->host_planet->host_star) {
          ax += moon->host_planet->host_star->body->position.x;
          ay += moon->host_planet->host_star->body->position.y;
          az += moon->host_planet->host_star->body->position.z;
        }
      }

      simd_double3 world_pos = simd_make_double3(ax * METERS_TO_RENDER_UNITS,
                                                 ay * METERS_TO_RENDER_UNITS,
                                                 az * METERS_TO_RENDER_UNITS);

      simd_float4 color = get_moon_color(moon->body->moon_class);
      process_body(state, camera, cam_pos, view, projection, near_plane,
                   (float)view_width, (float)view_height, world_pos,
                   (float)moon->body->radius_m, moon->body->name, color, moon,
                   FOLLOW_MOON, items, &item_count, MAX_ACTIVE_LABELS);
    }
  }

  // Sort by depth (farther first, so closest draw on top)
  if (item_count > 1)
    qsort(items, item_count, sizeof(BodyLabelItem), compare_labels_by_depth);

  [g_body_label_view updateLabels:items count:item_count];
}
