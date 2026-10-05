find_path(CRITERION_INCLUDE_DIR criterion/criterion.h)
find_library(CRITERION_LIBRARY criterion)

if (CRITERION_LIBRARY AND CRITERION_INCLUDE_DIR)
    message(STATUS "Criterion found, building tests.")

    # test_math
    add_executable(test_math test_math.c ../core/data/math.c)
    target_include_directories(test_math PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/.. ${CRITERION_INCLUDE_DIR})
    target_link_libraries(test_math PRIVATE ${CRITERION_LIBRARY})
    add_test(NAME test_math COMMAND test_math)

    # test_astro_time
    add_executable(test_astro_time test_astro_time.c ../core/space/astro_time.c)
    target_include_directories(test_astro_time PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/.. ${CRITERION_INCLUDE_DIR})
    target_link_libraries(test_astro_time PRIVATE ${CRITERION_LIBRARY})
    add_test(NAME test_astro_time COMMAND test_astro_time)

    # test_raycast
    add_executable(test_raycast test_raycast.c ../core/data/raycast.c)
    target_include_directories(test_raycast PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/.. ${CRITERION_INCLUDE_DIR})
    target_link_libraries(test_raycast PRIVATE ${CRITERION_LIBRARY})
    add_test(NAME test_raycast COMMAND test_raycast)

    # test_dyn_array
    add_executable(test_dyn_array test_dyn_array.c ../core/data/dyn_array.c)
    target_include_directories(test_dyn_array PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/.. ${CRITERION_INCLUDE_DIR})
    target_link_libraries(test_dyn_array PRIVATE ${CRITERION_LIBRARY})
    add_test(NAME test_dyn_array COMMAND test_dyn_array)
    # test_json_loader
    add_executable(test_json_loader test_json_loader.c ../core/data/loader/json/json_data_loader.c)
    target_include_directories(test_json_loader PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/.. ${CRITERION_INCLUDE_DIR} ${cjson_SOURCE_DIR})
    target_link_libraries(test_json_loader PRIVATE ${CRITERION_LIBRARY} cjson)
    add_test(NAME test_json_loader COMMAND test_json_loader)

    # test_cli_args
    file(GLOB CLI_SOURCES
        "../core/cli/functions.c"
        "../core/cli/instance_data.c"
        "../core/cli/args/*.c"
    )
    add_executable(test_cli_args test_cli_args.c ${CLI_SOURCES} ../core/data/dyn_array.c ../core/data/loader/data_loader.c ../core/data/loader/loader_registry.c ../core/data/loader/json/json_data_loader.c)
    target_include_directories(test_cli_args PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/.. ${CRITERION_INCLUDE_DIR} ${cjson_SOURCE_DIR})
    target_link_libraries(test_cli_args PRIVATE ${CRITERION_LIBRARY} cjson)
    add_test(NAME test_cli_args COMMAND test_cli_args)
else()
    message(WARNING "Criterion not found. To build tests, please install Criterion.")
endif()

# Python Schema Validation Test (Using VENV script)
add_test(NAME test_json_schema 
         COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/scripts/run_schema_tests.sh
         ${CMAKE_CURRENT_SOURCE_DIR}/data/schema.json 
         ${CMAKE_CURRENT_SOURCE_DIR}/data/test_data_file.json)

