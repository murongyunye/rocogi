#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../src/integrations/color_stats.h"

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

static void test_hsv(void) {
    double h = 0, s = 0, v = 0;
    color_rgb_to_hsv(255, 0, 0, &h, &s, &v);
    CHECK_NEAR(h, 0.0, 1e-9, "红 h");
    CHECK_NEAR(s, 1.0, 1e-9, "红 s");
    CHECK_NEAR(v, 1.0, 1e-9, "红 v");

    color_rgb_to_hsv(0, 255, 0, &h, &s, &v);
    CHECK_NEAR(h, 120.0, 1e-9, "绿 h");
    color_rgb_to_hsv(0, 0, 255, &h, &s, &v);
    CHECK_NEAR(h, 240.0, 1e-9, "蓝 h");
    color_rgb_to_hsv(255, 255, 0, &h, &s, &v);
    CHECK_NEAR(h, 60.0, 1e-9, "黄 h");
    color_rgb_to_hsv(0, 255, 255, &h, &s, &v);
    CHECK_NEAR(h, 180.0, 1e-9, "青 h");

    color_rgb_to_hsv(128, 128, 128, &h, &s, &v);
    CHECK_NEAR(s, 0.0, 1e-9, "灰 s");
    CHECK_NEAR(v, 128.0 / 255.0, 1e-9, "灰 v");
}

static void test_range(void) {
    hsv_range wrap = {350.0, 10.0, 0.5, 1.0, 0.5, 1.0};
    CHECK(color_hsv_within(355.0, 0.8, 0.9, &wrap), "环绕范围应命中 355");
    CHECK(color_hsv_within(5.0, 0.8, 0.9, &wrap), "环绕范围应命中 5");
    CHECK(!color_hsv_within(180.0, 0.8, 0.9, &wrap), "环绕范围外不命中");
    CHECK(!color_hsv_within(5.0, 0.2, 0.9, &wrap), "饱和度不足不命中");

    hsv_range plain = {100.0, 140.0, 0.0, 1.0, 0.0, 1.0};
    CHECK(color_hsv_within(120.0, 0.5, 0.5, &plain), "普通范围命中");
    CHECK(!color_hsv_within(90.0, 0.5, 0.5, &plain), "普通范围外不命中");
}

static uint8_t *make_image(int w, int h, int left_red_px) {
    uint8_t *buf = (uint8_t *)calloc((size_t)w * (size_t)h, 4);
    if (!buf) {
        return NULL;
    }
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            uint8_t *px = buf + ((size_t)y * (size_t)w + (size_t)x) * 4;
            if (x < left_red_px) {
                px[0] = 0;      /* B */
                px[1] = 0;      /* G */
                px[2] = 255;    /* R */
            } else {
                px[0] = 255;
                px[1] = 0;
                px[2] = 0;
            }
            px[3] = 255;
        }
    }
    return buf;
}

static void test_ratio(void) {
    const int w = 8, h = 8;
    uint8_t *img = make_image(w, h, 4);
    CHECK(img != NULL, "测试图像分配");
    if (!img) {
        return;
    }
    hsv_range red = {350.0, 10.0, 0.5, 1.0, 0.5, 1.0};
    double ratio = -1.0;
    CHECK(color_range_ratio(img, w, h, w * 4, NULL, &red, &ratio) == 1, "比例统计应成功");
    CHECK_NEAR(ratio, 0.5, 1e-9, "红色占比应为 0.5");

    color_roi roi = {4, 0, 4, 8};
    CHECK(color_range_ratio(img, w, h, w * 4, &roi, &red, &ratio) == 1, "ROI 统计应成功");
    CHECK_NEAR(ratio, 0.0, 1e-9, "ROI 内无红色");

    color_roi outside = {20, 20, 4, 4};
    CHECK(color_range_ratio(img, w, h, w * 4, &outside, &red, &ratio) == 0, "越界 ROI 应失败");

    uint32_t rgb = 0;
    free(img);
    uint8_t *majority = make_image(w, h, 6);
    CHECK(majority != NULL, "主色测试图像分配");
    if (majority) {
        CHECK(color_dominant(majority, w, h, w * 4, NULL, &rgb) == 1, "主色统计应成功");
        CHECK(((rgb >> 16) & 0xFF) >= 248, "主色应为红");
        CHECK((rgb & 0xFF) <= 8, "主色蓝分量应接近 0");
        free(majority);
    }
}

int main(void) {
    test_hsv();
    test_range();
    test_ratio();
    if (failures == 0) {
        printf("color_stats: all tests passed\n");
        return 0;
    }
    printf("color_stats: %d failure(s)\n", failures);
    return 1;
}
