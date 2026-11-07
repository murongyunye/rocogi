#include "routes.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

#include "capture.h"
#include "host.h"
#include "hotkey.h"
#include "input.h"
#include "mapstat.h"
#include "match.h"
#include "nodes.h"
#include "pngio.h"
#include "static.h"
#include "strbuf.h"
#include "winenum.h"
#include "workflow.h"

static char *g_root = NULL;
static char *g_data_dir = NULL;
static char *g_static_dir = NULL;
static char *g_workflows_dir = NULL;
static int g_run_count = 0;
static int g_hotkeys_registered = 0;
static volatile LONG g_shot_seq = 0;
static unsigned long long g_started_at = 0;

static char *dup_str(const char *s) {
    if (!s) return NULL;
    size_t n = strlen(s);
    char *out = (char *)malloc(n + 1);
    if (out) memcpy(out, s, n + 1);
    return out;
}

void routes_init(const char *root, const char *data_dir, const char *static_dir, const char *workflows_dir) {
    g_root = dup_str(root);
    g_data_dir = dup_str(data_dir);
    g_static_dir = dup_str(static_dir);
    g_workflows_dir = dup_str(workflows_dir);
    g_started_at = GetTickCount64();
    g_hotkeys_registered = hotkey_start();
}

static void reply_json(http_response *res, int status, strbuf *sb) {
    http_reply_alloc(res, status, "application/json; charset=utf-8", sb->data, sb->len);
    sb->data = NULL;
    sb->len = 0;
}

static void reply_error(http_response *res, int status, const char *detail) {
    strbuf sb;
    sb_init(&sb);
    sb_put(&sb, "{\"detail\":");
    sb_json_str(&sb, detail);
    sb_put(&sb, "}");
    reply_json(res, status, &sb);
}

/* ------------------------------------------------ 阶段 1 辅助 */

static jval *body_parse(const http_request *req) {
    if (!req->body || req->body_len == 0) {
        return NULL;
    }
    return json_parse(req->body, req->body_len);
}

static void window_title_utf8(HWND hwnd, char *out, size_t cap) {
    WCHAR wbuf[512];
    if (!hwnd || !GetWindowTextW(hwnd, wbuf, 512)) {
        out[0] = '\0';
        return;
    }
    if (!WideCharToMultiByte(CP_UTF8, 0, wbuf, -1, out, (int)cap, NULL, NULL)) {
        out[0] = '\0';
    }
}

static void window_class_utf8(HWND hwnd, char *out, size_t cap) {
    WCHAR wbuf[256];
    if (!hwnd || !GetClassNameW(hwnd, wbuf, 256)) {
        out[0] = '\0';
        return;
    }
    if (!WideCharToMultiByte(CP_UTF8, 0, wbuf, -1, out, (int)cap, NULL, NULL)) {
        out[0] = '\0';
    }
}

static HWND find_window(const jval *body) {
    double h = json_num(json_get(body, "hwnd"), 0);
    if (h > 0) {
        HWND w = (HWND)(intptr_t)(long long)h;
        if (IsWindow(w)) {
            return w;
        }
    }
    const char *needle = json_str(json_get(body, "title"), "");
    if (!needle || !*needle) {
        return NULL;
    }
    win_info wins[96];
    int n = win_enum_visible(wins, 96);
    for (int i = 0; i < n; ++i) {
        if (strstr(wins[i].title, needle)) {
            return wins[i].hwnd;
        }
    }
    return NULL;
}

/* 禁止操作系统关键窗口 */
static int protected_window(HWND hwnd) {
    char cls[128];
    window_class_utf8(hwnd, cls, sizeof(cls));
    if (strcmp(cls, "Shell_TrayWnd") == 0 || strcmp(cls, "Shell_SecondaryTrayWnd") == 0 ||
        strcmp(cls, "Progman") == 0 || strcmp(cls, "WorkerW") == 0) {
        return 1;
    }
    char title[256];
    window_title_utf8(hwnd, title, sizeof(title));
    return strstr(title, "Program Manager") != NULL;
}

static const char *captures_dir(void) {
    static char *dir = NULL;
    if (!dir) {
        dir = host_path_join(g_root, "captures");
        CreateDirectoryA(dir, NULL);
    }
    return dir;
}

static int resolve_tpl(const char *name, char *out, size_t cap) {
    if (!name || !*name) {
        return 0;
    }
    if (strchr(name, ':') || name[0] == '/' || name[0] == '\\') {
        snprintf(out, cap, "%s", name);
        return 1;
    }
    if (!g_data_dir) {
        return 0;
    }
    if (strstr(name, ".png") || strstr(name, ".PNG")) {
        snprintf(out, cap, "%s\\templates\\%s", g_data_dir, name);
    } else {
        snprintf(out, cap, "%s\\templates\\%s.png", g_data_dir, name);
    }
    return 1;
}

static void window_meta(strbuf *sb, HWND hwnd) {
    char title[256];
    char cls[128];
    window_title_utf8(hwnd, title, sizeof(title));
    window_class_utf8(hwnd, cls, sizeof(cls));
    RECT rc;
    memset(&rc, 0, sizeof(rc));
    GetWindowRect(hwnd, &rc);
    sb_put(sb, "{\"hwnd\":");
    sb_putf(sb, "%lld", (long long)(intptr_t)hwnd);
    sb_put(sb, ",\"title\":");
    sb_json_str(sb, title);
    sb_put(sb, ",\"class\":");
    sb_json_str(sb, cls);
    sb_put(sb, ",\"rect\":{\"x\":");
    sb_putf(sb, "%ld", rc.left);
    sb_put(sb, ",\"y\":");
    sb_putf(sb, "%ld", rc.top);
    sb_put(sb, ",\"width\":");
    sb_putf(sb, "%ld", rc.right - rc.left);
    sb_put(sb, ",\"height\":");
    sb_putf(sb, "%ld", rc.bottom - rc.top);
    sb_put(sb, "},\"minimized\":");
    sb_put(sb, IsIconic(hwnd) ? "true" : "false");
    sb_put(sb, "}");
}

static int capture_target(const jval *body, HWND *out_hwnd, capture_result *cap) {
    int desktop = json_bool(json_get(body, "desktop"), 0);
    HWND hwnd = desktop ? NULL : find_window(body);
    *out_hwnd = hwnd;
    if (hwnd) {
        const char *force = json_str(json_get(body, "force"), "");
        if (_stricmp(force, "bitblt") == 0) {
            return capture_window_bitblt(hwnd, cap);
        }
        return capture_window(hwnd, cap);
    }
    return capture_desktop(cap);
}

static void handle_windows(http_response *res) {
    win_info wins[96];
    int n = win_enum_visible(wins, 96);
    strbuf sb;
    sb_init(&sb);
    sb_put(&sb, "{\"count\":");
    sb_putf(&sb, "%d", n);
    sb_put(&sb, ",\"windows\":[");
    HWND fg = GetForegroundWindow();
    for (int i = 0; i < n; ++i) {
        if (i) sb_put(&sb, ",");
        sb_put(&sb, "{\"hwnd\":");
        sb_putf(&sb, "%lld", (long long)(intptr_t)wins[i].hwnd);
        sb_put(&sb, ",\"title\":");
        sb_json_str(&sb, wins[i].title);
        sb_put(&sb, ",\"class\":");
        sb_json_str(&sb, wins[i].cls);
        sb_put(&sb, ",\"rect\":{\"x\":");
        sb_putf(&sb, "%ld", wins[i].rect.left);
        sb_put(&sb, ",\"y\":");
        sb_putf(&sb, "%ld", wins[i].rect.top);
        sb_put(&sb, ",\"width\":");
        sb_putf(&sb, "%ld", wins[i].rect.right - wins[i].rect.left);
        sb_put(&sb, ",\"height\":");
        sb_putf(&sb, "%ld", wins[i].rect.bottom - wins[i].rect.top);
        sb_put(&sb, "},\"minimized\":");
        sb_put(&sb, wins[i].minimized ? "true" : "false");
        sb_put(&sb, ",\"foreground\":");
        sb_put(&sb, wins[i].hwnd == fg ? "true" : "false");
        sb_put(&sb, "}");
    }
    sb_put(&sb, "]}");
    reply_json(res, 200, &sb);
}

static void handle_capture_test(const http_request *req, http_response *res) {
    jval *body = body_parse(req);
    const char *explicit_title = json_str(json_get(body, "title"), "");
    HWND hwnd = NULL;
    capture_result cap;
    memset(&cap, 0, sizeof(cap));
    int ok = capture_target(body, &hwnd, &cap);
    if (!ok && explicit_title && *explicit_title) {
        json_free(body);
        reply_error(res, 404, "未找到窗口或截图失败");
        return;
    }
    if (!ok) {
        json_free(body);
        reply_error(res, 500, "截图失败");
        return;
    }

    unsigned long long tick = GetTickCount64();
    unsigned int seq = (unsigned int)InterlockedIncrement(&g_shot_seq);
    char path[MAX_PATH];
    snprintf(path, sizeof(path), "%s\\capture-%llu-%u.png", captures_dir(), tick, seq);
    int saved = capture_save_png(&cap, path);
    if (!saved) {
        snprintf(path, sizeof(path), "(未写入)");
    }

    int compare = json_bool(json_get(body, "compare"), 0);
    capture_result cap2;
    memset(&cap2, 0, sizeof(cap2));
    double diff = -1.0;
    char path2[MAX_PATH];
    path2[0] = '\0';
    if (compare) {
        if (hwnd) {
            ok = capture_window(hwnd, &cap2);
        } else {
            ok = capture_desktop(&cap2);
        }
        if (ok) {
            diff = capture_diff(&cap, &cap2);
            snprintf(path2, sizeof(path2), "%s\\capture-%llu-%u-b.png", captures_dir(), tick, seq);
            capture_save_png(&cap2, path2);
        }
        capture_free(&cap2);
    }

    strbuf sb;
    sb_init(&sb);
    sb_put(&sb, "{\"ok\":true,\"method\":");
    sb_json_str(&sb, cap.method_name);
    sb_put(&sb, ",\"width\":");
    sb_putf(&sb, "%d", cap.width);
    sb_put(&sb, ",\"height\":");
    sb_putf(&sb, "%d", cap.height);
    sb_put(&sb, ",\"path\":");
    sb_json_str(&sb, path);
    sb_put(&sb, ",\"ms\":");
    sb_json_num(&sb, cap.ms);
    sb_put(&sb, ",\"blank\":");
    sb_put(&sb, capture_is_blank(&cap) ? "true" : "false");
    sb_put(&sb, ",\"note\":");
    sb_json_str(&sb, cap.note);
    sb_put(&sb, ",\"desktop\":");
    sb_put(&sb, hwnd ? "false" : "true");
    if (hwnd) {
        sb_put(&sb, ",\"window\":");
        window_meta(&sb, hwnd);
    }
    if (compare) {
        sb_put(&sb, ",\"compare\":{\"diff\":");
        sb_json_num(&sb, diff);
        sb_put(&sb, ",\"path2\":");
        sb_json_str(&sb, path2);
        sb_put(&sb, "}");
    }
    sb_put(&sb, "}");
    capture_free(&cap);
    json_free(body);
    reply_json(res, 200, &sb);
}

static void handle_input_test(const http_request *req, http_response *res) {
    jval *body = body_parse(req);
    HWND hwnd = find_window(body);
    if (!hwnd) {
        json_free(body);
        reply_error(res, 404, "未找到目标窗口");
        return;
    }
    if (protected_window(hwnd)) {
        json_free(body);
        reply_error(res, 403, "拒绝对系统关键窗口注入输入");
        return;
    }

    char title_before[256];
    window_title_utf8(hwnd, title_before, sizeof(title_before));
    unsigned long long t0 = GetTickCount64();
    int focus = json_bool(json_get(body, "focus"), 1);
    int focused = focus ? input_focus_window(hwnd) : (GetForegroundWindow() == hwnd);

    strbuf sb;
    sb_init(&sb);
    sb_put(&sb, "{\"ok\":true,\"hwnd\":");
    sb_putf(&sb, "%lld", (long long)(intptr_t)hwnd);
    sb_put(&sb, ",\"title_before\":");
    sb_json_str(&sb, title_before);
    sb_put(&sb, ",\"focused\":");
    sb_put(&sb, focused ? "true" : "false");

    int want_click = json_bool(json_get(body, "click"), 0);
    if (want_click) {
        int x = (int)json_num(json_get(body, "x"), 0);
        int y = (int)json_num(json_get(body, "y"), 0);
        const char *button = json_str(json_get(body, "button"), "left");
        int clicks = (int)json_num(json_get(body, "clicks"), 1);
        int code = _stricmp(button, "right") == 0 ? 1 : (_stricmp(button, "middle") == 0 ? 2 : 0);
        int r = input_click(x, y, 1, hwnd, code, clicks);
        sb_put(&sb, ",\"click\":{\"x\":");
        sb_putf(&sb, "%d", x);
        sb_put(&sb, ",\"y\":");
        sb_putf(&sb, "%d", y);
        sb_put(&sb, ",\"button\":");
        sb_json_str(&sb, button);
        sb_put(&sb, ",\"ok\":");
        sb_put(&sb, r ? "true" : "false");
        sb_put(&sb, "}");
        Sleep(60);
    }

    const char *keys = json_str(json_get(body, "keys"), "");
    if (*keys) {
        int r = input_key(keys);
        sb_put(&sb, ",\"keys\":{\"combo\":");
        sb_json_str(&sb, keys);
        sb_put(&sb, ",\"ok\":");
        sb_put(&sb, r ? "true" : "false");
        sb_put(&sb, "}");
        Sleep(40);
    }

    const char *text = json_str(json_get(body, "text"), "");
    if (*text) {
        int r = input_text_any(text);
        sb_put(&sb, ",\"text\":{\"value\":");
        sb_json_str(&sb, text);
        sb_put(&sb, ",\"ok\":");
        sb_put(&sb, r ? "true" : "false");
        sb_put(&sb, ",\"method\":");
        sb_json_str(&sb, "auto");
        sb_put(&sb, "}");
    }

    char title_after[256];
    window_title_utf8(hwnd, title_after, sizeof(title_after));
    sb_put(&sb, ",\"title_after\":");
    sb_json_str(&sb, title_after);
    sb_put(&sb, ",\"elapsed_ms\":");
    sb_putf(&sb, "%llu", (unsigned long long)(GetTickCount64() - t0));
    sb_put(&sb, "}");
    json_free(body);
    reply_json(res, 200, &sb);
}

static void handle_match_test(const http_request *req, http_response *res) {
    jval *body = body_parse(req);
    capture_result cap;
    memset(&cap, 0, sizeof(cap));
    HWND hwnd = NULL;
    if (!capture_target(body, &hwnd, &cap)) {
        json_free(body);
        reply_error(res, 500, "截图失败，无法匹配");
        return;
    }

    const char *tpl_name = json_str(json_get(body, "template"), "");
    double threshold = json_num(json_get(body, "threshold"), 0.5);
    jval *crop = json_get(body, "crop");
    char tpl_path[MAX_PATH];
    tpl_path[0] = '\0';
    int crop_x = -1, crop_y = -1;
    match_result mr;
    memset(&mr, 0, sizeof(mr));
    int ok = 0;

    if (crop && crop->t == JARR && crop->count >= 4) {
        crop_x = (int)json_num(crop->items[0], 0);
        crop_y = (int)json_num(crop->items[1], 0);
        int cw = (int)json_num(crop->items[2], 0);
        int ch = (int)json_num(crop->items[3], 0);
        if (cw > 0 && ch > 0 && crop_x >= 0 && crop_y >= 0 &&
            crop_x + cw <= cap.width && crop_y + ch <= cap.height) {
            unsigned char *buf = (unsigned char *)malloc((size_t)cw * (size_t)ch * 4);
            if (buf) {
                for (int y = 0; y < ch; ++y) {
                    memcpy(buf + (size_t)y * cw * 4,
                           cap.bgra + ((size_t)(crop_y + y) * cap.width + crop_x) * 4,
                           (size_t)cw * 4);
                }
                snprintf(tpl_path, sizeof(tpl_path), "%s\\template-crop-%llu-%u.png",
                         captures_dir(), GetTickCount64(),
                         (unsigned int)InterlockedIncrement(&g_shot_seq));
                png_write_bgra(tpl_path, cw, ch, buf);
                ok = match_bgra(cap.bgra, cap.width, cap.height, buf, cw, ch, threshold, &mr);
                free(buf);
            }
        }
    }

    if (!ok) {
        int have = resolve_tpl(tpl_name, tpl_path, sizeof(tpl_path));
        ok = have ? match_file(tpl_path, cap.bgra, cap.width, cap.height, threshold, &mr) : 0;
        crop_x = -1;
        crop_y = -1;
    }

    double deviation = -1.0;
    if (ok && crop_x >= 0) {
        double dx = (double)(mr.x - crop_x);
        double dy = (double)(mr.y - crop_y);
        deviation = sqrt(dx * dx + dy * dy);
    }

    strbuf sb;
    sb_init(&sb);
    sb_put(&sb, "{\"ok\":");
    sb_put(&sb, ok ? "true" : "false");
    sb_put(&sb, ",\"template\":");
    sb_json_str(&sb, tpl_path);
    sb_put(&sb, ",\"threshold\":");
    sb_json_num(&sb, threshold);
    sb_put(&sb, ",\"capture\":{\"method\":");
    sb_json_str(&sb, cap.method_name);
    sb_put(&sb, ",\"width\":");
    sb_putf(&sb, "%d", cap.width);
    sb_put(&sb, ",\"height\":");
    sb_putf(&sb, "%d", cap.height);
    sb_put(&sb, ",\"ms\":");
    sb_json_num(&sb, cap.ms);
    sb_put(&sb, "}");
    if (ok) {
        sb_put(&sb, ",\"score\":");
        sb_json_num(&sb, mr.score);
        sb_put(&sb, ",\"x\":");
        sb_putf(&sb, "%d", mr.x);
        sb_put(&sb, ",\"y\":");
        sb_putf(&sb, "%d", mr.y);
        sb_put(&sb, ",\"w\":");
        sb_putf(&sb, "%d", mr.w);
        sb_put(&sb, ",\"h\":");
        sb_putf(&sb, "%d", mr.h);
        sb_put(&sb, ",\"match_ms\":");
        sb_json_num(&sb, mr.ms);
        sb_put(&sb, ",\"levels\":");
        sb_putf(&sb, "%d", mr.levels);
        sb_put(&sb, ",\"coarse_candidates\":");
        sb_putf(&sb, "%d", mr.coarse_candidates);
        sb_put(&sb, ",\"matched\":");
        sb_put(&sb, mr.score >= threshold ? "true" : "false");
    }
    if (deviation >= 0) {
        sb_put(&sb, ",\"crop\":{\"x\":");
        sb_putf(&sb, "%d", crop_x);
        sb_put(&sb, ",\"y\":");
        sb_putf(&sb, "%d", crop_y);
        sb_put(&sb, ",\"deviation_px\":");
        sb_json_num(&sb, deviation);
        sb_put(&sb, "}");
    }
    sb_put(&sb, "}");
    capture_free(&cap);
    json_free(body);
    reply_json(res, 200, &sb);
}

static void handle_hotkeys(http_response *res) {
    strbuf sb;
    sb_init(&sb);
    sb_put(&sb, "{\"registered\":");
    sb_putf(&sb, "%d", g_hotkeys_registered);
    sb_put(&sb, ",\"bindings\":[\"f9\",\"f10\",\"f11\"],\"modifiers\":");
    sb_json_str(&sb, hotkey_modifiers() ? "ctrl+alt" : "none");
    sb_put(&sb, ",\"last_id\":");
    sb_putf(&sb, "%d", hotkey_last_id());
    sb_put(&sb, ",\"events\":");
    sb_putf(&sb, "%d", hotkey_count());
    sb_put(&sb, "}");
    reply_json(res, 200, &sb);
}

static void handle_health(http_response *res) {
    strbuf sb;
    sb_init(&sb);
    sb_put(&sb, "{\"ok\":true,\"engine\":\"c\",\"version\":\"0.2.0\",\"service\":\"rocoflow\",\"uptime_ms\":");
    sb_putf(&sb, "%llu", (unsigned long long)(GetTickCount64() - g_started_at));
    sb_put(&sb, "}");
    reply_json(res, 200, &sb);
}

static void handle_meta(http_response *res) {
    strbuf sb;
    sb_init(&sb);
    int workflows = g_workflows_dir ? host_count_files(g_workflows_dir, "json") : 0;
    int templates = 0;
    if (g_data_dir) {
        char *tpl_dir = host_path_join(g_data_dir, "templates");
        if (tpl_dir) {
            templates = host_count_files(tpl_dir, "png");
            free(tpl_dir);
        }
    }

    sb_put(&sb, "{\"version\":\"0.2.0\",\"platform\":{");
    sb_put(&sb, "\"platform\":\"win32\",\"windows\":true,\"mock_target\":true,");
    sb_put(&sb, "\"interception\":false,\"sift\":false,\"battle_ai\":false,");
    sb_put(&sb, "\"reads_game_memory\":false,\"data_dir\":");
    sb_json_str(&sb, g_data_dir ? g_data_dir : "");
    sb_put(&sb, ",\"engine\":\"c\"},");

    sb_put(&sb, "\"target\":{\"kind\":\"mock\",\"title\":");
    sb_json_str(&sb, "洛克王国：世界（模拟窗口）");
    sb_put(&sb, ",\"width\":2560,\"height\":1600,\"scene\":\"field\"},");

    sb_put(&sb, "\"settings\":{");
    sb_put(&sb, "\"target\":{\"slot\":\"nrc-game\",\"kind\":\"mock\",\"window_title\":");
    sb_json_str(&sb, "洛克王国：世界");
    sb_put(&sb, ",\"capture_fps\":4,\"scale\":1},");
    sb_put(&sb, "\"input\":{\"backend\":\"mock\"},");
    sb_put(&sb, "\"hotkeys\":{\"enabled\":true,\"start\":\"f9\",\"stop\":\"f10\",\"tracker\":\"f11\"},");
    sb_put(&sb, "\"engine\":{\"max_steps\":1200,\"max_visits\":80,\"step_delay_ms\":0},");
    sb_put(&sb, "\"vision\":{\"threshold\":0.5,\"use_edges\":true,\"downscale\":0.5},");
    sb_put(&sb, "\"map\":{\"position_source\":\"mock\",\"sift_max_edge\":1600,\"cache_anchors\":true,");
    sb_put(&sb, "\"minimap_region\":[0.84,0.0275,0.1172,0.1875]},");
    sb_put(&sb, "\"battle\":{\"simulations\":40,\"max_turns\":24},");
    sb_put(&sb, "\"realtime\":{\"interval\":0.6,\"auto_ball\":true,\"battle_response\":true,");
    sb_put(&sb, "\"party_confirm\":true,\"normal_strategy\":\"gather\",\"polluted_strategy\":\"escape\",");
    sb_put(&sb, "\"threshold\":0.45,\"save_screenshots\":true},");
    sb_put(&sb, "\"tracker\":{\"interval\":0.5,\"confidenceMin\":0.25,\"screenshotEvery\":2},");
    sb_put(&sb, "\"demo\":{\"scene\":\"auto\"}},");

    sb_put(&sb, "\"workflowCount\":");
    sb_putf(&sb, "%d", workflows);
    sb_put(&sb, ",\"runCount\":");
    sb_putf(&sb, "%d", g_run_count);
    sb_put(&sb, ",\"map\":");
    sb_put(&sb, mapstat_json());
    sb_put(&sb, ",\"resources\":");
    sb_putf(&sb, "%d", templates);
    sb_put(&sb, ",\"activeRuns\":0,\"realtime\":{\"running\":false},\"tracker\":{\"running\":false}}");
    reply_json(res, 200, &sb);
}

static void handle_nodes(http_response *res) {
    strbuf sb;
    sb_init(&sb);
    nodes_json(&sb);
    reply_json(res, 200, &sb);
}

static void handle_validate(const http_request *req, http_response *res) {
    if (!req->body || req->body_len == 0) {
        reply_error(res, 400, "请求体为空");
        return;
    }
    workflow wf;
    strbuf errors;
    sb_init(&errors);
    int parsed = workflow_parse(req->body, req->body_len, &wf, &errors);
    int ok = 0;
    if (parsed) {
        ok = workflow_validate(&wf, &errors);
    }
    strbuf sb;
    sb_init(&sb);
    sb_put(&sb, "{\"ok\":");
    sb_put(&sb, ok ? "true" : "false");
    sb_put(&sb, ",\"nodeCount\":");
    sb_putf(&sb, "%d", parsed ? wf.n_nodes : 0);
    sb_put(&sb, ",\"edgeCount\":");
    sb_putf(&sb, "%d", parsed ? wf.n_edges : 0);
    sb_put(&sb, ",\"errors\":[");
    if (errors.len) {
        sb_put(&sb, errors.data);
    }
    sb_put(&sb, "]}");
    workflow_free(&wf);
    sb_free(&errors);
    reply_json(res, 200, &sb);
}

static void handle_run(const http_request *req, http_response *res) {
    if (!req->body || req->body_len == 0) {
        reply_error(res, 400, "请求体为空");
        return;
    }
    workflow wf;
    strbuf errors;
    sb_init(&errors);
    int parsed = workflow_parse(req->body, req->body_len, &wf, &errors);
    if (!parsed) {
        strbuf sb;
        sb_init(&sb);
        sb_put(&sb, "{\"ok\":false,\"errors\":[");
        if (errors.len) sb_put(&sb, errors.data);
        sb_put(&sb, "]}");
        workflow_free(&wf);
        sb_free(&errors);
        reply_json(res, 400, &sb);
        return;
    }
    if (!workflow_validate(&wf, &errors)) {
        strbuf sb;
        sb_init(&sb);
        sb_put(&sb, "{\"ok\":false,\"errors\":[");
        if (errors.len) sb_put(&sb, errors.data);
        sb_put(&sb, "]}");
        workflow_free(&wf);
        sb_free(&errors);
        reply_json(res, 400, &sb);
        return;
    }

    strbuf result;
    sb_init(&result);
    strbuf run_errors;
    sb_init(&run_errors);
    jval *meta = json_parse(req->body, req->body_len);
    HWND target = meta ? find_window(meta) : NULL;
    workflow_set_runtime(g_data_dir, target);
    json_free(meta);
    int ok = workflow_run(&wf, &result, &run_errors);
    if (ok) {
        g_run_count++;
        reply_json(res, 200, &result);
    } else {
        reply_json(res, 500, &result);
    }
    workflow_free(&wf);
    sb_free(&errors);
    sb_free(&run_errors);
    if (res->body != result.data) {
        sb_free(&result);
    }
}

static void serve_spa(const http_request *req, http_response *res) {
    if (static_serve(g_static_dir, req->path, res)) {
        return;
    }
    char *index = host_path_join(g_static_dir, "index.html");
    char *data = NULL;
    size_t len = 0;
    if (index && host_read_file(index, &data, &len)) {
        http_reply_alloc(res, 200, "text/html; charset=utf-8", data, len);
    } else {
        reply_error(res, 404, "前端构建产物不存在，请先执行 npm run build");
    }
    free(index);
}

void routes_handle(const http_request *req, http_response *res) {
    if (strcmp(req->method, "OPTIONS") == 0) {
        http_reply(res, 204, "text/plain; charset=utf-8", "");
        return;
    }

    if (strcmp(req->path, "/api/health") == 0) {
        handle_health(res);
        return;
    }
    if (strcmp(req->path, "/api/meta") == 0) {
        handle_meta(res);
        return;
    }
    if (strcmp(req->path, "/api/nodes") == 0) {
        handle_nodes(res);
        return;
    }
    if (strcmp(req->path, "/api/workflows/validate") == 0) {
        if (strcmp(req->method, "POST") != 0) {
            reply_error(res, 405, "仅支持 POST");
            return;
        }
        handle_validate(req, res);
        return;
    }
    if (strcmp(req->path, "/api/workflows/run") == 0) {
        if (strcmp(req->method, "POST") != 0) {
            reply_error(res, 405, "仅支持 POST");
            return;
        }
        handle_run(req, res);
        return;
    }
    if (strcmp(req->path, "/api/windows") == 0) {
        handle_windows(res);
        return;
    }
    if (strcmp(req->path, "/api/hotkeys") == 0) {
        handle_hotkeys(res);
        return;
    }
    if (strcmp(req->path, "/api/capture/test") == 0) {
        if (strcmp(req->method, "POST") != 0) {
            reply_error(res, 405, "仅支持 POST");
            return;
        }
        handle_capture_test(req, res);
        return;
    }
    if (strcmp(req->path, "/api/input/test") == 0) {
        if (strcmp(req->method, "POST") != 0) {
            reply_error(res, 405, "仅支持 POST");
            return;
        }
        handle_input_test(req, res);
        return;
    }
    if (strcmp(req->path, "/api/match/test") == 0) {
        if (strcmp(req->method, "POST") != 0) {
            reply_error(res, 405, "仅支持 POST");
            return;
        }
        handle_match_test(req, res);
        return;
    }
    if (strncmp(req->path, "/api/assets/map/", 16) == 0) {
        char *map_dir = g_data_dir ? host_path_join(g_data_dir, "map") : NULL;
        if (map_dir) {
            const char *rel = req->path + 16;
            if (!strstr(rel, "..") && static_serve(map_dir, rel, res)) {
                free(map_dir);
                return;
            }
            free(map_dir);
        }
        reply_error(res, 404, "资源不存在");
        return;
    }
    if (strncmp(req->path, "/api", 4) == 0) {
        reply_error(res, 404, "接口不存在");
        return;
    }
    serve_spa(req, res);
}
