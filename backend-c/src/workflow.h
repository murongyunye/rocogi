#ifndef ROCogi_WORKFLOW_H
#define ROCogi_WORKFLOW_H

#include "json.h"
#include "strbuf.h"

typedef struct {
    char *id;
    char *type;
    jval *params; /* 指向根 JSON 内部节点，不单独释放 */
} wf_node;

typedef struct {
    char *from;
    char *from_port;
    char *to;
    char *to_port;
} wf_edge;

typedef struct {
    jval *root; /* 持有整棵 JSON DOM */
    char *id;
    char *name;
    wf_node *nodes;
    int n_nodes;
    wf_edge *edges;
    int n_edges;
} workflow;

int workflow_parse(const char *text, size_t len, workflow *wf, strbuf *errors);
void workflow_free(workflow *wf);

/* 按节点契约校验，返回 1 通过 / 0 失败，错误写入 errors */
int workflow_validate(const workflow *wf, strbuf *errors);

/* 顺序执行，产出 Run Evidence JSON */
int workflow_run(const workflow *wf, strbuf *result, strbuf *errors);

/* 设置运行时上下文：data 目录（模板查找）与目标窗口（0/null=桌面） */
void workflow_set_runtime(const char *data_dir, void *target_hwnd);

#endif
