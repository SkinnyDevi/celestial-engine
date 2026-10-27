#import "shader_loader.h"
#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#include <string.h>

static NSURL *resolve_file(NSFileManager *filemanager, NSString *filename) {
  if ([filemanager fileExistsAtPath:filename])
    return [NSURL fileURLWithPath:[filename stringByStandardizingPath]];

  return nil;
}

static NSURL *resolve_by_bundle(NSFileManager *filemanager,
                                NSString *base_name) {
  NSURL *bundle_URL = [[NSBundle mainBundle] URLForResource:base_name
                                              withExtension:@"msl"];
  if (bundle_URL && [filemanager fileExistsAtPath:bundle_URL.path])
    return bundle_URL;

  NSURL *planet_URL = [[NSBundle mainBundle] URLForResource:base_name
                                              withExtension:@"msl"
                                               subdirectory:@"planets"];
  if (planet_URL && [filemanager fileExistsAtPath:planet_URL.path])
    return planet_URL;

  NSURL *moon_URL = [[NSBundle mainBundle] URLForResource:base_name
                                            withExtension:@"msl"
                                             subdirectory:@"moons"];
  if (moon_URL && [filemanager fileExistsAtPath:moon_URL.path])
    return moon_URL;

  return nil;
}

static NSURL *resolve_by_workdir(NSFileManager *filemanager,
                                 NSString *filename) {
  NSArray<NSString *> *subpaths = @[
    filename, [NSString stringWithFormat:@"planets/%@", filename],
    [NSString stringWithFormat:@"moons/%@", filename],
    [NSString stringWithFormat:@"shaders/%@", filename],
    [NSString stringWithFormat:@"shaders/planets/%@", filename],
    [NSString stringWithFormat:@"shaders/moons/%@", filename],
    [NSString stringWithFormat:@"src/macos/shaders/%@", filename],
    [NSString stringWithFormat:@"src/macos/shaders/planets/%@", filename],
    [NSString stringWithFormat:@"src/macos/shaders/moons/%@", filename],
    [NSString stringWithFormat:@"macos/shaders/%@", filename],
    [NSString stringWithFormat:@"macos/shaders/planets/%@", filename],
    [NSString stringWithFormat:@"macos/shaders/moons/%@", filename],
    [NSString stringWithFormat:@"src/renderer/macos/shaders/%@", filename],
    [NSString stringWithFormat:@"renderer/macos/shaders/%@", filename],
    [NSString stringWithFormat:@"../src/renderer/macos/shaders/%@", filename],
    [NSString stringWithFormat:@"../renderer/macos/shaders/%@", filename],
    [NSString
        stringWithFormat:@"../../src/renderer/macos/shaders/%@", filename],
    [NSString
        stringWithFormat:@"../../../src/renderer/macos/shaders/%@", filename]
  ];

  // Resolve in subpaths from exec dir
  NSString *exec_path = [[NSBundle mainBundle] executablePath];
  if (exec_path) {
    NSString *exec_dir = [exec_path stringByDeletingLastPathComponent];
    for (NSString *subpath in subpaths) {
      NSString *candidate = [[exec_dir stringByAppendingPathComponent:subpath]
          stringByStandardizingPath];

      if ([filemanager fileExistsAtPath:candidate])
        return [NSURL fileURLWithPath:candidate];
    }
  }

  // Resolve in subpaths from current working dir
  NSString *cwd = [filemanager currentDirectoryPath];
  if (cwd) {
    for (NSString *subpath in subpaths) {
      NSString *candidate = [[cwd stringByAppendingPathComponent:subpath]
          stringByStandardizingPath];

      if ([filemanager fileExistsAtPath:candidate])
        return [NSURL fileURLWithPath:candidate];
    }
  }

  // Resolve in subpaths upward from current working dir
  NSString *current = cwd;
  for (int i = 0; i < 5 && current.length > 1; i++) {
    NSString *candidate1 = [current
        stringByAppendingPathComponent:[NSString stringWithFormat:@"src/macos/"
                                                                  @"shaders/%@",
                                                                  filename]];
    if ([filemanager fileExistsAtPath:candidate1])
      return [NSURL fileURLWithPath:[candidate1 stringByStandardizingPath]];

    NSString *candidate1b =
        [current stringByAppendingPathComponent:
                     [NSString stringWithFormat:@"src/macos/"
                                                @"shaders/planets/%@",
                                                filename]];
    if ([filemanager fileExistsAtPath:candidate1b])
      return [NSURL fileURLWithPath:[candidate1b stringByStandardizingPath]];

    NSString *candidate2 = [current
        stringByAppendingPathComponent:[NSString stringWithFormat:@"shaders/%@",
                                                                  filename]];
    if ([filemanager fileExistsAtPath:candidate2])
      return [NSURL fileURLWithPath:[candidate2 stringByStandardizingPath]];

    current = [current stringByDeletingLastPathComponent];
  }

  return nil;
}

static NSURL *resolve_shader_url(NSString *shader_name) {
  NSFileManager *filemanager = [NSFileManager defaultManager];
  NSString *base_name = [shader_name stringByDeletingPathExtension];
  NSString *filename = [base_name stringByAppendingPathExtension:@"msl"];

  NSURL *resolve_by_shadername = resolve_file(filemanager, shader_name);
  if (resolve_by_shadername)
    return resolve_by_shadername;

  NSURL *resolve_by_filename = resolve_file(filemanager, filename);
  if (resolve_by_filename)
    return resolve_by_filename;

  NSURL *bundle_url = resolve_by_bundle(filemanager, base_name);
  if (bundle_url)
    return bundle_url;

#ifdef SHADER_SOURCE_DIR
  NSString *compile_path =
      [NSString stringWithFormat:@"%s/%@", SHADER_SOURCE_DIR, filename];
  if ([filemanager fileExistsAtPath:compile_path])
    return [NSURL fileURLWithPath:[compile_path stringByStandardizingPath]];

  NSString *planets_compile_path =
      [NSString stringWithFormat:@"%s/planets/%@", SHADER_SOURCE_DIR, filename];
  if ([filemanager fileExistsAtPath:planets_compile_path])
    return [NSURL
        fileURLWithPath:[planets_compile_path stringByStandardizingPath]];

  NSString *stars_compile_path =
      [NSString stringWithFormat:@"%s/stars/%@", SHADER_SOURCE_DIR, filename];
  if ([filemanager fileExistsAtPath:stars_compile_path])
    return
        [NSURL fileURLWithPath:[stars_compile_path stringByStandardizingPath]];

  NSString *moons_compile_path =
      [NSString stringWithFormat:@"%s/moons/%@", SHADER_SOURCE_DIR, filename];
  if ([filemanager fileExistsAtPath:moons_compile_path])
    return
        [NSURL fileURLWithPath:[moons_compile_path stringByStandardizingPath]];

#endif

  NSURL *resolved_in_workdir = resolve_by_workdir(filemanager, filename);
  if (resolved_in_workdir)
    return resolved_in_workdir;

  return nil;
}

static NSString *preprocess_shader_includes(NSString *source,
                                            NSString *parent_dir,
                                            NSMutableSet<NSString *> *visited) {
  if (!visited)
    visited = [NSMutableSet set];

  NSMutableString *result = [NSMutableString string];
  NSArray<NSString *> *lines = [source componentsSeparatedByString:@"\n"];
  NSFileManager *fm = [NSFileManager defaultManager];

  for (NSString *line in lines) {
    NSString *trimmed =
        [line stringByTrimmingCharactersInSet:[NSCharacterSet
                                                  whitespaceCharacterSet]];
    if ([trimmed hasPrefix:@"#include \""] && [trimmed hasSuffix:@"\""]) {
      NSRange firstQuote = [trimmed rangeOfString:@"\""];
      NSRange lastQuote = [trimmed rangeOfString:@"\""
                                         options:NSBackwardsSearch];

      if (firstQuote.location != NSNotFound &&
          lastQuote.location != NSNotFound &&
          lastQuote.location > firstQuote.location) {
        NSString *inc_name = [trimmed
            substringWithRange:NSMakeRange(firstQuote.location + 1,
                                           lastQuote.location -
                                               firstQuote.location - 1)];
        NSURL *inc_url = resolve_shader_url(inc_name);

        if (!inc_url && parent_dir) {
          NSString *local_path =
              [parent_dir stringByAppendingPathComponent:inc_name];

          if ([fm fileExistsAtPath:local_path])
            inc_url =
                [NSURL fileURLWithPath:[local_path stringByStandardizingPath]];
        }

        if (inc_url) {
          NSString *canonical_path = [inc_url path];
          if (![visited containsObject:canonical_path]) {
            [visited addObject:canonical_path];
            NSError *err = nil;
            NSString *inc_source =
                [NSString stringWithContentsOfURL:inc_url
                                         encoding:NSUTF8StringEncoding
                                            error:&err];

            if (inc_source) {
              NSString *expanded = preprocess_shader_includes(
                  inc_source,
                  [canonical_path stringByDeletingLastPathComponent], visited);

              [result appendFormat:@"// --- BEGIN INCLUDE: %@ ---\n%@\n// --- "
                                   @"END INCLUDE: %@ ---\n",
                                   inc_name, expanded, inc_name];
              continue;
            }
          } else {
            // Already included, skip to prevent multiple symbol definition
            continue;
          }
        }
      }
    }

    [result appendString:line];
    [result appendString:@"\n"];
  }

  return result;
}

const char *load_shader_file(const char *shader_name) {
  if (!shader_name) {
    LOG_ERROR("%s", "Failed to find shader: shader name is NULL");
    exit(EXIT_FAILURE);
  }

  NSString *nameStr = [NSString stringWithUTF8String:shader_name];
  NSURL *shaderURL = resolve_shader_url(nameStr);

  if (!shaderURL) {
    LOG_ERROR("Failed to find shader file: %s.msl", shader_name);
    exit(EXIT_FAILURE);
  }

  LOG_DEBUG("Loaded shader '%s' from: %s", shader_name,
            [[shaderURL path] UTF8String]);

  NSError *error = nil;
  NSString *shaderSource =
      [NSString stringWithContentsOfURL:shaderURL
                               encoding:NSUTF8StringEncoding
                                  error:&error];
  if (!shaderSource) {
    LOG_ERROR("Failed to read shader file %s.msl: %s", shader_name,
              [[error localizedDescription] UTF8String]);
    exit(EXIT_FAILURE);
  }

  NSString *parent_dir = [[shaderURL path] stringByDeletingLastPathComponent];
  NSMutableSet *visited = [NSMutableSet setWithObject:[shaderURL path]];
  NSString *processed =
      preprocess_shader_includes(shaderSource, parent_dir, visited);

  return strdup(processed.UTF8String);
}

void compile_grid_shader_lib(RenderState *state, const char *shader_name) {
  CAMetalLayer *metalLayer =
      (__bridge CAMetalLayer *)RenderState_GetMetalLayer(state);

  NSError *error = nil;
  NSString *shader_source =
      [NSString stringWithUTF8String:load_shader_file("displaced_grid_mesh")];
  MTLCompileOptions *compileOptions = [MTLCompileOptions new];
  id<MTLLibrary> shaderLibrary =
      [metalLayer.device newLibraryWithSource:shader_source
                                      options:compileOptions
                                        error:&error];
  if (error) {
    LOG_ERROR("Error creating shader library: %s",
              [[error localizedDescription] UTF8String]);
    exit(EXIT_FAILURE);
  }
  RenderState_SetGridShaderLib(state, (__bridge void *)shaderLibrary);
}