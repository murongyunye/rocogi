#ifndef ROCogi_CAPTURE_H
#define ROCogi_CAPTURE_H

#include <windows.h>

typedef struct {
    int width;
    int height;
    unsigned char *bgra;   /* 自上而下的 BGRA，行连续 */
    int method;            /* 1=DXGI 2=PrintWindow 3=BitBlt 4=桌面 GDI */
    const char *method_name;
    char note[256];
    double ms;
} capture_result;

/* 捕获指定窗口；失败返回 0 */
int capture_window(HWND hwnd, capture_result *out);
/* 强制走 BitBlt(窗口 DC)，用于对照验证遮挡时是否还能拿到内容 */
int capture_window_bitblt(HWND hwnd, capture_result *out);
/* 捕获整个桌面：先 DXGI，失败回落 GDI */
int capture_desktop(capture_result *out);
void capture_free(capture_result *out);
int capture_save_png(const capture_result *cap, const char *path);

/* 两帧像素差异（0..255 平均绝对差），用于判断是否空白 */
double capture_diff(const capture_result *a, const capture_result *b);

/* 采样判断是否为近似纯色（疑似空白） */
int capture_is_blank(const capture_result *cap);

#endif
