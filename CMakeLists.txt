cmake_minimum_required(VERSION 3.15)
project(lets_be_rational LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23) 
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_VISIBILITY_PRESET hidden)
set(CMAKE_CXX_VISIBILITY_PRESET hidden)
set(CMAKE_VISIBILITY_INLINES_HIDDEN YES)

# Collect all .cpp and .h files recursively
file(GLOB_RECURSE LBR_SOURCES CONFIGURE_DEPENDS
    src/*.cpp
    src/*.h
    include/*.h
    License README.md .gitignore
)

add_library(lets_be_rational SHARED ${LBR_SOURCES})

target_include_directories(lets_be_rational
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)
target_compile_definitions(lets_be_rational PRIVATE LBR_BUILDING_DLL)
target_compile_definitions(lets_be_rational PRIVATE NO_XL_API)

install(TARGETS lets_be_rational EXPORT lets_be_rationalTargets)
install(DIRECTORY include/ DESTINATION include)


