#ifndef ROCogi_NODES_H
#define ROCogi_NODES_H

#include "strbuf.h"

typedef struct {
    const char *id;
    const char *kind;   /* exec / data */
    const char *label;
} port_def;

typedef struct {
    const char *key;
    const char *type;   /* number / string / boolean / enum */
    const char *label;
    const char *def;    /* 默认值的 JSON 字面量 */
    int required;
    double minimum;
    double maximum;
} param_def;

typedef struct {
    const char *id;
    const char *kind;   /* flow / input / vision */
    const char *title;
    const char *description;
    const port_def *inputs;
    int n_inputs;
    const port_def *outputs;
    int n_outputs;
    const param_def *params;
    int n_params;
} node_contract;

const node_contract *node_find(const char *id);
int node_count(void);
const node_contract *node_at(int index);
/* 判断类型名是否为开始节点 */
int node_is_start(const char *id);

void nodes_json(strbuf *sb);

#endif
