#include "winenum.h"

#include <stdlib.h>
#include <string.h>
#include <wchar.h>

static void to_utf8(const WCHAR *src, char *dst, int cap) {
    if (cap <= 0) return;
    int n = WideCharToMultiByte(CP_UTF8, 0, src, -1, dst, cap - 1, NULL, NULL);
    if (n <= 0) {
        dst[0] = '\0';
    } else {
        dst[n - 1] = '\0';
    }
}

typedef struct {
    win_info *out;
    int max;
    int count;
} enum_ctx;

static HWND g_foreground = NULL;

static BOOL CALLBACK enum_proc(HWND hwnd, LPARAM lparam) {
    enum_ctx *ctx = (enum_ctx *)lparam;
    if (ctx->count >= ctx->max) {
        return FALSE;
    }
    if (!IsWindowVisible(hwnd)) {
        return TRUE;
    }
    WCHAR wtitle[256];
    wtitle[0] = 0;
    GetWindowTextW(hwnd, wtitle, 255);
    if (!wtitle[0]) {
        return TRUE;
    }
    win_info *info = &ctx->out[ctx->count];
    memset(info, 0, sizeof(*info));
    info->hwnd = hwnd;
    to_utf8(wtitle, info->title, sizeof(info->title));
    WCHAR wcls[128];
    wcls[0] = 0;
    GetClassNameW(hwnd, wcls, 127);
    to_utf8(wcls, info->cls, sizeof(info->cls));
    GetWindowRect(hwnd, &info->rect);
    info->visible = 1;
    info->minimized = IsIconic(hwnd) ? 1 : 0;
    info->foreground = (hwnd == g_foreground) ? 1 : 0;
    ctx->count++;
    return TRUE;
}

int win_enum_visible(win_info *out, int max) {
    enum_ctx ctx;
    ctx.out = out;
    ctx.max = max;
    ctx.count = 0;
    g_foreground = GetForegroundWindow();
    EnumWindows(enum_proc, (LPARAM)&ctx);
    return ctx.count;
}
