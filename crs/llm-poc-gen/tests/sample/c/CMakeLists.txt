cmake_minimum_required(VERSION 3.10)
project(sample)
set(CMAKE_C_COMPILER clang)
set(CMAKE_CXX_COMPILER clang)

add_executable(harness target/target.c harness.cpp)
target_compile_options(harness PRIVATE -g -O0 -fsanitize=fuzzer,address)
target_link_libraries(harness PRIVATE -fsanitize=fuzzer,address)
