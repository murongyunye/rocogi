#ifndef ROCogi_WINENUM_H
#define ROCogi_WINENUM_H

#include <windows.h>

typedef struct {
    HWND hwnd;
    char title[256];
    char cls[128];
    RECT rect;
    int visible;
    int minimized;
    int foreground;
} win_info;

int win_enum_visible(win_info *out, int max);

#endif
