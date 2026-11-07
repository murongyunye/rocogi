#include <math.h>
#include <stdio.h>

#include "../src/integrations/human_move.h"

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

static void test_curves(void) {
    CHECK_NEAR(human_ease_curve(0.0, HUMAN_EASE_DECAY), 0.0, 1e-9, "decay 起点");
    CHECK_NEAR(human_ease_curve(0.5, HUMAN_EASE_DECAY), 0.823223, 1e-5, "decay 中点");
    CHECK_NEAR(human_ease_curve(1.0, HUMAN_EASE_DECAY), 1.0, 1e-9, "decay 终点");
    CHECK_NEAR(human_ease_curve(0.5, HUMAN_EASE_SMOOTH), 0.5, 1e-9, "smooth 中点");
    CHECK_NEAR(human_ease_curve(0.5, HUMAN_EASE_SINE), 0.5, 1e-9, "sine 中点");
    CHECK_NEAR(human_ease_curve(-1.0, HUMAN_EASE_SINE), 0.0, 1e-9, "越界起点");
    CHECK_NEAR(human_ease_curve(2.0, HUMAN_EASE_SINE), 1.0, 1e-9, "越界终点");
}

static void test_plan(void) {
    screen_point out[32];
    int n = human_move_plan(0, 0, 100, 0, 10, HUMAN_EASE_SMOOTH, 0.0, 127,
                            out, 32);
    CHECK(n == 10, "步数应为 10");
    CHECK(out[0].x >= 0 && out[0].x < 100, "首步应接近起点");
    CHECK(out[n - 1].x == 100 && out[n - 1].y == 0, "末点应到达目标");
    for (int i = 1; i < n; ++i) {
        CHECK(out[i].x >= out[i - 1].x, "位移应单调前进");
    }

    int m = human_move_plan(0, 0, 100, 0, 10, HUMAN_EASE_DECAY, 0.2, 127,
                            out, 32);
    CHECK(m >= 9, "过冲轨迹步数");
    CHECK(out[m - 1].x == 100, "过冲后应回到目标");
    int max_x = 0;
    for (int i = 0; i < m; ++i) {
        if (out[i].x > max_x) {
            max_x = out[i].x;
        }
    }
    CHECK(max_x > 100, "应出现过冲");

    int k = human_move_plan(0, 0, 1000, 0, 2, HUMAN_EASE_SMOOTH, 0.0, 127,
                            out, 32);
    CHECK(k == 2, "限幅场景步数");
    CHECK(out[0].x == 127 && out[1].x == 254, "单步限幅 127");

    int z = human_move_plan(5, 5, 5, 5, 10, HUMAN_EASE_SMOOTH, 0.0, 127,
                            out, 32);
    CHECK(z == 0, "原地移动不产生轨迹");

    CHECK(human_move_plan(0, 0, 100, 0, 10, HUMAN_EASE_SMOOTH, 0.0, 127,
                          NULL, 32) == -1, "空输出应失败");
}

int main(void) {
    test_curves();
    test_plan();
    if (failures == 0) {
        printf("human_move: all tests passed\n");
        return 0;
    }
    printf("human_move: %d failure(s)\n", failures);
    return 1;
}
