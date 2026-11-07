cmake_minimum_required(VERSION 3.16)
project(rocogi_core C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

include_directories(third_party)

add_executable(rocogi-core
    src/main.c
    src/host.c
    src/strbuf.c
    src/json.c
    src/http.c
    src/static.c
    src/nodes.c
    src/workflow.c
    src/mapstat.c
    src/routes.c
    src/pngio.c
    src/capture.c
    src/winenum.c
    src/input.c
    src/match.c
    src/hotkey.c
)

target_link_libraries(rocogi-core ws2_32 d3d11 dxgi uuid ole32 user32 gdi32 m)

if(MINGW)
    target_link_options(rocogi-core PRIVATE -static -static-libgcc)
    target_compile_options(rocogi-core PRIVATE -Wall -Wextra -Wno-unused-parameter -Wno-sign-compare)
endif()

