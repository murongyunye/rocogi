#include "strbuf.h"

#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void sb_init(strbuf *sb) {
    sb->data = NULL;
    sb->len = 0;
    sb->cap = 0;
}

void sb_free(strbuf *sb) {
    free(sb->data);
    sb->data = NULL;
    sb->len = 0;
    sb->cap = 0;
}

void sb_clear(strbuf *sb) {
    sb->len = 0;
    if (sb->data) {
        sb->data[0] = '\0';
    }
}

static int sb_reserve(strbuf *sb, size_t extra) {
    if (sb->len + extra + 1 <= sb->cap) {
        return 1;
    }
    size_t cap = sb->cap ? sb->cap : 64;
    while (cap < sb->len + extra + 1) {
        cap *= 2;
    }
    char *next = (char *)realloc(sb->data, cap);
    if (!next) {
        return 0;
    }
    sb->data = next;
    sb->cap = cap;
    return 1;
}

void sb_put(strbuf *sb, const char *text) {
    if (!text) {
        return;
    }
    size_t n = strlen(text);
    if (!sb_reserve(sb, n)) {
        return;
    }
    memcpy(sb->data + sb->len, text, n);
    sb->len += n;
    sb->data[sb->len] = '\0';
}

void sb_putf(strbuf *sb, const char *fmt, ...) {
    char tmp[512];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(tmp, sizeof(tmp), fmt, ap);
    va_end(ap);
    sb_put(sb, tmp);
}

void sb_json_str(strbuf *sb, const char *text) {
    sb_put(sb, "\"");
    if (text) {
        for (const unsigned char *p = (const unsigned char *)text; *p; ++p) {
            switch (*p) {
                case '"': sb_put(sb, "\\\""); break;
                case '\\': sb_put(sb, "\\\\"); break;
                case '\b': sb_put(sb, "\\b"); break;
                case '\f': sb_put(sb, "\\f"); break;
                case '\n': sb_put(sb, "\\n"); break;
                case '\r': sb_put(sb, "\\r"); break;
                case '\t': sb_put(sb, "\\t"); break;
                default:
                    if (*p < 0x20) {
                        sb_putf(sb, "\\u%04x", *p);
                    } else {
                        char one[2] = {(char)*p, '\0'};
                        sb_put(sb, one);
                    }
            }
        }
    }
    sb_put(sb, "\"");
}

void sb_json_num(strbuf *sb, double value) {
    if (!isfinite(value)) {
        sb_put(sb, "null");
        return;
    }
    if (value == (double)(long long)value && fabs(value) < 1e15) {
        sb_putf(sb, "%lld", (long long)value);
    } else {
        sb_putf(sb, "%.10g", value);
    }
}
