#include "input.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void screen_point(int x, int y, int window_mode, HWND hwnd, int *sx, int *sy) {
    if (window_mode && hwnd) {
        RECT rc;
        GetWindowRect(hwnd, &rc);
        *sx = rc.left + x;
        *sy = rc.top + y;
    } else {
        *sx = x;
        *sy = y;
    }
}

static void send_mouse_move(int sx, int sy, DWORD extra_flags) {
    int sw = GetSystemMetrics(SM_CXSCREEN);
    int sh = GetSystemMetrics(SM_CYSCREEN);
    if (sw <= 1) sw = 2;
    if (sh <= 1) sh = 2;
    INPUT in;
    memset(&in, 0, sizeof(in));
    in.type = INPUT_MOUSE;
    in.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | extra_flags;
    in.mi.dx = (LONG)((double)sx * 65535.0 / (double)(sw - 1));
    in.mi.dy = (LONG)((double)sy * 65535.0 / (double)(sh - 1));
    SendInput(1, &in, sizeof(INPUT));
}

int input_move(int x, int y, int window_mode, HWND hwnd, int duration_ms) {
    int sx, sy;
    screen_point(x, y, window_mode, hwnd, &sx, &sy);
    if (duration_ms <= 0) {
        send_mouse_move(sx, sy, 0);
        return 1;
    }
    POINT start;
    GetCursorPos(&start);
    int steps = duration_ms / 10;
    if (steps < 4) steps = 4;
    if (steps > 120) steps = 120;
    for (int i = 1; i <= steps; ++i) {
        int cx = start.x + (sx - start.x) * i / steps;
        int cy = start.y + (sy - start.y) * i / steps;
        send_mouse_move(cx, cy, 0);
        Sleep(10);
    }
    return 1;
}

int input_click(int x, int y, int window_mode, HWND hwnd, int button, int clicks) {
    int sx, sy;
    screen_point(x, y, window_mode, hwnd, &sx, &sy);
    send_mouse_move(sx, sy, 0);
    Sleep(15);
    DWORD down_flag = MOUSEEVENTF_LEFTDOWN;
    DWORD up_flag = MOUSEEVENTF_LEFTUP;
    if (button == 1) {
        down_flag = MOUSEEVENTF_RIGHTDOWN;
        up_flag = MOUSEEVENTF_RIGHTUP;
    } else if (button == 2) {
        down_flag = MOUSEEVENTF_MIDDLEDOWN;
        up_flag = MOUSEEVENTF_MIDDLEUP;
    }
    if (clicks < 1) clicks = 1;
    INPUT in[2];
    for (int i = 0; i < clicks; ++i) {
        memset(in, 0, sizeof(in));
        in[0].type = INPUT_MOUSE;
        in[0].mi.dwFlags = down_flag;
        in[1].type = INPUT_MOUSE;
        in[1].mi.dwFlags = up_flag;
        SendInput(2, in, sizeof(INPUT));
        Sleep(40);
    }
    return 1;
}

static int vk_for_token(const char *tok) {
    if (!tok || !*tok) return 0;
    if (_stricmp(tok, "ctrl") == 0 || _stricmp(tok, "control") == 0) return VK_CONTROL;
    if (_stricmp(tok, "shift") == 0) return VK_SHIFT;
    if (_stricmp(tok, "alt") == 0) return VK_MENU;
    if (_stricmp(tok, "win") == 0) return VK_LWIN;
    if (_stricmp(tok, "enter") == 0 || _stricmp(tok, "return") == 0) return VK_RETURN;
    if (_stricmp(tok, "tab") == 0) return VK_TAB;
    if (_stricmp(tok, "esc") == 0 || _stricmp(tok, "escape") == 0) return VK_ESCAPE;
    if (_stricmp(tok, "space") == 0) return VK_SPACE;
    if (_stricmp(tok, "backspace") == 0) return VK_BACK;
    if (_stricmp(tok, "delete") == 0 || _stricmp(tok, "del") == 0) return VK_DELETE;
    if (_stricmp(tok, "home") == 0) return VK_HOME;
    if (_stricmp(tok, "end") == 0) return VK_END;
    if (_stricmp(tok, "up") == 0) return VK_UP;
    if (_stricmp(tok, "down") == 0) return VK_DOWN;
    if (_stricmp(tok, "left") == 0) return VK_LEFT;
    if (_stricmp(tok, "right") == 0) return VK_RIGHT;
    if (tok[0] == 'f' || tok[0] == 'F') {
        int n = atoi(tok + 1);
        if (n >= 1 && n <= 24) return VK_F1 + n - 1;
    }
    if (strlen(tok) == 1) {
        char c = (char)toupper((unsigned char)tok[0]);
        if (c >= 'A' && c <= 'Z') return c;
        if (c >= '0' && c <= '9') return c;
    }
    return 0;
}

int input_key(const char *combo) {
    if (!combo || !*combo) return 0;
    char buf[128];
    strncpy(buf, combo, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';

    int mods[4];
    int mod_count = 0;
    char key_tok[32] = {0};
    char *p = buf;
    while (*p) {
        char *plus = strchr(p, '+');
        char tok[32];
        size_t n = plus ? (size_t)(plus - p) : strlen(p);
        if (n >= sizeof(tok)) n = sizeof(tok) - 1;
        memcpy(tok, p, n);
        tok[n] = '\0';
        int vk = vk_for_token(tok);
        if (plus) {
            if (vk && mod_count < 4) mods[mod_count++] = vk;
        } else {
            strncpy(key_tok, tok, sizeof(key_tok) - 1);
        }
        if (!plus) break;
        p = plus + 1;
    }

    INPUT in[10];
    memset(in, 0, sizeof(in));
    int count = 0;
    for (int i = 0; i < mod_count; ++i) {
        in[count].type = INPUT_KEYBOARD;
        in[count].ki.wVk = (WORD)mods[i];
        count++;
    }
    int vk = vk_for_token(key_tok);
    if (vk) {
        in[count].type = INPUT_KEYBOARD;
        in[count].ki.wVk = (WORD)vk;
        count++;
        in[count].type = INPUT_KEYBOARD;
        in[count].ki.wVk = (WORD)vk;
        in[count].ki.dwFlags = KEYEVENTF_KEYUP;
        count++;
    }
    for (int i = mod_count - 1; i >= 0; --i) {
        in[count].type = INPUT_KEYBOARD;
        in[count].ki.wVk = (WORD)mods[i];
        in[count].ki.dwFlags = KEYEVENTF_KEYUP;
        count++;
    }
    if (count == 0) return 0;
    SendInput((UINT)count, in, sizeof(INPUT));
    return vk != 0;
}

int input_type_text(const char *utf8_text) {
    if (!utf8_text || !*utf8_text) return 0;
    size_t len = strlen(utf8_text);
    WCHAR *wide = (WCHAR *)malloc((len + 1) * sizeof(WCHAR));
    if (!wide) return 0;
    int n = MultiByteToWideChar(CP_UTF8, 0, utf8_text, (int)len, wide, (int)len + 1);
    if (n <= 0) {
        free(wide);
        return 0;
    }
    int ok = 1;
    for (int offset = 0; offset < n; offset += 32) {
        int chunk = n - offset;
        if (chunk > 32) chunk = 32;
        INPUT in[64];
        memset(in, 0, sizeof(in));
        for (int i = 0; i < chunk; ++i) {
            WCHAR ch = wide[offset + i];
            in[i * 2].type = INPUT_KEYBOARD;
            in[i * 2].ki.wScan = ch;
            in[i * 2].ki.dwFlags = KEYEVENTF_UNICODE;
            in[i * 2 + 1].type = INPUT_KEYBOARD;
            in[i * 2 + 1].ki.wScan = ch;
            in[i * 2 + 1].ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP;
        }
        if (SendInput((UINT)(chunk * 2), in, sizeof(INPUT)) != (UINT)(chunk * 2)) {
            ok = 0;
            break;
        }
        Sleep(10);
    }
    free(wide);
    return ok;
}

int input_wheel(int delta) {
    INPUT in;
    memset(&in, 0, sizeof(in));
    in.type = INPUT_MOUSE;
    in.mi.dwFlags = MOUSEEVENTF_WHEEL;
    in.mi.mouseData = (DWORD)delta;
    SendInput(1, &in, sizeof(INPUT));
    return 1;
}

int input_focus_window(HWND hwnd) {
    if (!hwnd || !IsWindow(hwnd)) return 0;
    if (IsIconic(hwnd)) {
        ShowWindow(hwnd, SW_RESTORE);
        Sleep(120);
    }
    if (GetForegroundWindow() == hwnd) {
        return 1;
    }
    DWORD fg_thread = GetWindowThreadProcessId(GetForegroundWindow(), NULL);
    DWORD my_thread = GetCurrentThreadId();
    BOOL attached = FALSE;
    if (fg_thread && fg_thread != my_thread) {
        attached = AttachThreadInput(my_thread, fg_thread, TRUE);
    }
    SetForegroundWindow(hwnd);
    BringWindowToTop(hwnd);
    if (attached) {
        AttachThreadInput(my_thread, fg_thread, FALSE);
    }
    Sleep(80);
    return GetForegroundWindow() == hwnd;
}

int input_clipboard_text(const char *utf8_text) {
    if (!utf8_text) return 0;
    size_t len = strlen(utf8_text);
    size_t wlen = len * 2 + 2;
    HGLOBAL mem = GlobalAlloc(GMEM_MOVEABLE, wlen * sizeof(WCHAR));
    if (!mem) return 0;
    WCHAR *dst = (WCHAR *)GlobalLock(mem);
    if (!dst) {
        GlobalFree(mem);
        return 0;
    }
    int n = MultiByteToWideChar(CP_UTF8, 0, utf8_text, (int)len, dst, (int)wlen);
    dst[n > 0 ? n : 0] = L'\0';
    GlobalUnlock(mem);
    if (!OpenClipboard(NULL)) {
        GlobalFree(mem);
        return 0;
    }
    EmptyClipboard();
    if (!SetClipboardData(CF_UNICODETEXT, mem)) {
        CloseClipboard();
        GlobalFree(mem);
        return 0;
    }
    CloseClipboard();
    return 1;
}

int input_paste(void) {
    return input_key("ctrl+v");
}

int input_text_any(const char *utf8_text) {
    if (!utf8_text || !*utf8_text) {
        return 0;
    }
    int ascii_only = 1;
    for (const unsigned char *p = (const unsigned char *)utf8_text; *p; ++p) {
        if (*p >= 0x80) {
            ascii_only = 0;
            break;
        }
    }
    if (ascii_only) {
        return input_type_text(utf8_text);
    }
    /* CJK 等非 ASCII：使用剪贴板 + Ctrl+V，避免部分控件不接收 KEYEVENTF_UNICODE */
    if (!input_clipboard_text(utf8_text)) {
        return input_type_text(utf8_text);
    }
    return input_paste();
}
