cmake_minimum_required(VERSION 3.16)
project(SupraLibKSysGuardClient LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_AUTOMOC ON)
find_package(Qt6 6.10 REQUIRED COMPONENTS Core DBus Qml)
add_executable(stats-server stats-server.cpp)
target_link_libraries(stats-server PRIVATE Qt6::Core Qt6::DBus Qt6::Qml)
if(NATIVE_PROVIDER_ONLY)
    # Read the reviewed upstream headers and generated headers from this build.
    # Do not substitute an installed Ubuntu SDK for native candidate tests.
    if(NOT IS_DIRECTORY "${NATIVE_SOURCE_DIR}/systemstats" OR NOT IS_DIRECTORY "${NATIVE_BUILD_DIR}/systemstats")
        message(FATAL_ERROR "Expected candidate source and generated build headers")
    endif()
    target_include_directories(stats-server PRIVATE "${NATIVE_SOURCE_DIR}"
        "${NATIVE_BUILD_DIR}/formatter" "${NATIVE_BUILD_DIR}/systemstats")
else()
    find_package(Qt6 6.10 REQUIRED COMPONENTS Gui Quick Test)
    if(CANDIDATE_CONSUMER)
        find_package(KSysGuard 6.7.5 EXACT REQUIRED)
    else()
        find_package(KSysGuard REQUIRED)
    endif()
    target_link_libraries(stats-server PRIVATE KSysGuard::SystemStats)
    add_executable(stats-client main.cpp)
    target_link_libraries(stats-client PRIVATE Qt6::Gui Qt6::Quick Qt6::Test Qt6::DBus
        KSysGuard::ProcessCore KSysGuard::Formatter KSysGuard::Sensors
        KSysGuard::SystemStats KSysGuard::SensorFaces)
endif()
