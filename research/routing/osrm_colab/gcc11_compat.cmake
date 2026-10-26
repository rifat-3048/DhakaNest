# Evidence: v6 log, line 11834, GCC 11 Mapbox variant destructor in OSRM::Route.
# Keep the warning visible and all other warnings fatal. Do not edit OSRM source.
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" AND
   CMAKE_CXX_COMPILER_VERSION VERSION_GREATER_EQUAL "11" AND
   CMAKE_CXX_COMPILER_VERSION VERSION_LESS "12")
    set_property(SOURCE "${PROJECT_SOURCE_DIR}/src/osrm/osrm.cpp" APPEND PROPERTY
                 COMPILE_OPTIONS "-Wno-error=free-nonheap-object")
    message(STATUS "DhakaNest: GCC 11 only, osrm.cpp only: keep free-nonheap-object visible but nonfatal")
endif()
