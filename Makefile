.PHONY: all configure build run test clean

BUILD_DIR := build
SRC_DIR := src
EXECUTABLE := $(BUILD_DIR)/celengine

all: build

configure:
	cmake -S $(SRC_DIR) -B $(BUILD_DIR)

build: configure
	cmake --build $(BUILD_DIR)

run: build
	./$(EXECUTABLE) $(ARGS)

test: build
	ctest --test-dir $(BUILD_DIR) -V

clean:
	rm -rf $(BUILD_DIR)

import-data:
	@bash ./data/import_data.sh