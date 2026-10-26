# Preserve the v7 GCC-11/osrm.cpp exception unchanged.
include("${CMAKE_CURRENT_LIST_DIR}/gcc11_compat.cmake")
# Sol2 3.3.0 lua_getfield warning, v7 log lines 7394/7409. Warning stays visible.
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set_property(SOURCE "${PROJECT_SOURCE_DIR}/src/extractor/scripting_environment_lua.cpp"
                 APPEND PROPERTY COMPILE_OPTIONS "-Wno-error=array-bounds")
    message(STATUS "DhakaNest: scripting_environment_lua.cpp only: array-bounds remains visible but nonfatal")
endif()
