#ifndef ROCogi_PATH_FOLLOW_H
#define ROCogi_PATH_FOLLOW_H

/* 路径跟随几何计算：用于地图路线（roco-map-tracker / luoke_location 点位序列）
 * 在 C 侧做航点推进、前视点与朝向误差，替代 Python 端点里的逐步循环。 */

typedef struct {
    double x;
    double y;
} path_point;

double path_length(const path_point *points, int count);

/* 点到线段最短距离；out_t 返回投影参数（0..1），可为 NULL。 */
double path_point_segment_distance(path_point p, path_point a, path_point b,
                                   double *out_t);

/* 从 start_index 起，若当前位置已到达下一个航点（距离 <= tolerance）则推进，返回新下标。 */
int path_progress(const path_point *points, int count, path_point position,
                  double tolerance, int start_index);

/* 沿折线从 index 起前进 lookahead 距离，输出前视点。点数不足返回 0。 */
int path_lookahead(const path_point *points, int count, int index,
                   double lookahead, path_point *out);

/* 目标朝向与当前朝向的最短夹角，范围 (-180, 180]。 */
double path_heading_error(double current_deg, double target_deg);

#endif
