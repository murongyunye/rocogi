#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

#include "host.h"
#include "http.h"
#include "mapstat.h"
#include "routes.h"

/* 显式声明 Per-Monitor V2 DPI 感知：保证 GetWindowRect / PrintWindow / BitBlt
   返回的坐标与像素在多显示器、不同缩放下一致，避免截图尺寸飘忽破坏模板匹配。
   这是进程内调用，不修改系统 DPI 设置。 */
static void init_dpi_awareness(void) {
    HMODULE u = GetModuleHandleW(L"user32.dll");
    if (u) {
        typedef BOOL(WINAPI * PFN)(HANDLE);
        PFN set_ctx = (PFN)GetProcAddress(u, "SetProcessDpiAwarenessContext");
        if (set_ctx) {
            /* DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4 */
            if (set_ctx((HANDLE)(intptr_t)-4)) {
                return;
            }
        }
    }
    /* Windows 10 1607 之前的回退 */
    SetProcessDPIAware();
}

static void print_usage(void) {
    printf("rocogi-core [--port 8788] [--host 127.0.0.1] [--root <dir>] [--static <dir>] [--data <dir>] [--workflows <dir>]\n");
}

int main(int argc, char **argv) {
    init_dpi_awareness();

    const char *exe_dir = host_exe_dir();
    char *root = host_path_join(exe_dir, "..\\..");
    char *static_dir = NULL;
    char *data_dir = NULL;
    char *workflows_dir = host_path_join(exe_dir, "..\\workflows");
    const char *host = "127.0.0.1";
    int port = 8788;

    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--port") == 0 && i + 1 < argc) {
            port = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--host") == 0 && i + 1 < argc) {
            host = argv[++i];
        } else if (strcmp(argv[i], "--root") == 0 && i + 1 < argc) {
            free(root);
            root = host_path_join(argv[++i], "");
        } else if (strcmp(argv[i], "--static") == 0 && i + 1 < argc) {
            free(static_dir);
            static_dir = host_path_join(argv[++i], "");
        } else if (strcmp(argv[i], "--data") == 0 && i + 1 < argc) {
            free(data_dir);
            data_dir = host_path_join(argv[++i], "");
        } else if (strcmp(argv[i], "--workflows") == 0 && i + 1 < argc) {
            free(workflows_dir);
            workflows_dir = host_path_join(argv[++i], "");
        } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            print_usage();
            return 0;
        } else {
            printf("未知参数：%s\n", argv[i]);
            print_usage();
            return 2;
        }
    }

    if (!static_dir) static_dir = host_path_join(root, "frontend\\dist");
    if (!data_dir) data_dir = host_path_join(root, "data");

    printf("rocogi-core (C core, yotta-style contracts)\n");
    printf("  root      : %s\n", root);
    printf("  static    : %s\n", static_dir);
    printf("  data      : %s\n", data_dir);
    printf("  workflows : %s\n", workflows_dir);

    char *map_dir = host_path_join(data_dir, "map");
    if (map_dir) {
        int ok = mapstat_init(map_dir);
        printf("  map stats : %s (%d points)\n", ok ? "loaded" : "unavailable", mapstat_point_count());
        free(map_dir);
    }

    routes_init(root, data_dir, static_dir, workflows_dir);

    int rc = http_run(host, port, routes_handle);
    if (!rc) {
        fprintf(stderr, "无法监听 %s:%d\n", host, port);
    }

    free(root);
    free(static_dir);
    free(data_dir);
    free(workflows_dir);
    return rc ? 0 : 1;
}
