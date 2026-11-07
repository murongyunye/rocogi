#ifndef ROCogi_STATIC_H
#define ROCogi_STATIC_H

#include "http.h"

/* 尝试从 root 下读取文件；命中返回 1，未命中返回 0 */
int static_serve(const char *root, const char *url_path, http_response *res);

#endif
