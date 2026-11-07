#include "route_plan.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../json.h"

static char *dup_str(const char *text) {
    if (!text) {
        return NULL;
    }
    size_t n = strlen(text);
    char *out = (char *)malloc(n + 1);
    if (out) {
        memcpy(out, text, n + 1);
    }
    return out;
}

static char *dup_str_or(const char *text, const char *fallback) {
    return dup_str(text ? text : fallback);
}

poi_point *poi_load_json(const char *text, size_t len, int *out_count) {
    if (!out_count) {
        return NULL;
    }
    *out_count = 0;
    if (!text) {
        return NULL;
    }
    jval *doc = json_parse(text, len);
    if (!doc || doc->t != JARR) {
        json_free(doc);
        return NULL;
    }
    poi_point *points = (poi_point *)calloc((size_t)doc->count, sizeof(poi_point));
    if (!points) {
        json_free(doc);
        return NULL;
    }

    int count = 0;
    for (int i = 0; i < doc->count; ++i) {
        jval *item = doc->items[i];
        if (!item || item->t != JOBJ) {
            continue;
        }
        const char *label = json_str(json_get(item, "label"), NULL);
        const char *category = json_str(json_get(item, "category"), NULL);
        const char *id = json_str(json_get(item, "id"), NULL);
        const char *title = json_str(json_get(item, "title"), NULL);
        points[count].label = dup_str_or(label, "未分类");
        points[count].category = dup_str_or(category, "其他");
        points[count].id = dup_str_or(id, "");
        points[count].title = dup_str_or(title, points[count].label);
        points[count].x = json_num(json_get(item, "x"), 0.0);
        points[count].y = json_num(json_get(item, "y"), 0.0);
        if (!points[count].id[0]) {
            free(points[count].id);
            char fallback[24];
            snprintf(fallback, sizeof(fallback), "p%d", count);
            points[count].id = dup_str(fallback);
        }
        if (!points[count].label || !points[count].category || !points[count].id ||
            !points[count].title) {
            poi_free(points, count + 1);
            json_free(doc);
            return NULL;
        }
        count++;
    }
    json_free(doc);
    *out_count = count;
    return points;
}

void poi_free(poi_point *points, int count) {
    if (!points) {
        return;
    }
    for (int i = 0; i < count; ++i) {
        free(points[i].id);
        free(points[i].title);
        free(points[i].label);
        free(points[i].category);
    }
    free(points);
}

static int name_in_list(const char *name, const char *const *list, int count) {
    if (!list || count <= 0) {
        return 1;
    }
    for (int i = 0; i < count; ++i) {
        if (list[i] && name && strcmp(list[i], name) == 0) {
            return 1;
        }
    }
    return 0;
}

static double dist2(double ax, double ay, double bx, double by) {
    double dx = ax - bx;
    double dy = ay - by;
    return dx * dx + dy * dy;
}

int route_plan(const poi_point *points, int point_count,
               const route_opts *opts, route_result *out) {
    if (!out) {
        return 0;
    }
    memset(out, 0, sizeof(*out));
    if (!opts || !points || point_count <= 0) {
        return 1;
    }

    int limit = opts->limit;
    if (limit < 1) {
        limit = 1;
    }
    if (limit > 200) {
        limit = 200;
    }

    int *candidates = (int *)malloc(sizeof(int) * (size_t)point_count);
    int *visited = (int *)calloc((size_t)point_count, sizeof(int));
    int *order = (int *)malloc(sizeof(int) * (size_t)(limit > 0 ? limit : 1));
    if (!candidates || !visited || !order) {
        free(candidates);
        free(visited);
        free(order);
        return 0;
    }

    int candidate_count = 0;
    for (int i = 0; i < point_count; ++i) {
        if (!name_in_list(points[i].label, opts->labels, opts->label_count)) {
            continue;
        }
        if (!name_in_list(points[i].category, opts->categories, opts->category_count)) {
            continue;
        }
        candidates[candidate_count++] = i;
    }
    if (limit > candidate_count) {
        limit = candidate_count;
    }

    double current_x = opts->start_x;
    double current_y = opts->start_y;
    int used = 0;
    double distance = 0.0;

    for (int step = 0; step < limit; ++step) {
        int best = -1;
        double best_dist = 0.0;
        for (int i = 0; i < candidate_count; ++i) {
            int index = candidates[i];
            if (visited[index]) {
                continue;
            }
            double d = dist2(points[index].x, points[index].y, current_x, current_y);
            if (best < 0 || d < best_dist) {
                best = index;
                best_dist = d;
            }
        }
        if (best < 0) {
            break;
        }
        visited[best] = 1;
        distance += sqrt(best_dist);
        current_x = points[best].x;
        current_y = points[best].y;
        order[used++] = best;
    }

    int has_return = 0;
    if (opts->roundtrip && used > 0) {
        distance += hypot(current_x - opts->start_x, current_y - opts->start_y);
        has_return = 1;
    }

    free(visited);
    free(candidates);
    out->indices = order;
    out->count = used;
    out->distance = distance;
    out->has_return = has_return;
    return 1;
}

void route_result_free(route_result *result) {
    if (!result) {
        return;
    }
    free(result->indices);
    memset(result, 0, sizeof(*result));
}
