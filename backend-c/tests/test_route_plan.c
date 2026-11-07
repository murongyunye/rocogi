#include <math.h>
#include <stdio.h>
#include <string.h>

#include "../src/integrations/route_plan.h"

static int failures = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        if (!(cond)) {                                          \
            printf("FAIL: %s (line %d)\n", msg, __LINE__);       \
            failures++;                                         \
        }                                                       \
    } while (0)

#define CHECK_NEAR(a, b, eps, msg)                              \
    do {                                                        \
        double _a = (a);                                        \
        double _b = (b);                                        \
        if (fabs(_a - _b) > (eps)) {                            \
            printf("FAIL: %s (line %d): %.4f != %.4f\n",         \
                   msg, __LINE__, _a, _b);                      \
            failures++;                                         \
        }                                                       \
    } while (0)

static const char *SAMPLE_JSON =
    "[{\"id\":\"a\",\"label\":\"采集\",\"category\":\"植物\",\"x\":10,\"y\":0},"
    " {\"id\":\"b\",\"label\":\"采集\",\"category\":\"植物\",\"x\":30,\"y\":0},"
    " {\"id\":\"c\",\"label\":\"采集\",\"category\":\"矿物\",\"x\":0,\"y\":10},"
    " {\"id\":\"d\",\"label\":\"传送\",\"category\":\"点位\",\"x\":100,\"y\":100},"
    " {\"id\":\"e\",\"label\":\"采集\",\"category\":\"植物\",\"x\":5,\"y\":5}]";

static void test_load(void) {
    int count = 0;
    poi_point *points = poi_load_json(SAMPLE_JSON, strlen(SAMPLE_JSON), &count);
    CHECK(points != NULL, "JSON 应能解析");
    CHECK(count == 5, "应解析出 5 个点位");
    if (points && count == 5) {
        CHECK(strcmp(points[0].id, "a") == 0, "id 应保留");
        CHECK(strcmp(points[0].label, "采集") == 0, "label 应保留");
        CHECK_NEAR(points[4].x, 5.0, 1e-9, "x 应保留");
    }
    poi_free(points, count);
}

static void test_defaults(void) {
    const char *json = "[{\"x\":1,\"y\":2}]";
    int count = 0;
    poi_point *points = poi_load_json(json, strlen(json), &count);
    CHECK(points != NULL, "缺省字段应回退");
    if (points && count == 1) {
        CHECK(strcmp(points[0].label, "未分类") == 0, "label 缺省");
        CHECK(strcmp(points[0].category, "其他") == 0, "category 缺省");
        CHECK(strncmp(points[0].id, "p", 1) == 0, "id 缺省生成");
    }
    poi_free(points, count);
}

static void test_route(void) {
    int count = 0;
    poi_point *points = poi_load_json(SAMPLE_JSON, strlen(SAMPLE_JSON), &count);
    CHECK(points != NULL && count == 5, "测试数据应可用");
    if (!points || count != 5) {
        poi_free(points, count);
        return;
    }

    route_opts opts;
    memset(&opts, 0, sizeof(opts));
    opts.limit = 3;
    route_result result;
    CHECK(route_plan(points, count, &opts, &result) == 1, "路线规划应成功");
    CHECK(result.count == 3, "limit 应生效");
    CHECK(result.has_return == 0, "无回程时 has_return=0");
    if (result.count == 3) {
        CHECK(result.indices[0] == 4, "最近点应为 e");
        CHECK(result.indices[1] == 0, "次近点应为 a");
        CHECK(result.indices[2] == 2, "第三点应为 c");
    }
    CHECK_NEAR(result.distance, 28.2842712, 1e-4, "总距离");
    route_result_free(&result);

    opts.limit = 3;
    opts.roundtrip = 1;
    CHECK(route_plan(points, count, &opts, &result) == 1, "回程规划应成功");
    CHECK(result.has_return == 1, "回程标记");
    CHECK_NEAR(result.distance, 38.2842712, 1e-4, "含回程总距离");
    route_result_free(&result);

    const char *labels[] = {"采集"};
    opts.labels = labels;
    opts.label_count = 1;
    opts.roundtrip = 0;
    CHECK(route_plan(points, count, &opts, &result) == 1, "标签过滤应成功");
    CHECK(result.count == 3, "标签过滤后 limit 不变");
    route_result_free(&result);

    const char *categories[] = {"矿物"};
    opts.labels = NULL;
    opts.label_count = 0;
    opts.categories = categories;
    opts.category_count = 1;
    opts.limit = 20;
    CHECK(route_plan(points, count, &opts, &result) == 1, "分类过滤应成功");
    CHECK(result.count == 1 && result.indices[0] == 2, "只保留矿物点");
    CHECK_NEAR(result.distance, 10.0, 1e-9, "单点距离");
    route_result_free(&result);

    poi_free(points, count);
}

static void test_limit_clamp(void) {
    route_opts opts;
    memset(&opts, 0, sizeof(opts));
    opts.limit = 0; /* 上游实现：max(1, min(limit, 200)) */
    route_opts clamped = opts;
    clamped.limit = 1;
    route_result a, b;
    poi_point single = {0};
    single.x = 3.0;
    single.y = 4.0;
    CHECK(route_plan(&single, 1, &opts, &a) == 1, "limit=0 应被夹到 1");
    CHECK(route_plan(&single, 1, &clamped, &b) == 1, "limit=1 基线");
    CHECK(a.count == b.count && a.count == 1, "两种 limit 结果一致");
    CHECK_NEAR(a.distance, 5.0, 1e-9, "单点距离应为 5");
    route_result_free(&a);
    route_result_free(&b);
}

int main(void) {
    test_load();
    test_defaults();
    test_route();
    test_limit_clamp();
    if (failures == 0) {
        printf("route_plan: all tests passed\n");
        return 0;
    }
    printf("route_plan: %d failure(s)\n", failures);
    return 1;
}
