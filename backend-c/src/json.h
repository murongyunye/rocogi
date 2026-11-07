#ifndef ROCogi_JSON_H
#define ROCogi_JSON_H

#include <stddef.h>

typedef enum { JNULL, JBOOL, JNUM, JSTR, JARR, JOBJ } jtype;

typedef struct jval {
    jtype t;
    int b;                  /* JBOOL */
    double n;               /* JNUM */
    char *s;                /* JSTR */
    struct jval **items;    /* JARR / JOBJ 值 */
    char **keys;            /* JOBJ 键，与 items 对齐 */
    int count;
} jval;

jval *json_parse(const char *text, size_t len);
void json_free(jval *v);

jval *json_get(const jval *obj, const char *key);
const char *json_str(const jval *v, const char *def);
double json_num(const jval *v, double def);
int json_bool(const jval *v, int def);
int json_len(const jval *v);

#endif
