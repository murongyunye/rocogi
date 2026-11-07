#ifndef ROCogi_HUMAN_MOVE_H
#define ROCogi_HUMAN_MOVE_H

/* 拟人鼠标移动轨迹：重写 AutoCapture（Tsuann/RocoKingdom-AutoCapture）
 * controller.py 的 move_to / _human_ease，去掉随机抖动，保留缓动、过冲与单步限幅。 */

typedef struct {
    int x;
    int y;
} screen_point;

typedef enum {
    HUMAN_EASE_DECAY = 0,     /* 先快后慢 1-(1-t)^2.5 */
    HUMAN_EASE_SMOOTH = 1,    /* S 型 3t^2-2t^3 */
    HUMAN_EASE_SINE = 2       /* 先慢后快再慢 */
} human_ease_kind;

double human_ease_curve(double t, human_ease_kind kind);

/* 生成绝对坐标轨迹（不含起点）。overshoot_ratio=0 时单阶段；>0 时先过冲再回正。
 * max_step 为单轴限幅（上游 HID 为 127）。返回写入 out 的点数，失败返回 -1。 */
int human_move_plan(int start_x, int start_y, int target_x, int target_y,
                    int steps, human_ease_kind kind, double overshoot_ratio,
                    int max_step, screen_point *out, int out_cap);

#endif
