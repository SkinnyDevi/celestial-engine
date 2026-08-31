#import "overlay.h"
#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>

#define DEBUG_OVERLAY_MAX_PANELS 8
#define DEBUG_OVERLAY_MAX_FIELDS 16

typedef struct {
  char title[64];
  float x;
  float y;
  float width;
  float height;
  float alpha;
  DebugOverlayField fields[DEBUG_OVERLAY_MAX_FIELDS];
  size_t fieldCount;
} DebugPanel;

struct DebugOverlay {
  NSWindow *window;
  NSView *view;
  bool visible;
  DebugPanel panels[DEBUG_OVERLAY_MAX_PANELS];
  size_t panelCount;
};

@interface DebugOverlayView : NSView
@property(nonatomic, assign) struct DebugOverlay *overlay;
@end

static void debug_draw_panel(NSView *hostView, DebugPanel *panel);

@implementation DebugOverlayView
- (void)drawRect:(NSRect)dirtyRect {
  [super drawRect:dirtyRect];

  if (!self.overlay || !self.overlay->visible) {
    return;
  }

  for (size_t i = 0; i < self.overlay->panelCount; ++i) {
    debug_draw_panel(self, &self.overlay->panels[i]);
  }
}
@end

static NSColor *debug_color_for_alpha(float alpha) {
  return [NSColor colorWithCalibratedRed:0.08f
                                   green:0.10f
                                    blue:0.14f
                                   alpha:alpha];
}

static NSFont *debug_font(void) {
  return [NSFont systemFontOfSize:11.0 weight:NSFontWeightMedium];
}

static void debug_clear_panel_fields(DebugPanel *panel) {
  if (!panel) {
    return;
  }

  for (size_t i = 0; i < panel->fieldCount; ++i) {
    free((void *)panel->fields[i].label);
    panel->fields[i].label = NULL;
    free((void *)panel->fields[i].value);
    panel->fields[i].value = NULL;
  }
  panel->fieldCount = 0;
}

static void debug_draw_panel(NSView *hostView, DebugPanel *panel) {
  if (!hostView || !panel) {
    return;
  }

  NSRect frame = NSMakeRect(panel->x, panel->y, panel->width, panel->height);
  NSBezierPath *background = [NSBezierPath bezierPathWithRoundedRect:frame
                                                             xRadius:8.0
                                                             yRadius:8.0];
  [debug_color_for_alpha(panel->alpha) setFill];
  [background fill];

  NSRect titleRect = NSMakeRect(frame.origin.x + 10.0,
                                frame.origin.y + frame.size.height - 20.0,
                                frame.size.width - 20.0, 16.0);
  NSDictionary *titleAttributes = @{
    NSFontAttributeName : debug_font(),
    NSForegroundColorAttributeName : [NSColor whiteColor]
  };
  [@(panel->title) drawInRect:titleRect withAttributes:titleAttributes];

  CGFloat rowY = frame.origin.y + frame.size.height - 34.0;
  for (size_t i = 0; i < panel->fieldCount; ++i) {
    if (i >= DEBUG_OVERLAY_MAX_FIELDS) {
      break;
    }

    DebugOverlayField *field = &panel->fields[i];
    NSString *label = [NSString stringWithUTF8String:field->label];
    NSString *value = [NSString stringWithUTF8String:field->value];
    NSString *line = [NSString stringWithFormat:@"%@: %@", label, value];

    NSDictionary *attrs = @{
      NSFontAttributeName : debug_font(),
      NSForegroundColorAttributeName : [NSColor colorWithWhite:0.92 alpha:1.0]
    };
    NSRect valueRect =
        NSMakeRect(frame.origin.x + 10.0, rowY, frame.size.width - 20.0, 14.0);
    [line drawInRect:valueRect withAttributes:attrs];
    rowY -= 16.0;
  }
}

DebugOverlay *debug_overlay_create(void *window) {
  DebugOverlay *overlay = calloc(1, sizeof(DebugOverlay));
  if (!overlay) {
    return NULL;
  }

  overlay->window = (__bridge NSWindow *)window;
  overlay->visible = true;

  if (overlay->window && overlay->window.contentView) {
    DebugOverlayView *view = [[DebugOverlayView alloc]
        initWithFrame:overlay->window.contentView.bounds];
    view.overlay = overlay;
    view.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
    view.wantsLayer = YES;
    view.layer.backgroundColor = CGColorGetConstantColor(kCGColorClear);
    view.layer.zPosition = 1000.0f;
    view.layer.masksToBounds = NO;
    view.layer.opaque = NO;
    [overlay->window.contentView addSubview:view];
    overlay->view = view;
  }

  return overlay;
}

void debug_overlay_destroy(DebugOverlay *overlay) {
  if (!overlay) {
    return;
  }

  debug_overlay_clear(overlay);

  if (overlay->view) {
    [overlay->view removeFromSuperview];
    overlay->view = nil;
  }

  free(overlay);
}

void debug_overlay_clear(DebugOverlay *overlay) {
  if (!overlay) {
    return;
  }

  for (size_t i = 0; i < overlay->panelCount; ++i) {
    debug_clear_panel_fields(&overlay->panels[i]);
  }
  overlay->panelCount = 0;
  if (overlay->view) {
    [overlay->view setNeedsDisplay:YES];
  }
}

void debug_overlay_add_panel(DebugOverlay *overlay, const char *title, float x,
                             float y, float width, float height, float alpha,
                             const DebugOverlayField *fields,
                             size_t fieldCount) {
  if (!overlay || !title || !fields || fieldCount == 0) {
    return;
  }

  if (overlay->panelCount >= DEBUG_OVERLAY_MAX_PANELS) {
    return;
  }

  DebugPanel *panel = &overlay->panels[overlay->panelCount++];
  snprintf(panel->title, sizeof(panel->title), "%s", title);
  panel->x = x;
  panel->y = y;
  panel->width = width;
  panel->height = height;
  panel->alpha = alpha;
  panel->fieldCount = fieldCount < DEBUG_OVERLAY_MAX_FIELDS
                          ? fieldCount
                          : DEBUG_OVERLAY_MAX_FIELDS;

  for (size_t i = 0; i < panel->fieldCount; ++i) {
    panel->fields[i].label = strdup(fields[i].label ? fields[i].label : "");
    panel->fields[i].value = strdup(fields[i].value ? fields[i].value : "");
  }

  if (overlay->view) {
    [overlay->view setNeedsDisplay:YES];
  }
}

void debug_overlay_set_visible(DebugOverlay *overlay, bool visible) {
  if (!overlay) {
    return;
  }

  overlay->visible = visible;
  if (overlay->view) {
    [overlay->view setNeedsDisplay:YES];
  }
}

void debug_overlay_update_camera(DebugOverlay *overlay, const Camera *camera) {
  if (!overlay || !camera || !overlay->visible) {
    return;
  }

  DebugOverlayField cameraFields[] = {
      {"azimuth", ""}, {"elevation", ""}, {"zoom", ""},
      {"center", ""},  {"position", ""},
  };

  char azBuf[32];
  char elBuf[32];
  char distBuf[32];
  char centerBuf[64];
  char posBuf[64];

  simd_float3 pos = camera_orbit_position(camera);

  snprintf(azBuf, sizeof(azBuf), "%0.3f", camera->azimuth);
  snprintf(elBuf, sizeof(elBuf), "%0.3f", camera->elevation);
  snprintf(distBuf, sizeof(distBuf), "%0.3f", camera->zoom);
  snprintf(centerBuf, sizeof(centerBuf), "(%0.2f, %0.2f, %0.2f)",
           camera->center.x, camera->center.y, camera->center.z);
  snprintf(posBuf, sizeof(posBuf), "(%0.2f, %0.2f, %0.2f)", pos.x, pos.y,
           pos.z);

  cameraFields[0].value = strdup(azBuf);
  cameraFields[1].value = strdup(elBuf);
  cameraFields[2].value = strdup(distBuf);
  cameraFields[3].value = strdup(centerBuf);
  cameraFields[4].value = strdup(posBuf);

  debug_overlay_add_panel(overlay, "Camera", 20.0f, 20.0f, 230.0f, 136.0f, 0.6f,
                          cameraFields, 5);

  for (size_t i = 0; i < 5; ++i) {
    free((void *)cameraFields[i].value);
    cameraFields[i].value = NULL;
  }
}
