#include "mapstat.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "host.h"
#include "json.h"
#include "strbuf.h"

#define MAP_WIDTH 6144
#define MAP_HEIGHT 5888
#define DEDUP_SLOTS (1 << 15)

typedef struct {
    double rx;
    double ry;
    const char *label;
} dedup_key;

typedef struct {
    const char *name;
    int count;
    int first;
} stat_entry;

typedef struct {
    stat_entry *items;
    int count;
    int cap;
} stat_list;

static const char *PALETTE[] = {
    "#5eead4", "#fbbf24", "#f472b6", "#60a5fa", "#34d399",
    "#a78bfa", "#fb923c", "#38bdf8", "#facc15", "#c084fc",
    "#4ade80", "#f87171", "#94a3b8", "#2dd4bf", "#e879f9"};
static const int PALETTE_N = (int)(sizeof(PALETTE) / sizeof(PALETTE[0]));

static char *g_json = NULL;
static int g_points = 0;

static char *dup_local(const char *s) {
    if (!s) return NULL;
    size_t n = strlen(s);
    char *out = (char *)malloc(n + 1);
    if (out) memcpy(out, s, n + 1);
    return out;
}

static uint64_t hash_key(double rx, double ry, const char *label) {
    uint64_t h = (uint64_t)(int64_t)rx * 1000003ULL;
    h ^= (uint64_t)(int64_t)ry * 2654435761ULL;
    for (const char *p = label; *p; ++p) {
        h = h * 131 + (unsigned char)*p;
    }
    h ^= h >> 33;
    h *= 0xff51afd7ed558ccdULL;
    h ^= h >> 33;
    return h;
}

static int stat_add(stat_list *list, const char *name, int first) {
    for (int i = 0; i < list->count; ++i) {
        if (list->items[i].name && name && strcmp(list->items[i].name, name) == 0) {
            list->items[i].count++;
            return 1;
        }
    }
    if (list->count >= list->cap) {
        int cap = list->cap ? list->cap * 2 : 32;
        stat_entry *next = (stat_entry *)realloc(list->items, sizeof(stat_entry) * (size_t)cap);
        if (!next) {
            return 0;
        }
        list->items = next;
        list->cap = cap;
    }
    list->items[list->count].name = name;
    list->items[list->count].count = 1;
    list->items[list->count].first = first;
    list->count++;
    return 1;
}

static int cmp_stat(const void *a, const void *b) {
    const stat_entry *x = (const stat_entry *)a;
    const stat_entry *y = (const stat_entry *)b;
    if (y->count != x->count) {
        return y->count - x->count;
    }
    return x->first - y->first;
}

static void emit_list(strbuf *sb, stat_list *list, int limit, int with_color) {
    qsort(list->items, (size_t)list->count, sizeof(stat_entry), cmp_stat);
    int n = list->count < limit ? list->count : limit;
    sb_put(sb, "[");
    for (int i = 0; i < n; ++i) {
        if (i) sb_put(sb, ",");
        sb_put(sb, "{\"id\":");
        sb_json_str(sb, list->items[i].name ? list->items[i].name : "");
        sb_put(sb, ",\"label\":");
        sb_json_str(sb, list->items[i].name ? list->items[i].name : "");
        sb_put(sb, ",\"count\":");
        sb_putf(sb, "%d", list->items[i].count);
        if (with_color) {
            sb_put(sb, ",\"color\":");
            sb_json_str(sb, PALETTE[i % PALETTE_N]);
        }
        sb_put(sb, "}");
    }
    sb_put(sb, "]");
}

int mapstat_init(const char *map_dir) {
    if (g_json) {
        return 1;
    }
    stat_list categories = {0};
    stat_list labels = {0};
    jval *docs[2] = {NULL, NULL};
    const char *files[2] = {"taptap.json", "easy_roco.json"};
    dedup_key *seen = (dedup_key *)calloc(DEDUP_SLOTS, sizeof(dedup_key));
    int *used = (int *)calloc(DEDUP_SLOTS, sizeof(int));
    if (!seen || !used) {
        free(seen);
        free(used);
        return 0;
    }

    int first_index = 0;
    for (int f = 0; f < 2; ++f) {
        char *path = host_path_join(map_dir, files[f]);
        char *text = NULL;
        size_t len = 0;
        if (path && host_read_file(path, &text, &len) && text) {
            docs[f] = json_parse(text, len);
        }
        free(path);
        free(text);
        if (!docs[f] || docs[f]->t != JARR) {
            continue;
        }
        for (int i = 0; i < docs[f]->count; ++i) {
            jval *item = docs[f]->items[i];
            if (!item || item->t != JOBJ) {
                continue;
            }
            const char *label = json_str(json_get(item, "label"), "未分类");
            const char *category = json_str(json_get(item, "category"), "其他");
            double x = json_num(json_get(item, "pixel_x"), 0);
            double y = json_num(json_get(item, "pixel_y"), 0);
            double rx = nearbyint(x / 24.0);
            double ry = nearbyint(y / 24.0);
            uint64_t h = hash_key(rx, ry, label);
            int slot = (int)(h & (DEDUP_SLOTS - 1));
            int duplicate = 0;
            for (int probe = 0; probe < DEDUP_SLOTS; ++probe) {
                int at = (slot + probe) & (DEDUP_SLOTS - 1);
                if (!used[at]) {
                    used[at] = 1;
                    seen[at].rx = rx;
                    seen[at].ry = ry;
                    seen[at].label = dup_local(label);
                    break;
                }
                if (seen[at].rx == rx && seen[at].ry == ry && strcmp(seen[at].label, label) == 0) {
                    duplicate = 1;
                    break;
                }
            }
            if (duplicate) {
                continue;
            }
            g_points++;
            stat_add(&categories, category, first_index);
            stat_add(&labels, label, first_index);
            first_index++;
        }
    }

    int marker_count = 0;
    char *mt_path = host_path_join(map_dir, "marker_types.json");
    char *mt_text = NULL;
    size_t mt_len = 0;
    if (mt_path && host_read_file(mt_path, &mt_text, &mt_len) && mt_text) {
        jval *mt = json_parse(mt_text, mt_len);
        if (mt && mt->t == JARR) {
            marker_count = mt->count;
        }
        json_free(mt);
    }
    free(mt_path);
    free(mt_text);

    strbuf sb;
    sb_init(&sb);
    sb_put(&sb, "{\"pointCount\":");
    sb_putf(&sb, "%d", g_points);
    sb_put(&sb, ",\"categoryCount\":");
    sb_putf(&sb, "%d", categories.count);
    sb_put(&sb, ",\"labelCount\":");
    sb_putf(&sb, "%d", labels.count);
    sb_put(&sb, ",\"categories\":");
    emit_list(&sb, &categories, categories.count, 1);
    sb_put(&sb, ",\"labels\":");
    emit_list(&sb, &labels, 80, 0);
    sb_put(&sb, ",\"mapWidth\":");
    sb_putf(&sb, "%d", MAP_WIDTH);
    sb_put(&sb, ",\"mapHeight\":");
    sb_putf(&sb, "%d", MAP_HEIGHT);
    sb_put(&sb, ",\"baseMap\":\"/api/assets/map/base_map.jpg\",\"markerTypeCount\":");
    sb_putf(&sb, "%d", marker_count);
    sb_put(&sb, "}");

    g_json = sb.data;

    free(categories.items);
    free(labels.items);
    for (int i = 0; i < DEDUP_SLOTS; ++i) {
        if (used[i]) {
            free((void *)seen[i].label);
        }
    }
    free(seen);
    free(used);
    json_free(docs[0]);
    json_free(docs[1]);
    return g_json != NULL;
}

const char *mapstat_json(void) {
    return g_json ? g_json : "{}";
}

int mapstat_point_count(void) {
    return g_points;
}
