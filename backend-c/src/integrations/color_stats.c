#include "color_stats.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

static double min3(double a, double b, double c) {
    double m = a;
    if (b < m) m = b;
    if (c < m) m = c;
    return m;
}

static double max3(double a, double b, double c) {
    double m = a;
    if (b > m) m = b;
    if (c > m) m = c;
    return m;
}

void color_rgb_to_hsv(uint8_t r, uint8_t g, uint8_t b,
                      double *h, double *s, double *v) {
    double rr = (double)r / 255.0;
    double gg = (double)g / 255.0;
    double bb = (double)b / 255.0;
    double mx = max3(rr, gg, bb);
    double mn = min3(rr, gg, bb);
    double delta = mx - mn;
    double hue = 0.0;

    if (delta > 0.0) {
        if (mx == rr) {
            hue = 60.0 * fmod((gg - bb) / delta, 6.0);
        } else if (mx == gg) {
            hue = 60.0 * ((bb - rr) / delta + 2.0);
        } else {
            hue = 60.0 * ((rr - gg) / delta + 4.0);
        }
        if (hue < 0.0) {
            hue += 360.0;
        }
    }

    if (h) *h = hue;
    if (s) *s = mx > 0.0 ? delta / mx : 0.0;
    if (v) *v = mx;
}

double color_distance_rgb(uint8_t r1, uint8_t g1, uint8_t b1,
                          uint8_t r2, uint8_t g2, uint8_t b2) {
    double dr = (double)r1 - (double)r2;
    double dg = (double)g1 - (double)g2;
    double db = (double)b1 - (double)b2;
    return sqrt(dr * dr + dg * dg + db * db);
}

int color_hsv_within(double h, double s, double v, const hsv_range *range) {
    if (!range) {
        return 0;
    }
    if (s < range->s_min || s > range->s_max) {
        return 0;
    }
    if (v < range->v_min || v > range->v_max) {
        return 0;
    }
    if (range->h_min <= range->h_max) {
        return h >= range->h_min && h <= range->h_max;
    }
    return h >= range->h_min || h <= range->h_max;
}

static int clamp_roi(const color_roi *roi, int width, int height,
                     int *x0, int *y0, int *x1, int *y1) {
    int rx = 0;
    int ry = 0;
    int rw = width;
    int rh = height;
    if (roi) {
        rx = roi->x;
        ry = roi->y;
        rw = roi->w;
        rh = roi->h;
    }
    if (rx < 0) {
        rw += rx;
        rx = 0;
    }
    if (ry < 0) {
        rh += ry;
        ry = 0;
    }
    if (rx >= width || ry >= height || rw <= 0 || rh <= 0) {
        return 0;
    }
    if (rx + rw > width) {
        rw = width - rx;
    }
    if (ry + rh > height) {
        rh = height - ry;
    }
    *x0 = rx;
    *y0 = ry;
    *x1 = rx + rw;
    *y1 = ry + rh;
    return 1;
}

int color_range_ratio(const uint8_t *bgra, int width, int height, int stride,
                      const color_roi *roi, const hsv_range *range,
                      double *out_ratio) {
    if (!bgra || !range || !out_ratio || width <= 0 || height <= 0) {
        return 0;
    }
    if (stride < width * 4) {
        return 0;
    }
    int x0 = 0, y0 = 0, x1 = 0, y1 = 0;
    if (!clamp_roi(roi, width, height, &x0, &y0, &x1, &y1)) {
        return 0;
    }

    long long total = 0;
    long long hit = 0;
    for (int y = y0; y < y1; ++y) {
        const uint8_t *row = bgra + (size_t)y * (size_t)stride;
        for (int x = x0; x < x1; ++x) {
            const uint8_t *px = row + (size_t)x * 4;
            double h, s, v;
            color_rgb_to_hsv(px[2], px[1], px[0], &h, &s, &v);
            if (color_hsv_within(h, s, v, range)) {
                hit++;
            }
            total++;
        }
    }
    if (total == 0) {
        return 0;
    }
    *out_ratio = (double)hit / (double)total;
    return 1;
}

int color_dominant(const uint8_t *bgra, int width, int height, int stride,
                   const color_roi *roi, uint32_t *out_rgb) {
    if (!bgra || !out_rgb || width <= 0 || height <= 0) {
        return 0;
    }
    if (stride < width * 4) {
        return 0;
    }
    int x0 = 0, y0 = 0, x1 = 0, y1 = 0;
    if (!clamp_roi(roi, width, height, &x0, &y0, &x1, &y1)) {
        return 0;
    }

    enum { BINS = 32 * 32 * 32 };
    int *hist = (int *)calloc(BINS, sizeof(int));
    if (!hist) {
        return 0;
    }

    int best_bin = 0;
    for (int y = y0; y < y1; ++y) {
        const uint8_t *row = bgra + (size_t)y * (size_t)stride;
        for (int x = x0; x < x1; ++x) {
            const uint8_t *px = row + (size_t)x * 4;
            int rb = px[2] >> 3;
            int gb = px[1] >> 3;
            int bb = px[0] >> 3;
            int bin = (rb << 10) | (gb << 5) | bb;
            hist[bin]++;
            if (hist[bin] > hist[best_bin]) {
                best_bin = bin;
            }
        }
    }

    int rb = (best_bin >> 10) & 31;
    int gb = (best_bin >> 5) & 31;
    int bb = best_bin & 31;
    uint32_t r = (uint32_t)(rb * 8 + 4);
    uint32_t g = (uint32_t)(gb * 8 + 4);
    uint32_t b = (uint32_t)(bb * 8 + 4);
    *out_rgb = (r << 16) | (g << 8) | b;
    free(hist);
    return 1;
}
