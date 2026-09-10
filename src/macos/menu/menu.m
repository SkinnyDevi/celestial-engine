#import "menu.h"
#include <AppKit/AppKit.h>

#include "core/data/constants.h"

NSMenuItem *add_app_menu(NSMenu *menuBar) {
  NSMenuItem *appMenuItem = [[NSMenuItem alloc] init];
  [menuBar addItem:appMenuItem];

  return appMenuItem;
}

NSMenuItem *add_view_menu(NSMenu *menuBar) {
  NSMenuItem *viewMenuItem = [[NSMenuItem alloc] init];
  [menuBar addItem:viewMenuItem];
  return viewMenuItem;
}

void app_menu_quit_entry(NSMenu *menu) {
  NSMenuItem *quitItem = [[NSMenuItem alloc] initWithTitle:@"Quit"
                                                    action:@selector(terminate:)
                                             keyEquivalent:@"q"];
  [quitItem setTitle:@"Quit " APP_NAME];
  [quitItem setKeyEquivalentModifierMask:NSEventModifierFlagCommand];
  [menu addItem:quitItem];
}

void view_menu_hide_grid_entry(NSMenu *menu) {
  NSMenuItem *hideGridItem =
      [[NSMenuItem alloc] initWithTitle:@"Hide Grid"
                                 action:@selector(hideGrid:)
                          keyEquivalent:@"g"];
  [hideGridItem setState:NSControlStateValueOn];
  [hideGridItem setKeyEquivalentModifierMask:NSEventModifierFlagCommand];
  [menu addItem:hideGridItem];
}
