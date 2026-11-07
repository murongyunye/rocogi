#include "json.h"

#include <stdlib.h>
#include <string.h>

typedef struct {
    const char *p;
    const char *end;
    int error;
} jparser;

static void *xcalloc(size_t n, size_t sz) {
    void *p = calloc(n, sz);
    return p;
}

static jval *jnew(jtype t) {
    jval *v = (jval *)xcalloc(1, sizeof(jval));
    if (v) {
        v->t = t;
    }
    return v;
}

void json_free(jval *v) {
    if (!v) {
        return;
    }
    if (v->t == JSTR) {
        free(v->s);
    }
    if (v->items) {
        for (int i = 0; i < v->count; ++i) {
            json_free(v->items[i]);
        }
        free(v->items);
    }
    if (v->keys) {
        for (int i = 0; i < v->count; ++i) {
            free(v->keys[i]);
        }
        free(v->keys);
    }
    free(v);
}

static void skip_ws(jparser *jp) {
    while (jp->p < jp->end) {
        char c = *jp->p;
        if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
            jp->p++;
        } else {
            break;
        }
    }
}

static jval *parse_value(jparser *jp, int depth);

static char *parse_raw_string(jparser *jp) {
    if (jp->p >= jp->end || *jp->p != '"') {
        jp->error = 1;
        return NULL;
    }
    jp->p++;
    size_t cap = 64, len = 0;
    char *out = (char *)malloc(cap);
    if (!out) {
        jp->error = 1;
        return NULL;
    }
    while (jp->p < jp->end && *jp->p != '"') {
        unsigned char c = (unsigned char)*jp->p++;
        if (c == '\\') {
            if (jp->p >= jp->end) {
                break;
            }
            unsigned char e = (unsigned char)*jp->p++;
            switch (e) {
                case '"': c = '"'; break;
                case '\\': c = '\\'; break;
                case '/': c = '/'; break;
                case 'b': c = '\b'; break;
                case 'f': c = '\f'; break;
                case 'n': c = '\n'; break;
                case 'r': c = '\r'; break;
                case 't': c = '\t'; break;
                case 'u': {
                    if (jp->p + 4 > jp->end) {
                        jp->error = 1;
                        free(out);
                        return NULL;
                    }
                    unsigned int code = 0;
                    for (int i = 0; i < 4; ++i) {
                        char h = *jp->p++;
                        code <<= 4;
                        if (h >= '0' && h <= '9') code |= (unsigned)(h - '0');
                        else if (h >= 'a' && h <= 'f') code |= (unsigned)(h - 'a' + 10);
                        else if (h >= 'A' && h <= 'F') code |= (unsigned)(h - 'A' + 10);
                        else { jp->error = 1; free(out); return NULL; }
                    }
                    /* 仅处理 BMP 内的字符；代理对按原样丢弃低位 */
                    if (code >= 0xD800 && code <= 0xDBFF) {
                        c = '?';
                    } else {
                        c = (unsigned char)code;
                    }
                    break;
                }
                default:
                    c = e;
            }
        }
        if (len + 2 > cap) {
            cap *= 2;
            char *next = (char *)realloc(out, cap);
            if (!next) {
                jp->error = 1;
                free(out);
                return NULL;
            }
            out = next;
        }
        out[len++] = (char)c;
    }
    if (jp->p >= jp->end) {
        jp->error = 1;
        free(out);
        return NULL;
    }
    jp->p++; /* 跳过结束引号 */
    out[len] = '\0';
    return out;
}

static int push_item(jval *v, jval *item, char *key) {
    jval **items = (jval **)realloc(v->items, sizeof(jval *) * (size_t)(v->count + 1));
    if (!items) {
        return 0;
    }
    v->items = items;
    if (v->t == JOBJ) {
        char **keys = (char **)realloc(v->keys, sizeof(char *) * (size_t)(v->count + 1));
        if (!keys) {
            return 0;
        }
        v->keys = keys;
        v->keys[v->count] = key;
    }
    v->items[v->count] = item;
    v->count++;
    return 1;
}

static jval *parse_array(jparser *jp, int depth) {
    jval *v = jnew(JARR);
    if (!v) {
        jp->error = 1;
        return NULL;
    }
    jp->p++; /* [ */
    skip_ws(jp);
    if (jp->p < jp->end && *jp->p == ']') {
        jp->p++;
        return v;
    }
    while (jp->p < jp->end) {
        jval *item = parse_value(jp, depth + 1);
        if (!item) {
            json_free(v);
            return NULL;
        }
        if (!push_item(v, item, NULL)) {
            json_free(item);
            json_free(v);
            jp->error = 1;
            return NULL;
        }
        skip_ws(jp);
        if (jp->p < jp->end && *jp->p == ',') {
            jp->p++;
            skip_ws(jp);
            continue;
        }
        break;
    }
    if (jp->p >= jp->end || *jp->p != ']') {
        json_free(v);
        jp->error = 1;
        return NULL;
    }
    jp->p++;
    return v;
}

static jval *parse_object(jparser *jp, int depth) {
    jval *v = jnew(JOBJ);
    if (!v) {
        jp->error = 1;
        return NULL;
    }
    jp->p++; /* { */
    skip_ws(jp);
    if (jp->p < jp->end && *jp->p == '}') {
        jp->p++;
        return v;
    }
    while (jp->p < jp->end) {
        skip_ws(jp);
        char *key = parse_raw_string(jp);
        if (!key) {
            json_free(v);
            jp->error = 1;
            return NULL;
        }
        skip_ws(jp);
        if (jp->p >= jp->end || *jp->p != ':') {
            free(key);
            json_free(v);
            jp->error = 1;
            return NULL;
        }
        jp->p++;
        jval *item = parse_value(jp, depth + 1);
        if (!item) {
            free(key);
            json_free(v);
            return NULL;
        }
        if (!push_item(v, item, key)) {
            free(key);
            json_free(item);
            json_free(v);
            jp->error = 1;
            return NULL;
        }
        skip_ws(jp);
        if (jp->p < jp->end && *jp->p == ',') {
            jp->p++;
            continue;
        }
        break;
    }
    skip_ws(jp);
    if (jp->p >= jp->end || *jp->p != '}') {
        json_free(v);
        jp->error = 1;
        return NULL;
    }
    jp->p++;
    return v;
}

static jval *parse_value(jparser *jp, int depth) {
    if (depth > 64) {
        jp->error = 1;
        return NULL;
    }
    skip_ws(jp);
    if (jp->p >= jp->end) {
        jp->error = 1;
        return NULL;
    }
    char c = *jp->p;
    if (c == '{') {
        return parse_object(jp, depth);
    }
    if (c == '[') {
        return parse_array(jp, depth);
    }
    if (c == '"') {
        jval *v = jnew(JSTR);
        if (!v) {
            jp->error = 1;
            return NULL;
        }
        v->s = parse_raw_string(jp);
        if (!v->s) {
            json_free(v);
            return NULL;
        }
        return v;
    }
    if (c == 't' && jp->end - jp->p >= 4 && strncmp(jp->p, "true", 4) == 0) {
        jp->p += 4;
        jval *v = jnew(JBOOL);
        if (v) v->b = 1;
        return v;
    }
    if (c == 'f' && jp->end - jp->p >= 5 && strncmp(jp->p, "false", 5) == 0) {
        jp->p += 5;
        return jnew(JBOOL);
    }
    if (c == 'n' && jp->end - jp->p >= 4 && strncmp(jp->p, "null", 4) == 0) {
        jp->p += 4;
        return jnew(JNULL);
    }
    {
        char buf[64];
        int n = 0;
        while (jp->p < jp->end && n < 63) {
            char d = *jp->p;
            if ((d >= '0' && d <= '9') || d == '-' || d == '+' || d == '.' || d == 'e' || d == 'E') {
                buf[n++] = d;
                jp->p++;
            } else {
                break;
            }
        }
        if (n == 0) {
            jp->error = 1;
            return NULL;
        }
        buf[n] = '\0';
        jval *v = jnew(JNUM);
        if (!v) {
            jp->error = 1;
            return NULL;
        }
        v->n = strtod(buf, NULL);
        return v;
    }
}

jval *json_parse(const char *text, size_t len) {
    jparser jp;
    jp.p = text;
    jp.end = text + len;
    jp.error = 0;
    jval *v = parse_value(&jp, 0);
    if (!v || jp.error) {
        json_free(v);
        return NULL;
    }
    return v;
}

jval *json_get(const jval *obj, const char *key) {
    if (!obj || obj->t != JOBJ || !key) {
        return NULL;
    }
    for (int i = 0; i < obj->count; ++i) {
        if (obj->keys[i] && strcmp(obj->keys[i], key) == 0) {
            return obj->items[i];
        }
    }
    return NULL;
}

const char *json_str(const jval *v, const char *def) {
    if (!v || v->t != JSTR || !v->s) {
        return def;
    }
    return v->s;
}

double json_num(const jval *v, double def) {
    if (!v) {
        return def;
    }
    if (v->t == JNUM) {
        return v->n;
    }
    if (v->t == JSTR && v->s) {
        return strtod(v->s, NULL);
    }
    return def;
}

int json_bool(const jval *v, int def) {
    if (!v) {
        return def;
    }
    if (v->t == JBOOL) {
        return v->b;
    }
    if (v->t == JNUM) {
        return v->n != 0;
    }
    return def;
}

int json_len(const jval *v) {
    if (!v || v->t == JNULL) {
        return 0;
    }
    return v->count;
}
