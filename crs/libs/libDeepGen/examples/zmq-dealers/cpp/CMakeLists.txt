cmake_minimum_required(VERSION 3.10)
project(cpp_dealer)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find ZeroMQ
find_package(ZeroMQ QUIET)
if(NOT ZeroMQ_FOUND)
    message(STATUS "ZeroMQ not found via find_package, using cppzmq's built-in support")
endif()

# Add cppzmq
add_subdirectory(cppzmq)

# Add nlohmann/json (header-only library)
include(FetchContent)
FetchContent_Declare(json
    URL https://github.com/nlohmann/json/releases/download/v3.11.2/json.tar.xz
)
FetchContent_MakeAvailable(json)

# Add the dealer executable
add_executable(dealer dealer.cpp)
target_link_libraries(dealer 
    PRIVATE 
    cppzmq
    nlohmann_json::nlohmann_json
    pthread
)

# Installation targets
install(TARGETS dealer
    RUNTIME DESTINATION bin
)