# Celestial Body Engine

A celestial mechanics simulation and 3D visualization engine written in C and Objective-C. It utilizes Apple's Metal framework for high-performance graphics on macOS and features real-time celestial motion based on imported datasets.

## Features
- **3D Rendering:** Native Metal integration for smooth macOS visualization.
- **Modular Data Loaders:** Expandable data format support (currently supports `.json`).
- **Dynamic Time Scale:** Fast-forward, slow down, or reverse time in the simulation.
- **State Saving:** Save simulation states as a checkpoint to resume later.
- **Interactive Camera:** Orbit and zoom around the generated solar system.
- **Debug Overlays:** Real-time metrics including FPS, camera position, simulation date, and wireframe views.

## Prerequisites
- macOS (Metal API support required)
- CMake `3.23` or newer
- Apple Clang (Command Line Tools)

## Building the Project

The project uses CMake to configure and build the executable. The build process automatically fetches external dependencies such as `cJSON`.

```bash
# Create a build directory
mkdir -p build && cd build

# Configure the project
cmake ../src

# Build the executable
cmake --build .
```

This will produce the `celengine` executable inside the `build` directory.

## Usage

```bash
./build/celengine [OPTIONS]
```

### Rendering Engine
- `--macos`: Use the Metal rendering engine (Required on macOS).
- `--vulkan`: Use the Vulkan rendering engine.

### Simulation
- `--sim-date <date>`: Set the starting simulation date in UTC (Format: `YYYY-MM-DDTHH:mm:ss`).
- `--time-scale <scale>`: Set the time scale multiplier. Supports positive, negative, and scientific notation (e.g., `1`, `-5`, `1e5`).
- `--data-file <path>`: Load simulation data from a specified file.
- `--save-state <path>`: Output the final state of all celestial bodies to a file when the app closes.

### Options
- `--fps`: Show the FPS counter overlay.
- `--debug`: Enable debug mode, including extensive console logging and overlay metrics.
- `--help`: Display available command-line arguments.

### Example

Load a local JSON dataset, speed up time significantly, show the FPS counter, enable the debug overlay, and save the state upon exiting:

```bash
./build/celengine \
    --macos \
    --debug \
    --fps \
    --time-scale 1e5 \
    --data-file ./src/core/data/loader/json/test_data_file.json \
    --save-state ./checkpoint.save.json
```

## Data File Formats

Currently supported formats:
- `.json`: Standard JSON schema for describing stars, planets, and moons along with their orbital properties.
