#ifndef ROCogi_HTTP_H
#define ROCogi_HTTP_H

#include <stddef.h>

typedef struct {
    char method[16];
    char path[2048];
    char query[1024];
    char *body;
    size_t body_len;
} http_request;

typedef struct {
    int status;
    char *content_type;
    char *body;
    size_t len;
} http_response;

typedef void (*http_handler)(const http_request *req, http_response *res);

void http_reply(http_response *res, int status, const char *content_type, const char *body);
void http_reply_alloc(http_response *res, int status, const char *content_type, char *body, size_t len);

int http_run(const char *host, int port, http_handler handler);

#endif
