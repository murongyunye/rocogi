#ifndef ROCogi_MATCH_H
#define ROCogi_MATCH_H

typedef struct {
    int x;              /* 命中左上角（原图坐标） */
    int y;
    int w;              /* 模板宽高（原图坐标） */
    int h;
    double score;       /* 归一化互相关，-1..1 */
    double ms;          /* 耗时 */
    int levels;         /* 金字塔层数（1 表示只用了原图） */
    int coarse_candidates;
} match_result;

/* 灰度 NCC 模板匹配：4x 金字塔粗搜 + 全分辨率精修 */
int match_gray(const unsigned char *img, int iw, int ih,
               const unsigned char *tpl, int tw, int th,
               double threshold, match_result *out);

/* BGRA 版本：内部转灰度 */
int match_bgra(const unsigned char *img, int iw, int ih,
               const unsigned char *tpl, int tw, int th,
               double threshold, match_result *out);

/* 从 PNG 文件加载灰度模板，并在 BGRA 截图里匹配 */
int match_file(const char *template_path,
               const unsigned char *bgra_img, int iw, int ih,
               double threshold, match_result *out);

#endif
