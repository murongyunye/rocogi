#ifndef ROCogi_ROUTE_PLAN_H
#define ROCogi_ROUTE_PLAN_H

#include <stddef.h>

/* 地图 POI 点：字段模型对齐 backend/app/adapters/mapdata.py
 * （id / title / label / category / x / y），数据来自 roco-map-tracker 与 luoke_location 导出的点位 JSON。 */
typedef struct {
    char *id;
    char *title;
    char *label;
    char *category;
    double x;
    double y;
} poi_point;

typedef struct {
    double start_x;
    double start_y;
    const char *const *labels;      /* NULL 表示不过滤 */
    int label_count;
    const char *const *categories;  /* NULL 表示不过滤 */
    int category_count;
    int limit;                      /* 1..200，与上游一致：小于 1 按 1 处理 */
    int roundtrip;                  /* 非 0 时把返回起点的距离计入 */
} route_opts;

typedef struct {
    int *indices;   /* points 数组下标，按访问顺序 */
    int count;      /* 访问的点数，不含返回起点 */
    double distance;
    int has_return; /* 是否按 roundtrip 追加返回起点 */
} route_result;

/* 解析点位 JSON 数组（对象字段：id/title/label/category/x/y）。成功返回点位数组，失败返回 NULL。 */
poi_point *poi_load_json(const char *text, size_t len, int *out_count);
void poi_free(poi_point *points, int count);

/* 最近邻排序（等价于 mapdata.py 的 plan_route）：按标签/分类过滤，逐点取最近，可选回程。 */
int route_plan(const poi_point *points, int point_count,
               const route_opts *opts, route_result *out);

void route_result_free(route_result *result);

#endif
