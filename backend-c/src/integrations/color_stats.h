#ifndef ROCogi_COLOR_STATS_H
#define ROCogi_COLOR_STATS_H

#include <stdint.h>

/* BGRA 像素（与 DXGI 截图一致）颜色统计与 HSV 阈值判断。
 * 对应上游 RocoPilot core/vision.py 的灰度/阈值预处理与 AutoCapture 的颜色筛选。 */

typedef struct {
    double h_min; /* 0..360，h_min > h_max 表示跨 0 度环绕 */
    double h_max;
    double s_min; /* 0..1 */
    double s_max;
    double v_min;
    double v_max;
} hsv_range;

typedef struct {
    int x;
    int y;
    int w;
    int h;
} color_roi;

void color_rgb_to_hsv(uint8_t r, uint8_t g, uint8_t b,
                      double *h, double *s, double *v);

double color_distance_rgb(uint8_t r1, uint8_t g1, uint8_t b1,
                          uint8_t r2, uint8_t g2, uint8_t b2);

int color_hsv_within(double h, double s, double v, const hsv_range *range);

/* 统计 ROI 内落在 HSV 范围的像素比例；roi 传 NULL 表示整帧。成功返回 1。 */
int color_range_ratio(const uint8_t *bgra, int width, int height, int stride,
                      const color_roi *roi, const hsv_range *range,
                      double *out_ratio);

/* 主色：按 5 bit/通道量化后取直方图峰值，输出 0x00RRGGBB。 */
int color_dominant(const uint8_t *bgra, int width, int height, int stride,
                   const color_roi *roi, uint32_t *out_rgb);

#endif
