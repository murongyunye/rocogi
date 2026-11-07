#include "hotkey.h"

#include <windows.h>

#define HK_START 1
#define HK_STOP 2
#define HK_TRACK 3

static volatile LONG g_last = 0;
static volatile LONG g_count = 0;
static volatile LONG g_ready = 0;
static HANDLE g_thread = NULL;
static DWORD g_tid = 0;
static int g_registered = 0;
static int g_mods = 0;

static int register_set(UINT mods) {
    int n = 0;
    if (RegisterHotKey(NULL, HK_START, mods, VK_F9)) n++;
    if (RegisterHotKey(NULL, HK_STOP, mods, VK_F10)) n++;
    if (RegisterHotKey(NULL, HK_TRACK, mods, VK_F11)) n++;
    return n;
}

/* 热键必须注册在拥有消息循环的线程里，所以线程内注册 */
static DWORD WINAPI hotkey_loop(void *arg) {
    (void)arg;
    MSG msg;
    PeekMessage(&msg, NULL, WM_USER, WM_USER, PM_NOREMOVE); /* 建立线程消息队列 */
    g_registered = register_set(0);
    if (g_registered == 0) {
        g_registered = register_set(MOD_CONTROL | MOD_ALT);
        if (g_registered) {
            g_mods = MOD_CONTROL | MOD_ALT;
        }
    }
    InterlockedExchange(&g_ready, 1);
    if (g_registered == 0) {
        return 0;
    }
    while (GetMessage(&msg, NULL, 0, 0)) {
        if (msg.message == WM_HOTKEY) {
            InterlockedExchange(&g_last, (LONG)msg.wParam);
            InterlockedIncrement(&g_count);
        }
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return 0;
}

int hotkey_start(void) {
    if (g_thread) {
        return g_registered;
    }
    g_ready = 0;
    g_registered = 0;
    g_thread = CreateThread(NULL, 0, hotkey_loop, NULL, 0, &g_tid);
    if (!g_thread) {
        return 0;
    }
    for (int i = 0; i < 50 && !g_ready; ++i) {
        Sleep(10);
    }
    return g_registered;
}

void hotkey_stop(void) {
    if (g_thread) {
        if (g_tid) {
            PostThreadMessage(g_tid, WM_QUIT, 0, 0);
        }
        WaitForSingleObject(g_thread, 500);
        CloseHandle(g_thread);
        g_thread = NULL;
    }
    g_registered = 0;
}

int hotkey_last_id(void) {
    return (int)InterlockedCompareExchange(&g_last, 0, 0);
}

int hotkey_count(void) {
    return (int)InterlockedCompareExchange(&g_count, 0, 0);
}

int hotkey_modifiers(void) {
    return g_mods;
}
