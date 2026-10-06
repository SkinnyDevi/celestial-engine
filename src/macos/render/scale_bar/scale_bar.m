#import "scale_bar.h"
#include "core/log/log.h"
#import "core/space/units.h"

#import <Cocoa/Cocoa.h>
#import <math.h>

@interface ScaleBarView : NSView
@property(nonatomic, assign) double actual_pixels;
@property(nonatomic, copy) NSString *label_text;
@property(nonatomic, assign) BOOL visible;
@end

@implementation ScaleBarView
- (void)drawRect:(NSRect)dirtyRect {
  [super drawRect:dirtyRect];

  if (!self.visible || self.actual_pixels <= 0)
    return;

  // Background box
  NSRect frame = NSMakeRect(self.bounds.size.width - self.actual_pixels - 40.0,
                            20.0, self.actual_pixels + 20.0, 40.0);
  NSBezierPath *background = [NSBezierPath bezierPathWithRoundedRect:frame
                                                             xRadius:6.0
                                                             yRadius:6.0];
  [[NSColor colorWithCalibratedRed:0.08f green:0.10f blue:0.14f
                             alpha:0.6f] setFill];
  [background fill];

  // Scale line
  CGFloat startX = frame.origin.x + 10.0;
  CGFloat endX = startX + self.actual_pixels;
  CGFloat lineY = frame.origin.y + 12.0;

  NSBezierPath *linePath = [NSBezierPath bezierPath];
  [linePath moveToPoint:NSMakePoint(startX, lineY + 4)];
  [linePath lineToPoint:NSMakePoint(startX, lineY)];
  [linePath lineToPoint:NSMakePoint(endX, lineY)];
  [linePath lineToPoint:NSMakePoint(endX, lineY + 4)];

  linePath.lineWidth = 2.0;
  [[NSColor whiteColor] setStroke];
  [linePath stroke];

  if (self.label_text) {
    NSDictionary *attrs = @{
      NSFontAttributeName : [NSFont systemFontOfSize:11.0
                                              weight:NSFontWeightMedium],
      NSForegroundColorAttributeName : [NSColor colorWithWhite:0.92 alpha:1.0]
    };

    NSSize textSize = [self.label_text sizeWithAttributes:attrs];
    NSRect textRect =
        NSMakeRect(startX + (self.actual_pixels - textSize.width) / 2.0,
                   lineY + 6.0, textSize.width, textSize.height);
    [self.label_text drawInRect:textRect withAttributes:attrs];
  }
}
@end

static ScaleBarView *g_scale_bar_view = nil;

void create_scale_bar(void *window_ptr) {
  NSWindow *window = (__bridge NSWindow *)window_ptr;
  if (!window || !window.contentView)
    return;

  g_scale_bar_view =
      [[ScaleBarView alloc] initWithFrame:window.contentView.bounds];
  g_scale_bar_view.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
  g_scale_bar_view.wantsLayer = YES;
  g_scale_bar_view.layer.backgroundColor =
      CGColorGetConstantColor(kCGColorClear);
  g_scale_bar_view.layer.zPosition = 1000.0f;
  g_scale_bar_view.layer.masksToBounds = NO;
  g_scale_bar_view.layer.opaque = NO;
  g_scale_bar_view.visible = YES;

  [window.contentView addSubview:g_scale_bar_view];
}

void destroy_scale_bar(void) {
  if (g_scale_bar_view) {
    [g_scale_bar_view removeFromSuperview];
    g_scale_bar_view = nil;
  }
}

static void format_distance(double meters, char *out_buf, size_t buf_size) {
  if (meters >= PARSECS_TO_METERS)
    snprintf(out_buf, buf_size, "%g pc", meter_to_parsec(meters));
  else if (meters >= LY_TO_METERS)
    snprintf(out_buf, buf_size, "%g ly", meter_to_ly(meters));
  else if (meters >= AU_TO_METERS * 0.1)
    snprintf(out_buf, buf_size, "%g AU", meter_to_au(meters));
  else {
    double km = meters / 1000.0;
    if (km >= 1e6)
      snprintf(out_buf, buf_size, "%gM km", km / 1e6);
    else
      snprintf(out_buf, buf_size, "%g km", km);
  }
}

void update_scale_bar(const Camera *camera, float screen_width,
                      float screen_height) {
  if (!g_scale_bar_view || !camera || screen_width <= 0 || screen_height <= 0)
    return;

  double fov_radians = 70.0 * M_PI / 180.0;
  double visible_height_ru = 2.0 * camera->zoom * tan(fov_radians / 2.0);
  double visible_width_ru = visible_height_ru * (screen_width / screen_height);
  double visible_width_meters = render_unit_to_meter(visible_width_ru);

  double target_pixels = 150.0;
  double target_meters = visible_width_meters * (target_pixels / screen_width);

  if (target_meters <= 0.0)
    return;

  double log10_val = floor(log10(target_meters));
  double base = pow(10.0, log10_val);
  double normalized = target_meters / base;

  double nice_factor = 1.0;
  if (normalized >= 5.0)
    nice_factor = 5.0;
  else if (normalized >= 2.0)
    nice_factor = 2.0;

  double nice_meters = nice_factor * base;
  LOG_DEBUG("Visible width: %g meters | Actual meters %g", visible_width_meters,
            nice_meters);

  double nice_ru = meter_to_render_unit(nice_meters);
  double actual_pixels = (nice_ru / visible_width_ru) * screen_width;

  char label_buf[64];
  format_distance(nice_meters, label_buf, sizeof(label_buf));

  g_scale_bar_view.actual_pixels = actual_pixels;
  g_scale_bar_view.label_text = [NSString stringWithUTF8String:label_buf];
  [g_scale_bar_view setNeedsDisplay:YES];
}
