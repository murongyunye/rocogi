#ifndef ROCogi_STRBUF_H
#define ROCogi_STRBUF_H

#include <stddef.h>

typedef struct {
    char *data;
    size_t len;
    size_t cap;
} strbuf;

void sb_init(strbuf *sb);
void sb_free(strbuf *sb);
void sb_clear(strbuf *sb);
void sb_put(strbuf *sb, const char *text);
void sb_putf(strbuf *sb, const char *fmt, ...);
/* 以 JSON 字符串字面量形式写入（自动转义、加引号） */
void sb_json_str(strbuf *sb, const char *text);
/* 写入不带引号的 JSON 数字，整数用 %lld，非整数用 %.10g */
void sb_json_num(strbuf *sb, double value);

#endif
