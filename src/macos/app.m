#import "app.h"
#import <AppKit/AppKit.h>
#import <stdio.h>
#import <stdlib.h>

#import "core/data/constants.h"
#import "core/log/log.h"
#import "macos/menu/menu.h"
#import "macos/render/renderer.h"

@interface AppDelegate : NSObject <NSApplicationDelegate>
@end

@implementation AppDelegate

- (void)hideGrid:(id)sender {
  NSMenuItem *item = (NSMenuItem *)sender;
  if (item.state == NSControlStateValueOn) {
    item.state = NSControlStateValueOff;
  } else {
    item.state = NSControlStateValueOn;
  }
  toggle_grid_visibility();
}

@end

static AppDelegate *app_delegate = nil;

int run_macos_app(void) {
  NSRect screen_rect = [[NSScreen mainScreen] frame];
  int screen_width = (int)screen_rect.size.width;
  int screen_height = (int)screen_rect.size.height;

  LOG_INFO("Using Metal rendering engine.", NULL);
  RendererHandle handler =
      init_metal_window(screen_width, screen_height, "Celestial Body Engine");

  app_delegate = [[AppDelegate alloc] init];
  [NSApp setDelegate:app_delegate];

  NSMenu *menuBar = [[NSMenu alloc] init];
  NSMenuItem *appMenuItem = add_app_menu(menuBar);
  NSMenuItem *viewMenuItem = add_view_menu(menuBar);

  NSMenu *appMenu = [[NSMenu alloc] initWithTitle:@"App"];
  app_menu_quit_entry(appMenu);

  NSMenu *viewMenu = [[NSMenu alloc] initWithTitle:@"View"];
  view_menu_hide_grid_entry(viewMenu);

  [appMenuItem setSubmenu:appMenu];
  [viewMenuItem setSubmenu:viewMenu];
  [NSApp setMainMenu:menuBar];

  if (!handler) {
    LOG_ERROR("Failed to initialize Metal window.", NULL);
    exit(EXIT_FAILURE);
  }

  while (1) {
    pump_os_events();    // Keep the window responsive
    draw_frame(handler); // Issue GPU commands
  }
}