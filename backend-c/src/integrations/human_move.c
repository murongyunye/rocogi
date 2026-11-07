#include "human_move.h"

#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

double human_ease_curve(double t, human_ease_kind kind) {
    if (t <= 0.0) {
        return 0.0;
    }
    if (t >= 1.0) {
        return 1.0;
    }
    switch (kind) {
        case HUMAN_EASE_DECAY:
            return 1.0 - pow(1.0 - t, 2.5);
        case HUMAN_EASE_SINE:
            return 0.5 * (sin((t - 0.5) * M_PI) + 1.0);
        case HUMAN_EASE_SMOOTH:
        default:
            return t * t * (3.0 - 2.0 * t);
    }
}

static int run_phase(double *cur_x, double *cur_y, double dx, double dy,
                     int steps, human_ease_kind kind, int max_step,
                     screen_point *out, int used, int out_cap) {
    if (steps < 1) {
        steps = 1;
    }
    double base_x = *cur_x;
    double base_y = *cur_y;

    for (int i = 1; i <= steps; ++i) {
        double t = (double)i / (double)steps;
        double ease = human_ease_curve(t, kind);
        int next_x = (int)(base_x + dx * ease);
        int next_y = (int)(base_y + dy * ease);

        int step_x = next_x - (int)*cur_x;
        int step_y = next_y - (int)*cur_y;
        if (max_step > 0) {
            if (step_x > max_step) step_x = max_step;
            if (step_x < -max_step) step_x = -max_step;
            if (step_y > max_step) step_y = max_step;
            if (step_y < -max_step) step_y = -max_step;
        }

        next_x = (int)*cur_x + step_x;
        next_y = (int)*cur_y + step_y;
        *cur_x = (double)next_x;
        *cur_y = (double)next_y;

        if (used < out_cap) {
            out[used].x = next_x;
            out[used].y = next_y;
        }
        used++;
    }
    return used;
}

int human_move_plan(int start_x, int start_y, int target_x, int target_y,
                    int steps, human_ease_kind kind, double overshoot_ratio,
                    int max_step, screen_point *out, int out_cap) {
    if (!out || out_cap <= 0) {
        return -1;
    }
    if (steps < 1) {
        steps = 1;
    }

    double total_x = (double)target_x - (double)start_x;
    double total_y = (double)target_y - (double)start_y;
    if (fabs(total_x) < 2.0 && fabs(total_y) < 2.0) {
        return 0;
    }

    double overshoot_x = 0.0;
    double overshoot_y = 0.0;
    if (overshoot_ratio > 0.0) {
        overshoot_x = total_x * overshoot_ratio;
        overshoot_y = total_y * overshoot_ratio;
    }

    double cur_x = (double)start_x;
    double cur_y = (double)start_y;
    int used = 0;

    int main_steps = steps;
    if (overshoot_x != 0.0 || overshoot_y != 0.0) {
        main_steps = steps - 3;
        if (main_steps < 2) {
            main_steps = 2;
        }
    }
    used = run_phase(&cur_x, &cur_y, total_x + overshoot_x, total_y + overshoot_y,
                     main_steps, kind, max_step, out, used, out_cap);

    if (overshoot_x != 0.0 || overshoot_y != 0.0) {
        used = run_phase(&cur_x, &cur_y, -overshoot_x, -overshoot_y,
                         3, kind, max_step, out, used, out_cap);
    }
    return used;
}
