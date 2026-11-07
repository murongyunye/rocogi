#include "path_follow.h"

#include <math.h>

double path_length(const path_point *points, int count) {
    if (!points || count < 2) {
        return 0.0;
    }
    double total = 0.0;
    for (int i = 1; i < count; ++i) {
        total += hypot(points[i].x - points[i - 1].x,
                       points[i].y - points[i - 1].y);
    }
    return total;
}

double path_point_segment_distance(path_point p, path_point a, path_point b,
                                   double *out_t) {
    double dx = b.x - a.x;
    double dy = b.y - a.y;
    double len2 = dx * dx + dy * dy;
    double t = 0.0;
    if (len2 > 0.0) {
        t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / len2;
        if (t < 0.0) t = 0.0;
        if (t > 1.0) t = 1.0;
    }
    double px = a.x + t * dx;
    double py = a.y + t * dy;
    if (out_t) {
        *out_t = t;
    }
    return hypot(p.x - px, p.y - py);
}

int path_progress(const path_point *points, int count, path_point position,
                  double tolerance, int start_index) {
    if (!points || count <= 0) {
        return 0;
    }
    int index = start_index;
    if (index < 0) {
        index = 0;
    }
    if (index >= count) {
        index = count - 1;
    }
    while (index + 1 < count &&
           hypot(position.x - points[index + 1].x,
                 position.y - points[index + 1].y) <= tolerance) {
        index++;
    }
    return index;
}

int path_lookahead(const path_point *points, int count, int index,
                   double lookahead, path_point *out) {
    if (!points || !out || count <= 0) {
        return 0;
    }
    if (index < 0) {
        index = 0;
    }
    if (index >= count) {
        index = count - 1;
    }
    if (lookahead <= 0.0) {
        *out = points[index];
        return 1;
    }

    int i = index;
    double remain = lookahead;
    while (i + 1 < count) {
        double seg = hypot(points[i + 1].x - points[i].x,
                           points[i + 1].y - points[i].y);
        if (seg <= 0.0) {
            i++;
            continue;
        }
        if (remain <= seg) {
            double t = remain / seg;
            out->x = points[i].x + (points[i + 1].x - points[i].x) * t;
            out->y = points[i].y + (points[i + 1].y - points[i].y) * t;
            return 1;
        }
        remain -= seg;
        i++;
    }
    *out = points[count - 1];
    return 1;
}

double path_heading_error(double current_deg, double target_deg) {
    double delta = fmod(target_deg - current_deg, 360.0);
    if (delta > 180.0) {
        delta -= 360.0;
    } else if (delta <= -180.0) {
        delta += 360.0;
    }
    return delta;
}
