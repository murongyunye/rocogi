#include <math.h>
#include <stdio.h>

#include "../src/integrations/path_follow.h"

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

static void test_length(void) {
    path_point square[] = {{0, 0}, {10, 0}, {10, 10}, {0, 10}};
    CHECK_NEAR(path_length(square, 4), 30.0, 1e-9, "折线总长");
    CHECK_NEAR(path_length(square, 1), 0.0, 1e-9, "单点长度为 0");
    CHECK_NEAR(path_length(NULL, 4), 0.0, 1e-9, "空指针安全");
}

static void test_point_segment(void) {
    path_point a = {0, 0};
    path_point b = {10, 0};
    path_point inside = {5, 3};
    path_point outside = {-5, 0};
    double t = -1.0;

    CHECK_NEAR(path_point_segment_distance(inside, a, b, &t), 3.0, 1e-9, "线段内投影距离");
    CHECK_NEAR(t, 0.5, 1e-9, "投影参数");
    CHECK_NEAR(path_point_segment_distance(outside, a, b, &t), 5.0, 1e-9, "线段外距离");
    CHECK_NEAR(t, 0.0, 1e-9, "越界投影被夹紧");
}

static void test_progress(void) {
    path_point square[] = {{0, 0}, {10, 0}, {10, 10}, {0, 10}};
    path_point near_second = {10.2, 0.2};
    CHECK(path_progress(square, 4, near_second, 1.0, 0) == 1, "推进到第 2 个航点");

    path_point near_third = {9.9, 9.9};
    CHECK(path_progress(square, 4, near_third, 1.0, 1) == 2, "从下标 1 推进到 2");

    path_point far = {80.0, 80.0};
    CHECK(path_progress(square, 4, far, 1.0, 2) == 2, "未到达不推进");
    CHECK(path_progress(square, 4, far, 1.0, -3) == 0, "负下标归零");
    CHECK(path_progress(square, 4, far, 1.0, 9) == 3, "越界下标夹紧");
}

static void test_lookahead(void) {
    path_point square[] = {{0, 0}, {10, 0}, {10, 10}, {0, 10}};
    path_point out;

    CHECK(path_lookahead(square, 4, 0, 5.0, &out) == 1, "前视点成功");
    CHECK_NEAR(out.x, 5.0, 1e-9, "前视 x");
    CHECK_NEAR(out.y, 0.0, 1e-9, "前视 y");

    CHECK(path_lookahead(square, 4, 1, 5.0, &out) == 1, "跨段前视成功");
    CHECK_NEAR(out.x, 10.0, 1e-9, "跨段 x");
    CHECK_NEAR(out.y, 5.0, 1e-9, "跨段 y");

    CHECK(path_lookahead(square, 4, 0, 35.0, &out) == 1, "超出总长应夹到终点");
    CHECK_NEAR(out.x, 0.0, 1e-9, "终点 x");
    CHECK_NEAR(out.y, 10.0, 1e-9, "终点 y");

    CHECK(path_lookahead(square, 4, 0, 0.0, &out) == 1, "零前视返回当前点");
    CHECK_NEAR(out.x, 0.0, 1e-9, "零前视 x");
    CHECK(path_lookahead(NULL, 4, 0, 5.0, &out) == 0, "空指针失败");
}

static void test_heading(void) {
    CHECK_NEAR(path_heading_error(350.0, 10.0), 20.0, 1e-9, "跨 0 度正向");
    CHECK_NEAR(path_heading_error(10.0, 350.0), -20.0, 1e-9, "跨 0 度反向");
    CHECK_NEAR(path_heading_error(0.0, 180.0), 180.0, 1e-9, "正 180");
    CHECK_NEAR(path_heading_error(0.0, 181.0), -179.0, 1e-9, "超过 180 取最短");
    CHECK_NEAR(path_heading_error(0.0, -181.0), 179.0, 1e-9, "负向取最短");
}

int main(void) {
    test_length();
    test_point_segment();
    test_progress();
    test_lookahead();
    test_heading();
    if (failures == 0) {
        printf("path_follow: all tests passed\n");
        return 0;
    }
    printf("path_follow: %d failure(s)\n", failures);
    return 1;
}
