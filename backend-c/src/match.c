#include "match.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

#include "pngio.h"

#define MAX_LEVEL 3          /* 0=原图 1=1/2 2=1/4 */
#define TOP_K 8              /* 每层保留的候选数 */
#define REFINE_RADIUS 3      /* 逐层精修半径 */

typedef struct {
    unsigned char *p;
    int w;
    int h;
} glev;

static double now_ms(void) {
    LARGE_INTEGER freq, counter;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&counter);
    return (double)counter.QuadPart * 1000.0 / (double)freq.QuadPart;
}

static void levels_free(glev *lv, int n) {
    for (int i = 0; i < n; ++i) {
        free(lv[i].p);
        lv[i].p = NULL;
    }
}

/* BGRA -> 灰度 */
static unsigned char *bgra_to_gray(const unsigned char *src, int w, int h) {
    if (!src || w <= 0 || h <= 0) {
        return NULL;
    }
    unsigned char *g = (unsigned char *)malloc((size_t)w * (size_t)h);
    if (!g) {
        return NULL;
    }
    size_t n = (size_t)w * (size_t)h;
    for (size_t i = 0; i < n; ++i) {
        const unsigned char *p = src + i * 4;
        g[i] = (unsigned char)((p[2] * 299 + p[1] * 587 + p[0] * 114) / 1000);
    }
    return g;
}

/* 2x2 均值降采样 */
static int down2(const unsigned char *src, int sw, int sh, glev *out) {
    int w = sw / 2;
    int h = sh / 2;
    if (w < 1 || h < 1) {
        return 0;
    }
    unsigned char *dst = (unsigned char *)malloc((size_t)w * (size_t)h);
    if (!dst) {
        return 0;
    }
    for (int y = 0; y < h; ++y) {
        const unsigned char *r0 = src + (size_t)(y * 2) * sw;
        const unsigned char *r1 = r0 + sw;
        unsigned char *d = dst + (size_t)y * w;
        for (int x = 0; x < w; ++x) {
            int v = (int)r0[x * 2] + r0[x * 2 + 1] + r1[x * 2] + r1[x * 2 + 1];
            d[x] = (unsigned char)(v / 4);
        }
    }
    out->p = dst;
    out->w = w;
    out->h = h;
    return 1;
}

static void integral_build(const glev *g, long long *S, long long *S2) {
    int W = g->w + 1;
    for (int x = 0; x <= g->w; ++x) {
        S[x] = 0;
        S2[x] = 0;
    }
    for (int y = 0; y < g->h; ++y) {
        S[(size_t)(y + 1) * W] = 0;
        S2[(size_t)(y + 1) * W] = 0;
        const unsigned char *row = g->p + (size_t)y * g->w;
        for (int x = 0; x < g->w; ++x) {
            long long v = row[x];
            size_t i = (size_t)(y + 1) * W + (x + 1);
            S[i] = v + S[(size_t)y * W + (x + 1)]
                     + S[(size_t)(y + 1) * W + x]
                     - S[(size_t)y * W + x];
            S2[i] = v * v + S2[(size_t)y * W + (x + 1)]
                     + S2[(size_t)(y + 1) * W + x]
                     - S2[(size_t)y * W + x];
        }
    }
}

static long long rect_sum(const long long *S, int W, int x, int y, int w, int h) {
    return S[(size_t)(y + h) * W + (x + w)] - S[(size_t)y * W + (x + w)]
         - S[(size_t)(y + h) * W + x] + S[(size_t)y * W + x];
}

/* 用积分图求窗口均值/方差，直接循环求互相关 */
static double ncc_integral(const glev *g, const long long *S, const long long *S2,
                           const unsigned char *t, int tw, int th, int ox, int oy,
                           double tsum, double tsum2) {
    int W = g->w + 1;
    double n = (double)tw * (double)th;
    double si = (double)rect_sum(S, W, ox, oy, tw, th);
    double sii = (double)rect_sum(S2, W, ox, oy, tw, th);
    double sit = 0.0;
    for (int y = 0; y < th; ++y) {
        const unsigned char *ir = g->p + (size_t)(oy + y) * g->w + ox;
        const unsigned char *tr = t + (size_t)y * tw;
        double row = 0.0;
        for (int x = 0; x < tw; ++x) {
            row += (double)ir[x] * (double)tr[x];
        }
        sit += row;
    }
    double num = n * sit - si * tsum;
    double d1 = n * sii - si * si;
    double d2 = n * tsum2 - tsum * tsum;
    if (d1 <= 1e-9 || d2 <= 1e-9) {
        return 0.0;
    }
    return num / sqrt(d1 * d2);
}

/* 原图直接计算窗口 NCC */
static double ncc_direct(const glev *g, const unsigned char *t, int tw, int th,
                         int ox, int oy, double tsum, double tsum2) {
    double n = (double)tw * (double)th;
    double si = 0.0, sii = 0.0, sit = 0.0;
    for (int y = 0; y < th; ++y) {
        const unsigned char *ir = g->p + (size_t)(oy + y) * g->w + ox;
        const unsigned char *tr = t + (size_t)y * tw;
        for (int x = 0; x < tw; ++x) {
            double iv = (double)ir[x];
            double tv = (double)tr[x];
            si += iv;
            sii += iv * iv;
            sit += iv * tv;
        }
    }
    double num = n * sit - si * tsum;
    double d1 = n * sii - si * si;
    double d2 = n * tsum2 - tsum * tsum;
    if (d1 <= 1e-9 || d2 <= 1e-9) {
        return 0.0;
    }
    return num / sqrt(d1 * d2);
}

typedef struct {
    int x;
    int y;
    double score;
} cand;

static void cand_push(cand *list, int *count, int max, int x, int y, double score) {
    if (*count < max) {
        list[*count].x = x;
        list[*count].y = y;
        list[*count].score = score;
        (*count)++;
        return;
    }
    int worst = 0;
    for (int i = 1; i < max; ++i) {
        if (list[i].score < list[worst].score) {
            worst = i;
        }
    }
    if (score > list[worst].score) {
        list[worst].x = x;
        list[worst].y = y;
        list[worst].score = score;
    }
}

static double tpl_stats(const unsigned char *t, int n, double *sum, double *sum2) {
    double s = 0.0, s2 = 0.0;
    for (int i = 0; i < n; ++i) {
        double v = (double)t[i];
        s += v;
        s2 += v * v;
    }
    *sum = s;
    *sum2 = s2;
    return s2;
}

int match_gray(const unsigned char *img, int iw, int ih,
               const unsigned char *tpl, int tw, int th,
               double threshold, match_result *out) {
    (void)threshold;
    if (!img || !tpl || iw <= 0 || ih <= 0 || tw <= 0 || th <= 0) {
        return 0;
    }
    if (tw > iw || th > ih) {
        return 0;
    }
    double t0 = now_ms();
    memset(out, 0, sizeof(*out));

    glev ilv[MAX_LEVEL];
    glev tlv[MAX_LEVEL];
    memset(ilv, 0, sizeof(ilv));
    memset(tlv, 0, sizeof(tlv));
    int n_ilev = 1, n_tlev = 1;

    ilv[0].p = (unsigned char *)malloc((size_t)iw * (size_t)ih);
    tlv[0].p = (unsigned char *)malloc((size_t)tw * (size_t)th);
    if (!ilv[0].p || !tlv[0].p) {
        levels_free(ilv, 1);
        levels_free(tlv, 1);
        return 0;
    }
    memcpy(ilv[0].p, img, (size_t)iw * (size_t)ih);
    memcpy(tlv[0].p, tpl, (size_t)tw * (size_t)th);
    ilv[0].w = iw;
    ilv[0].h = ih;
    tlv[0].w = tw;
    tlv[0].h = th;

    for (int k = 1; k < MAX_LEVEL; ++k) {
        if (!down2(ilv[k - 1].p, ilv[k - 1].w, ilv[k - 1].h, &ilv[k])) {
            break;
        }
        n_ilev++;
    }
    for (int k = 1; k < MAX_LEVEL; ++k) {
        if (!down2(tlv[k - 1].p, tlv[k - 1].w, tlv[k - 1].h, &tlv[k])) {
            break;
        }
        n_tlev++;
    }

    /* 选择最粗且仍可容纳模板的层级 */
    int L = 0;
    int top_level = n_ilev < n_tlev ? n_ilev : n_tlev;
    for (int k = top_level - 1; k >= 0; --k) {
        if (tlv[k].w >= 4 && tlv[k].h >= 4 &&
            ilv[k].w >= tlv[k].w && ilv[k].h >= tlv[k].h) {
            L = k;
            break;
        }
    }
    int start_level = L;

    double tsum_l = 0.0, tsum2_l = 0.0;
    tpl_stats(tlv[L].p, tlv[L].w * tlv[L].h, &tsum_l, &tsum2_l);

    cand cands[TOP_K];
    int n_cands = 0;

    int rw = ilv[L].w - tlv[L].w + 1;
    int rh = ilv[L].h - tlv[L].h + 1;
    int W = ilv[L].w + 1;
    long long *S = (long long *)calloc((size_t)W * (size_t)(ilv[L].h + 1), sizeof(long long));
    long long *S2 = (long long *)calloc((size_t)W * (size_t)(ilv[L].h + 1), sizeof(long long));
    if (!S || !S2) {
        free(S);
        free(S2);
        levels_free(ilv, n_ilev);
        levels_free(tlv, n_tlev);
        return 0;
    }
    integral_build(&ilv[L], S, S2);

    for (int y = 0; y < rh; ++y) {
        for (int x = 0; x < rw; ++x) {
            double sc = ncc_integral(&ilv[L], S, S2,
                                     tlv[L].p, tlv[L].w, tlv[L].h, x, y,
                                     tsum_l, tsum2_l);
            cand_push(cands, &n_cands, TOP_K, x, y, sc);
        }
    }
    free(S);
    free(S2);

    int coarse_candidates = n_cands;

    /* 逐层精修 */
    for (int k = L - 1; k >= 0; --k) {
        double tsum = 0.0, tsum2 = 0.0;
        tpl_stats(tlv[k].p, tlv[k].w * tlv[k].h, &tsum, &tsum2);
        cand next[TOP_K];
        int n_next = 0;
        int maxx = ilv[k].w - tlv[k].w;
        int maxy = ilv[k].h - tlv[k].h;
        for (int i = 0; i < n_cands; ++i) {
            int bx = cands[i].x * 2;
            int by = cands[i].y * 2;
            for (int dy = -REFINE_RADIUS; dy <= REFINE_RADIUS; ++dy) {
                for (int dx = -REFINE_RADIUS; dx <= REFINE_RADIUS; ++dx) {
                    int x = bx + dx;
                    int y = by + dy;
                    if (x < 0 || y < 0 || x > maxx || y > maxy) {
                        continue;
                    }
                    double sc = ncc_direct(&ilv[k], tlv[k].p, tlv[k].w, tlv[k].h,
                                           x, y, tsum, tsum2);
                    cand_push(next, &n_next, TOP_K, x, y, sc);
                }
            }
        }
        if (n_next == 0) {
            break;
        }
        memcpy(cands, next, (size_t)n_next * sizeof(cand));
        n_cands = n_next;
        L = k;
    }

    int best = 0;
    for (int i = 1; i < n_cands; ++i) {
        if (cands[i].score > cands[best].score) {
            best = i;
        }
    }
    if (n_cands == 0) {
        levels_free(ilv, n_ilev);
        levels_free(tlv, n_tlev);
        return 0;
    }

    out->x = cands[best].x;
    out->y = cands[best].y;
    out->w = tw;
    out->h = th;
    out->score = cands[best].score;
    out->ms = now_ms() - t0;
    out->levels = start_level + 1;
    out->coarse_candidates = coarse_candidates;

    levels_free(ilv, n_ilev);
    levels_free(tlv, n_tlev);
    return 1;
}

int match_bgra(const unsigned char *img, int iw, int ih,
               const unsigned char *tpl, int tw, int th,
               double threshold, match_result *out) {
    unsigned char *gi = bgra_to_gray(img, iw, ih);
    unsigned char *gt = bgra_to_gray(tpl, tw, th);
    if (!gi || !gt) {
        free(gi);
        free(gt);
        return 0;
    }
    int ok = match_gray(gi, iw, ih, gt, tw, th, threshold, out);
    free(gi);
    free(gt);
    return ok;
}

int match_file(const char *template_path,
               const unsigned char *bgra_img, int iw, int ih,
               double threshold, match_result *out) {
    if (!template_path || !bgra_img) {
        return 0;
    }
    int tw = 0, th = 0;
    unsigned char *gt = img_load_gray(template_path, &tw, &th);
    if (!gt) {
        return 0;
    }
    unsigned char *gi = bgra_to_gray(bgra_img, iw, ih);
    if (!gi) {
        free(gt);
        return 0;
    }
    int ok = match_gray(gi, iw, ih, gt, tw, th, threshold, out);
    free(gi);
    free(gt);
    return ok;
}
