#include "workflow.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

#include "capture.h"
#include "input.h"
#include "match.h"
#include "nodes.h"

#define MAX_STEPS 64
#define MAX_DEPTH 24

static char *g_data_dir = NULL;
static HWND g_target = NULL;

void workflow_set_runtime(const char *data_dir, void *target_hwnd) {
    free(g_data_dir);
    g_data_dir = NULL;
    if (data_dir && *data_dir) {
        size_t n = strlen(data_dir);
        g_data_dir = (char *)malloc(n + 1);
        if (g_data_dir) {
            memcpy(g_data_dir, data_dir, n + 1);
        }
    }
    g_target = (HWND)target_hwnd;
}

static char *dup_str(const char *s) {
    if (!s) {
        return NULL;
    }
    size_t n = strlen(s);
    char *out = (char *)malloc(n + 1);
    if (out) {
        memcpy(out, s, n + 1);
    }
    return out;
}

static void err_add(strbuf *errors, const char *msg) {
    if (!errors) {
        return;
    }
    if (errors->len) {
        sb_put(errors, ", ");
    }
    sb_json_str(errors, msg);
}

/* ---------------------------------------------------------------- 解析 */

int workflow_parse(const char *text, size_t len, workflow *wf, strbuf *errors) {
    memset(wf, 0, sizeof(*wf));
    wf->root = json_parse(text, len);
    if (!wf->root || wf->root->t != JOBJ) {
        err_add(errors, "工作流根节点必须是 JSON 对象");
        return 0;
    }
    wf->id = dup_str(json_str(json_get(wf->root, "id"), ""));
    wf->name = dup_str(json_str(json_get(wf->root, "name"), ""));

    jval *nodes = json_get(wf->root, "nodes");
    if (!nodes || nodes->t != JARR || nodes->count == 0) {
        err_add(errors, "nodes 必须是非空数组");
        return 0;
    }
    wf->nodes = (wf_node *)calloc((size_t)nodes->count, sizeof(wf_node));
    if (!wf->nodes) {
        err_add(errors, "内存不足");
        return 0;
    }
    wf->n_nodes = nodes->count;
    for (int i = 0; i < nodes->count; ++i) {
        jval *n = nodes->items[i];
        if (!n || n->t != JOBJ) {
            err_add(errors, "nodes 中存在非对象元素");
            continue;
        }
        wf->nodes[i].id = dup_str(json_str(json_get(n, "id"), ""));
        wf->nodes[i].type = dup_str(json_str(json_get(n, "type"), ""));
        wf->nodes[i].params = json_get(n, "params");
    }

    jval *edges = json_get(wf->root, "edges");
    if (edges && edges->t == JARR) {
        wf->edges = (wf_edge *)calloc((size_t)edges->count, sizeof(wf_edge));
        if (!wf->edges) {
            err_add(errors, "内存不足");
            return 0;
        }
        wf->n_edges = edges->count;
        for (int i = 0; i < edges->count; ++i) {
            jval *e = edges->items[i];
            if (!e || e->t != JOBJ) {
                continue;
            }
            wf->edges[i].from = dup_str(json_str(json_get(e, "from"), ""));
            wf->edges[i].to = dup_str(json_str(json_get(e, "to"), ""));
            wf->edges[i].from_port = dup_str(json_str(json_get(e, "from_port"), "out"));
            wf->edges[i].to_port = dup_str(json_str(json_get(e, "to_port"), "in"));
        }
    }
    return 1;
}

void workflow_free(workflow *wf) {
    for (int i = 0; i < wf->n_nodes; ++i) {
        free(wf->nodes[i].id);
        free(wf->nodes[i].type);
    }
    free(wf->nodes);
    for (int i = 0; i < wf->n_edges; ++i) {
        free(wf->edges[i].from);
        free(wf->edges[i].from_port);
        free(wf->edges[i].to);
        free(wf->edges[i].to_port);
    }
    free(wf->edges);
    free(wf->id);
    free(wf->name);
    json_free(wf->root);
    memset(wf, 0, sizeof(*wf));
}

/* ---------------------------------------------------------------- 查询 */

static int find_node(const workflow *wf, const char *id) {
    if (!id) {
        return -1;
    }
    for (int i = 0; i < wf->n_nodes; ++i) {
        if (wf->nodes[i].id && strcmp(wf->nodes[i].id, id) == 0) {
            return i;
        }
    }
    return -1;
}

static int port_exists(const node_contract *c, const char *port, int outputs) {
    if (!c || !port) {
        return 0;
    }
    int n = outputs ? c->n_outputs : c->n_inputs;
    const port_def *p = outputs ? c->outputs : c->inputs;
    for (int i = 0; i < n; ++i) {
        if (strcmp(p[i].id, port) == 0) {
            return 1;
        }
    }
    return 0;
}

static const wf_edge *edge_from(const workflow *wf, const char *node_id, const char *port) {
    for (int i = 0; i < wf->n_edges; ++i) {
        const wf_edge *e = &wf->edges[i];
        if (e->from && e->to && strcmp(e->from, node_id) == 0 && strcmp(e->from_port, port) == 0) {
            return e;
        }
    }
    return NULL;
}

/* ---------------------------------------------------------------- 校验 */

static int check_cycle(const workflow *wf, int index, int *state, strbuf *errors) {
    if (state[index] == 1) {
        err_add(errors, "存在环形连线，阶段 0 只支持无环流程");
        return 0;
    }
    if (state[index] == 2) {
        return 1;
    }
    state[index] = 1;
    const char *id = wf->nodes[index].id;
    for (int i = 0; i < wf->n_edges; ++i) {
        if (wf->edges[i].from && id && strcmp(wf->edges[i].from, id) == 0) {
            int next = find_node(wf, wf->edges[i].to);
            if (next >= 0 && !check_cycle(wf, next, state, errors)) {
                return 0;
            }
        }
    }
    state[index] = 2;
    return 1;
}

int workflow_validate(const workflow *wf, strbuf *errors) {
    int ok = 1;
    int start_count = 0;

    for (int i = 0; i < wf->n_nodes; ++i) {
        const wf_node *n = &wf->nodes[i];
        if (!n->id || !*n->id) {
            err_add(errors, "节点缺少 id");
            ok = 0;
            continue;
        }
        if (!n->type || !*n->type) {
            char msg[160];
            snprintf(msg, sizeof(msg), "节点 %s 缺少 type", n->id);
            err_add(errors, msg);
            ok = 0;
            continue;
        }
        const node_contract *c = node_find(n->type);
        if (!c) {
            char msg[200];
            snprintf(msg, sizeof(msg), "未知节点类型 %s", n->type);
            err_add(errors, msg);
            ok = 0;
            continue;
        }
        if (node_is_start(n->type)) {
            start_count++;
        }
        for (int j = 0; j < i; ++j) {
            if (wf->nodes[j].id && strcmp(wf->nodes[j].id, n->id) == 0) {
                char msg[200];
                snprintf(msg, sizeof(msg), "节点 id 重复：%s", n->id);
                err_add(errors, msg);
                ok = 0;
                break;
            }
        }
    }

    if (start_count == 0) {
        err_add(errors, "缺少 start 节点");
        ok = 0;
    }

    for (int i = 0; i < wf->n_edges; ++i) {
        const wf_edge *e = &wf->edges[i];
        char msg[240];
        int a = find_node(wf, e->from);
        int b = find_node(wf, e->to);
        if (a < 0) {
            snprintf(msg, sizeof(msg), "连线源节点不存在：%s", e->from ? e->from : "(null)");
            err_add(errors, msg);
            ok = 0;
            continue;
        }
        if (b < 0) {
            snprintf(msg, sizeof(msg), "连线目标节点不存在：%s", e->to ? e->to : "(null)");
            err_add(errors, msg);
            ok = 0;
            continue;
        }
        const node_contract *ca = node_find(wf->nodes[a].type);
        const node_contract *cb = node_find(wf->nodes[b].type);
        if (ca && !port_exists(ca, e->from_port, 1)) {
            snprintf(msg, sizeof(msg), "节点 %s 没有输出端口 %s", wf->nodes[a].id, e->from_port);
            err_add(errors, msg);
            ok = 0;
        }
        if (cb && cb->n_inputs > 0 && !port_exists(cb, e->to_port, 0)) {
            snprintf(msg, sizeof(msg), "节点 %s 没有输入端口 %s", wf->nodes[b].id, e->to_port);
            err_add(errors, msg);
            ok = 0;
        }
    }

    if (ok) {
        int *state = (int *)calloc((size_t)wf->n_nodes, sizeof(int));
        if (state) {
            for (int i = 0; i < wf->n_nodes && ok; ++i) {
                if (state[i] == 0) {
                    ok = check_cycle(wf, i, state, errors);
                }
            }
            free(state);
        }
    }
    return ok;
}

/* ---------------------------------------------------------------- 参数取值 */

static const param_def *param_def_find(const node_contract *c, const char *key) {
    for (int i = 0; i < c->n_params; ++i) {
        if (strcmp(c->params[i].key, key) == 0) {
            return &c->params[i];
        }
    }
    return NULL;
}

static double param_num(const node_contract *c, const wf_node *n, const char *key, double dflt) {
    jval *v = n->params ? json_get(n->params, key) : NULL;
    if (v) {
        if (v->t == JNUM) return v->n;
        if (v->t == JSTR) return strtod(v->s, NULL);
        if (v->t == JBOOL) return v->b ? 1 : 0;
    }
    const param_def *d = param_def_find(c, key);
    if (d && d->def) {
        if (d->def[0] == '"') return dflt;
        return strtod(d->def, NULL);
    }
    return dflt;
}

static const char *param_str(const node_contract *c, const wf_node *n, const char *key, const char *dflt) {
    jval *v = n->params ? json_get(n->params, key) : NULL;
    if (v && v->t == JSTR) {
        return v->s;
    }
    const param_def *d = param_def_find(c, key);
    if (d && d->def) {
        size_t len = strlen(d->def);
        if (len >= 2 && d->def[0] == '"' && d->def[len - 1] == '"') {
            static char buf[128];
            size_t copy = len - 2 < sizeof(buf) - 1 ? len - 2 : sizeof(buf) - 1;
            memcpy(buf, d->def + 1, copy);
            buf[copy] = '\0';
            return buf;
        }
    }
    return dflt;
}

/* ---------------------------------------------------------------- 执行 */

typedef struct {
    strbuf *events;
    int seq;
    unsigned long long started;
    int steps;
    capture_result frame;
    int has_frame;
} run_ctx;

/* 把模板名解析成绝对路径；支持绝对路径与 data/templates 下的名称 */
static int resolve_template(const char *name, char *out, size_t cap) {
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

static int run_capture(run_ctx *ctx) {
    capture_free(&ctx->frame);
    ctx->has_frame = 0;
    int ok = g_target ? capture_window(g_target, &ctx->frame) : capture_desktop(&ctx->frame);
    if (ok) {
        ctx->has_frame = 1;
    }
    return ok;
}

static int button_code(const char *name) {
    if (!name) return 0;
    if (_stricmp(name, "right") == 0) return 1;
    if (_stricmp(name, "middle") == 0) return 2;
    return 0;
}

static void event_begin(run_ctx *ctx, const wf_node *n, const char *type) {
    ctx->seq++;
    if (ctx->events->len) {
        sb_put(ctx->events, ",");
    }
    sb_put(ctx->events, "{\"seq\":");
    sb_putf(ctx->events, "%d", ctx->seq);
    sb_put(ctx->events, ",\"ts_ms\":");
    sb_putf(ctx->events, "%llu", (unsigned long long)(GetTickCount64() - ctx->started));
    sb_put(ctx->events, ",\"node_id\":");
    sb_json_str(ctx->events, n->id);
    sb_put(ctx->events, ",\"node\":");
    sb_json_str(ctx->events, type);
    sb_put(ctx->events, ",\"status\":\"ok\",\"port\":");
}

static void event_port(run_ctx *ctx, const char *port) {
    sb_json_str(ctx->events, port);
    sb_put(ctx->events, ",\"detail\":");
}

static void end_event(run_ctx *ctx) {
    sb_put(ctx->events, "}");
}

/* 前向声明 */
static int exec_from(const workflow *wf, int index, const char *stop_id, run_ctx *ctx, int depth);

static int follow(const workflow *wf, const char *node_id, const char *port, const char *stop_id, run_ctx *ctx, int depth) {
    const wf_edge *e = edge_from(wf, node_id, port);
    if (!e) {
        return 1;
    }
    if (stop_id && strcmp(e->to, stop_id) == 0) {
        return 1;
    }
    int next = find_node(wf, e->to);
    if (next < 0) {
        return 1;
    }
    return exec_from(wf, next, stop_id, ctx, depth + 1);
}

static int exec_from(const workflow *wf, int index, const char *stop_id, run_ctx *ctx, int depth) {
    if (depth > MAX_DEPTH || ctx->steps >= MAX_STEPS) {
        return 0;
    }
    const wf_node *n = &wf->nodes[index];
    const node_contract *c = node_find(n->type);
    if (!c) {
        return 0;
    }
    ctx->steps++;

    char detail[256];
    const char *port = "out";

    if (strcmp(c->id, "start") == 0) {
        event_begin(ctx, n, c->id);
        event_port(ctx, port);
        sb_put(ctx->events, "{\"mock\":true}");
        end_event(ctx);
    } else if (strcmp(c->id, "delay") == 0) {
        double ms = param_num(c, n, "ms", 100);
        Sleep((DWORD)(ms > 0 ? ms : 0));
        event_begin(ctx, n, c->id);
        event_port(ctx, port);
        sb_put(ctx->events, "{\"ms\":");
        sb_json_num(ctx->events, ms);
        sb_put(ctx->events, "}");
        end_event(ctx);
    } else if (strcmp(c->id, "click") == 0 || strcmp(c->id, "move") == 0) {
        double x = param_num(c, n, "x", 0);
        double y = param_num(c, n, "y", 0);
        const char *mode = param_str(c, n, "mode", "window");
        int window_mode = strcmp(mode, "screen") != 0 && g_target != NULL;
        int ok;
        if (strcmp(c->id, "click") == 0) {
            int button = button_code(param_str(c, n, "button", "left"));
            int clicks = (int)param_num(c, n, "clicks", 1);
            ok = input_click((int)x, (int)y, window_mode, g_target, button, clicks);
            double delay = param_num(c, n, "delay_ms", 80);
            if (delay > 0) {
                Sleep((DWORD)delay);
            }
        } else {
            ok = input_move((int)x, (int)y, window_mode, g_target,
                            (int)param_num(c, n, "duration_ms", 200));
        }
        event_begin(ctx, n, c->id);
        event_port(ctx, port);
        sb_put(ctx->events, "{\"x\":");
        sb_json_num(ctx->events, x);
        sb_put(ctx->events, ",\"y\":");
        sb_json_num(ctx->events, y);
        sb_put(ctx->events, ",\"mode\":");
        sb_json_str(ctx->events, window_mode ? "window" : "screen");
        sb_put(ctx->events, ",\"ok\":");
        sb_put(ctx->events, ok ? "true" : "false");
        sb_put(ctx->events, "}");
        end_event(ctx);
    } else if (strcmp(c->id, "input") == 0) {
        const char *keys = param_str(c, n, "keys", "");
        const char *text = param_str(c, n, "text", "");
        int ok;
        if (*text) {
            ok = input_text_any(text);
        } else {
            ok = input_key(keys);
        }
        event_begin(ctx, n, c->id);
        event_port(ctx, port);
        sb_put(ctx->events, "{\"keys\":");
        sb_json_str(ctx->events, keys);
        sb_put(ctx->events, ",\"text\":");
        sb_json_str(ctx->events, text);
        sb_put(ctx->events, ",\"ok\":");
        sb_put(ctx->events, ok ? "true" : "false");
        sb_put(ctx->events, "}");
        end_event(ctx);
    } else if (strcmp(c->id, "capture") == 0) {
        int ok = run_capture(ctx);
        event_begin(ctx, n, c->id);
        event_port(ctx, port);
        sb_put(ctx->events, "{\"ok\":");
        sb_put(ctx->events, ok ? "true" : "false");
        if (ok) {
            sb_put(ctx->events, ",\"method\":");
            sb_json_str(ctx->events, ctx->frame.method_name);
            sb_put(ctx->events, ",\"width\":");
            sb_putf(ctx->events, "%d", ctx->frame.width);
            sb_put(ctx->events, ",\"height\":");
            sb_putf(ctx->events, "%d", ctx->frame.height);
            sb_put(ctx->events, ",\"capture_ms\":");
            sb_json_num(ctx->events, ctx->frame.ms);
            sb_put(ctx->events, ",\"note\":");
            sb_json_str(ctx->events, ctx->frame.note);
        }
        sb_put(ctx->events, "}");
        end_event(ctx);
        if (!ok) {
            return 1;
        }
    } else if (strcmp(c->id, "match") == 0) {
        double threshold = param_num(c, n, "threshold", 0.5);
        const char *tpl = param_str(c, n, "template", "");
        char path[512];
        match_result mr;
        memset(&mr, 0, sizeof(mr));
        if (!ctx->has_frame) {
            run_capture(ctx);
        }
        int have = ctx->has_frame && resolve_template(tpl, path, sizeof(path));
        int ok = have ? match_file(path, ctx->frame.bgra, ctx->frame.width, ctx->frame.height,
                                   threshold, &mr) : 0;
        event_begin(ctx, n, c->id);
        event_port(ctx, port);
        sb_put(ctx->events, "{\"template\":");
        sb_json_str(ctx->events, tpl);
        sb_put(ctx->events, ",\"path\":");
        sb_json_str(ctx->events, have ? path : "");
        sb_put(ctx->events, ",\"ok\":");
        sb_put(ctx->events, ok ? "true" : "false");
        if (ok) {
            sb_put(ctx->events, ",\"score\":");
            sb_json_num(ctx->events, mr.score);
            sb_put(ctx->events, ",\"x\":");
            sb_putf(ctx->events, "%d", mr.x);
            sb_put(ctx->events, ",\"y\":");
            sb_putf(ctx->events, "%d", mr.y);
            sb_put(ctx->events, ",\"w\":");
            sb_putf(ctx->events, "%d", mr.w);
            sb_put(ctx->events, ",\"h\":");
            sb_putf(ctx->events, "%d", mr.h);
            sb_put(ctx->events, ",\"match_ms\":");
            sb_json_num(ctx->events, mr.ms);
            sb_put(ctx->events, ",\"levels\":");
            sb_putf(ctx->events, "%d", mr.levels);
        }
        sb_put(ctx->events, ",\"threshold\":");
        sb_json_num(ctx->events, threshold);
        sb_put(ctx->events, ",\"matched\":");
        sb_put(ctx->events, ok && mr.score >= threshold ? "true" : "false");
        sb_put(ctx->events, "}");
        end_event(ctx);
        if (!ok || mr.score < threshold) {
            return 1;
        }
    } else if (strcmp(c->id, "branch") == 0) {
        const char *op = param_str(c, n, "op", "eq");
        const char *left = param_str(c, n, "left", "");
        const char *right = param_str(c, n, "right", "");
        int result;
        if (strcmp(op, "ne") == 0) {
            result = strcmp(left, right) != 0;
        } else if (strcmp(op, "gt") == 0) {
            result = strtod(left, NULL) > strtod(right, NULL);
        } else if (strcmp(op, "lt") == 0) {
            result = strtod(left, NULL) < strtod(right, NULL);
        } else if (strcmp(op, "contains") == 0) {
            result = strstr(left, right) != NULL;
        } else {
            result = strcmp(left, right) == 0;
        }
        port = result ? "true" : "false";
        event_begin(ctx, n, c->id);
        event_port(ctx, port);
        sb_put(ctx->events, "{\"op\":");
        sb_json_str(ctx->events, op);
        sb_put(ctx->events, ",\"left\":");
        sb_json_str(ctx->events, left);
        sb_put(ctx->events, ",\"right\":");
        sb_json_str(ctx->events, right);
        sb_put(ctx->events, ",\"result\":");
        sb_put(ctx->events, result ? "true" : "false");
        sb_put(ctx->events, "}");
        end_event(ctx);
    } else if (strcmp(c->id, "loop") == 0) {
        double times = param_num(c, n, "times", 3);
        int count = times > 0 ? (int)times : 1;
        if (count > 1000) {
            count = 1000;
        }
        event_begin(ctx, n, c->id);
        event_port(ctx, "body");
        sb_put(ctx->events, "{\"times\":");
        sb_json_num(ctx->events, times);
        sb_put(ctx->events, "}");
        end_event(ctx);
        for (int i = 0; i < count; ++i) {
            if (!follow(wf, n->id, "body", n->id, ctx, depth)) {
                return 0;
            }
        }
        port = "done";
    } else if (strcmp(c->id, "subgraph") == 0) {
        const char *wfid = param_str(c, n, "workflow_id", "");
        event_begin(ctx, n, c->id);
        event_port(ctx, port);
        sb_put(ctx->events, "{\"workflow_id\":");
        sb_json_str(ctx->events, wfid);
        sb_put(ctx->events, ",\"status\":\"not_implemented\"}");
        end_event(ctx);
    } else {
        event_begin(ctx, n, c->id);
        event_port(ctx, port);
        sb_put(ctx->events, "{}");
        end_event(ctx);
    }

    (void)detail;
    return follow(wf, n->id, port, stop_id, ctx, depth);
}

int workflow_run(const workflow *wf, strbuf *result, strbuf *errors) {
    int start = -1;
    for (int i = 0; i < wf->n_nodes; ++i) {
        if (node_is_start(wf->nodes[i].type)) {
            start = i;
            break;
        }
    }
    if (start < 0) {
        err_add(errors, "缺少 start 节点");
        return 0;
    }

    run_ctx ctx;
    strbuf events;
    sb_init(&events);
    ctx.events = &events;
    ctx.seq = 0;
    ctx.steps = 0;
    ctx.started = GetTickCount64();
    memset(&ctx.frame, 0, sizeof(ctx.frame));
    ctx.has_frame = 0;

    exec_from(wf, start, NULL, &ctx, 0);

    sb_put(result, "{\"run_id\":\"run-");
    sb_putf(result, "%llu", (unsigned long long)GetTickCount64());
    sb_put(result, "\",\"workflow_id\":");
    sb_json_str(result, wf->id ? wf->id : "");
    sb_put(result, ",\"name\":");
    sb_json_str(result, wf->name ? wf->name : "");
    sb_put(result, ",\"status\":\"finished\",\"steps\":");
    sb_putf(result, "%d", ctx.steps);
    sb_put(result, ",\"duration_ms\":");
    sb_putf(result, "%llu", (unsigned long long)(GetTickCount64() - ctx.started));
    sb_put(result, ",\"evidence\":{\"events\":[");
    sb_put(result, events.data ? events.data : "");
    sb_put(result, "]}}");
    sb_free(&events);
    capture_free(&ctx.frame);
    return 1;
}
