#include "nodes.h"

#include <string.h>

/* ---------------------------------------------------------------- 端口定义 */

static const port_def P_EXEC_IN[] = {{"in", "exec", "输入"}};
static const port_def P_EXEC_OUT[] = {{"out", "exec", "输出"}};
static const port_def P_NO_PORT[] = {{0, 0, 0}};

static const port_def P_START_OUT[] = {{"out", "exec", "输出"}};
static const port_def P_BRANCH_OUT[] = {
    {"true", "exec", "条件成立"},
    {"false", "exec", "条件不成立"},
};
static const port_def P_BRANCH_IN[] = {
    {"in", "exec", "输入"},
    {"value", "data", "比较值"},
};
static const port_def P_LOOP_OUT[] = {
    {"body", "exec", "循环体"},
    {"done", "exec", "循环结束"},
};
static const port_def P_CAPTURE_OUT[] = {
    {"out", "exec", "输出"},
    {"image", "data", "截图"},
};
static const port_def P_MATCH_IN[] = {
    {"in", "exec", "输入"},
    {"image", "data", "截图"},
};
static const port_def P_MATCH_OUT[] = {
    {"out", "exec", "输出"},
    {"matched", "data", "是否命中"},
    {"score", "data", "相似度"},
};

/* ---------------------------------------------------------------- 参数定义 */

static const param_def PA_NONE[] = {{0, 0, 0, 0, 0, 0, 0}};

static const param_def PA_BRANCH[] = {
    {"op", "enum", "比较运算", "\"eq\"", 0, 0, 0},
    {"left", "string", "左值", "\"\"", 0, 0, 0},
    {"right", "string", "右值", "\"\"", 0, 0, 0},
};
static const param_def PA_LOOP[] = {
    {"times", "number", "循环次数", "3", 0, 1, 10000},
    {"interval_ms", "number", "间隔毫秒", "0", 0, 0, 600000},
};
static const param_def PA_CLICK[] = {
    {"x", "number", "X 坐标", "0", 1, 0, 100000},
    {"y", "number", "Y 坐标", "0", 1, 0, 100000},
    {"button", "enum", "按键", "\"left\"", 0, 0, 0},
    {"clicks", "number", "点击次数", "1", 0, 1, 10},
    {"delay_ms", "number", "点击后延迟", "80", 0, 0, 60000},
    {"mode", "enum", "坐标系", "\"window\"", 0, 0, 0},
};
static const param_def PA_KEY[] = {
    {"keys", "string", "按键组合", "\"\"", 1, 0, 0},
    {"text", "string", "文本内容", "\"\"", 0, 0, 0},
    {"action", "enum", "动作", "\"tap\"", 0, 0, 0},
    {"duration_ms", "number", "按住时长", "100", 0, 0, 60000},
};
static const param_def PA_CAPTURE[] = {
    {"region", "string", "截图区域", "\"full\"", 0, 0, 0},
    {"scale", "number", "缩放", "1", 0, 0.1, 4},
    {"format", "enum", "格式", "\"png\"", 0, 0, 0},
};
static const param_def PA_MATCH[] = {
    {"template", "string", "模板名称", "\"\"", 1, 0, 0},
    {"threshold", "number", "阈值", "0.5", 0, 0, 1},
    {"timeout_ms", "number", "超时", "2000", 0, 0, 600000},
};
static const param_def PA_MOVE[] = {
    {"x", "number", "X 坐标", "0", 1, 0, 100000},
    {"y", "number", "Y 坐标", "0", 1, 0, 100000},
    {"duration_ms", "number", "移动时长", "200", 0, 0, 60000},
    {"curve", "enum", "轨迹", "\"linear\"", 0, 0, 0},
    {"mode", "enum", "坐标系", "\"window\"", 0, 0, 0},
};
static const param_def PA_DELAY[] = {
    {"ms", "number", "延迟毫秒", "100", 0, 0, 600000},
};
static const param_def PA_SUBGRAPH[] = {
    {"workflow_id", "string", "子流程 ID", "\"\"", 1, 0, 0},
    {"mode", "enum", "执行模式", "\"sync\"", 0, 0, 0},
};

/* ---------------------------------------------------------------- 契约表 */

static const node_contract CONTRACTS[] = {
    {"start", "flow", "开始", "工作流的执行入口，触发一条执行连线。",
     P_NO_PORT, 0, P_START_OUT, 1, PA_NONE, 0},
    {"branch", "flow", "条件分支", "按 op/left/right 判定真假，选择 true 或 false 分支。",
     P_BRANCH_IN, 2, P_BRANCH_OUT, 2, PA_BRANCH, 3},
    {"loop", "flow", "循环", "按 times 重复执行循环体连线，完成后走 done。",
     P_EXEC_IN, 1, P_LOOP_OUT, 2, PA_LOOP, 2},
    {"click", "input", "鼠标点击", "在目标窗口坐标点击，输出执行连线。",
     P_EXEC_IN, 1, P_EXEC_OUT, 1, PA_CLICK, 6},
    {"input", "input", "键盘输入", "发送按键或组合键。",
     P_EXEC_IN, 1, P_EXEC_OUT, 1, PA_KEY, 4},
    {"capture", "vision", "截图", "抓取目标窗口画面，输出截图数据。",
     P_EXEC_IN, 1, P_CAPTURE_OUT, 2, PA_CAPTURE, 3},
    {"match", "vision", "模板匹配", "在截图中匹配视觉模板，输出命中与相似度。",
     P_MATCH_IN, 2, P_MATCH_OUT, 3, PA_MATCH, 3},
    {"move", "input", "鼠标移动", "把指针移动到目标坐标。",
     P_EXEC_IN, 1, P_EXEC_OUT, 1, PA_MOVE, 5},
    {"delay", "flow", "延迟", "等待指定毫秒后继续。",
     P_EXEC_IN, 1, P_EXEC_OUT, 1, PA_DELAY, 1},
    {"subgraph", "flow", "子流程", "调用另一个工作流作为子图。",
     P_EXEC_IN, 1, P_EXEC_OUT, 1, PA_SUBGRAPH, 2},
};

static const int CONTRACT_COUNT = (int)(sizeof(CONTRACTS) / sizeof(CONTRACTS[0]));

int node_count(void) {
    return CONTRACT_COUNT;
}

const node_contract *node_at(int index) {
    if (index < 0 || index >= CONTRACT_COUNT) {
        return NULL;
    }
    return &CONTRACTS[index];
}

const node_contract *node_find(const char *id) {
    if (!id) {
        return NULL;
    }
    for (int i = 0; i < CONTRACT_COUNT; ++i) {
        if (strcmp(CONTRACTS[i].id, id) == 0) {
            return &CONTRACTS[i];
        }
        /* 兼容 Python 版与 yotta 的命名空间写法 */
        const char *dot = strrchr(id, '.');
        if (dot && strcmp(CONTRACTS[i].id, dot + 1) == 0) {
            return &CONTRACTS[i];
        }
    }
    return NULL;
}

int node_is_start(const char *id) {
    const node_contract *c = node_find(id);
    return c && strcmp(c->id, "start") == 0;
}

/* ---------------------------------------------------------------- 序列化 */

static void ports_json(strbuf *sb, const port_def *ports, int n) {
    sb_put(sb, "[");
    for (int i = 0; i < n; ++i) {
        if (i) sb_put(sb, ",");
        sb_put(sb, "{\"id\":");
        sb_json_str(sb, ports[i].id);
        sb_put(sb, ",\"kind\":");
        sb_json_str(sb, ports[i].kind);
        sb_put(sb, ",\"label\":");
        sb_json_str(sb, ports[i].label);
        sb_put(sb, "}");
    }
    sb_put(sb, "]");
}

static void params_json(strbuf *sb, const param_def *params, int n) {
    sb_put(sb, "[");
    for (int i = 0; i < n; ++i) {
        if (i) sb_put(sb, ",");
        sb_put(sb, "{\"key\":");
        sb_json_str(sb, params[i].key);
        sb_put(sb, ",\"type\":");
        sb_json_str(sb, params[i].type);
        sb_put(sb, ",\"label\":");
        sb_json_str(sb, params[i].label);
        sb_put(sb, ",\"default\":");
        sb_put(sb, params[i].def ? params[i].def : "null");
        sb_put(sb, ",\"required\":");
        sb_put(sb, params[i].required ? "true" : "false");
        if (params[i].maximum > 0) {
            sb_put(sb, ",\"minimum\":");
            sb_json_num(sb, params[i].minimum);
            sb_put(sb, ",\"maximum\":");
            sb_json_num(sb, params[i].maximum);
        }
        sb_put(sb, "}");
    }
    sb_put(sb, "]");
}

void nodes_json(strbuf *sb) {
    sb_put(sb, "{\"nodes\":[");
    for (int i = 0; i < CONTRACT_COUNT; ++i) {
        const node_contract *c = &CONTRACTS[i];
        if (i) sb_put(sb, ",");
        sb_put(sb, "{\"id\":");
        sb_json_str(sb, c->id);
        sb_put(sb, ",\"kind\":");
        sb_json_str(sb, c->kind);
        sb_put(sb, ",\"title\":");
        sb_json_str(sb, c->title);
        sb_put(sb, ",\"description\":");
        sb_json_str(sb, c->description);
        sb_put(sb, ",\"inputs\":");
        ports_json(sb, c->inputs, c->n_inputs);
        sb_put(sb, ",\"outputs\":");
        ports_json(sb, c->outputs, c->n_outputs);
        sb_put(sb, ",\"params\":");
        params_json(sb, c->params, c->n_params);
        sb_put(sb, "}");
    }
    sb_put(sb, "],\"count\":");
    sb_putf(sb, "%d", CONTRACT_COUNT);
    sb_put(sb, "}");
}
