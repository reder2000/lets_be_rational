#pragma once

#if defined(_WIN32) || defined(__CYGWIN__)
  #ifdef LBR_BUILDING_DLL
    #define LBR_API __declspec(dllexport)
  #else
    #define LBR_API __declspec(dllimport)
  #endif
#else
  #ifdef LBR_BUILDING_DLL
    #define LBR_API __attribute__((visibility("default")))
  #else
    #define LBR_API
  #endif
#endif

