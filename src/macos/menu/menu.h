#ifndef MACOS_APP_MENU_H
#define MACOS_APP_MENU_H

#ifdef __OBJC__
#import <AppKit/AppKit.h>

NSMenuItem *add_app_menu(NSMenu *menuBar);
NSMenuItem *add_view_menu(NSMenu *menuBar);

void app_menu_quit_entry(NSMenu *menu);
void view_menu_hide_grid_entry(NSMenu *menu);
#endif

#endif