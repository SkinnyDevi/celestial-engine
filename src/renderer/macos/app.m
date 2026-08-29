#import "app.h"
#import "renderer.h"
#include <AppKit/AppKit.h>
#include <stdio.h>
#include <stdlib.h>

int run_macos_app(void) {
  RendererHandle handler =
      init_metal_window(1280, 720, "Celestial Body Engine");

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
    puts("Failed to initialize Metal window.");
    exit(EXIT_FAILURE);
  }

  while (1) {
    pump_os_events();    // Keep the window responsive
    draw_frame(handler); // Issue GPU commands
  }
}