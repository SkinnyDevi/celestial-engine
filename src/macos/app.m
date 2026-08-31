#import "app.h"
#include <AppKit/AppKit.h>
#include <stdio.h>
#include <stdlib.h>

#include "core/log/log.h"
#include "renderer.h"

int run_macos_app(void) {
  NSRect screen_rect = [[NSScreen mainScreen] frame];
  int screen_width = (int)screen_rect.size.width;
  int screen_height = (int)screen_rect.size.height;

  RendererHandle handler =
      init_metal_window(screen_width, screen_height, "Celestial Body Engine");

  NSMenu *menuBar = [[NSMenu alloc] init];
  NSMenuItem *appMenuItem = [[NSMenuItem alloc] init];
  [menuBar addItem:appMenuItem];

  NSMenu *appMenu = [[NSMenu alloc] initWithTitle:@"App"];
  NSString *appName = [[NSProcessInfo processInfo] processName];

  NSMenuItem *quitItem = [[NSMenuItem alloc]
      initWithTitle:[NSString stringWithFormat:@"Quit %@", appName]
             action:@selector(terminate:)
      keyEquivalent:@"q"];
  [quitItem setKeyEquivalentModifierMask:NSEventModifierFlagCommand];
  [appMenu addItem:quitItem];

  [appMenuItem setSubmenu:appMenu];
  [NSApp setMainMenu:menuBar];

  if (!handler) {
    LOG_ERROR("Failed to initialize Metal window.", NULL);
    exit(EXIT_FAILURE);
  }

  LOG_INFO("Using Metal rendering engine.", NULL);
  while (1) {
    pump_os_events();    // Keep the window responsive
    draw_frame(handler); // Issue GPU commands
  }
}