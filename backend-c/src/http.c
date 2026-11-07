#include "http.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <winsock2.h>
#include <ws2tcpip.h>

#define HEADER_MAX 65536
#define BODY_MAX (8 * 1024 * 1024)

void http_reply(http_response *res, int status, const char *content_type, const char *body) {
    const char *text = body ? body : "";
    size_t n = strlen(text);
    char *copy = (char *)malloc(n + 1);
    if (!copy) {
        res->status = 500;
        res->content_type = "text/plain; charset=utf-8";
        res->body = NULL;
        res->len = 0;
        return;
    }
    memcpy(copy, text, n + 1);
    res->status = status;
    res->content_type = (char *)(content_type ? content_type : "text/plain; charset=utf-8");
    res->body = copy;
    res->len = n;
}

void http_reply_alloc(http_response *res, int status, const char *content_type, char *body, size_t len) {
    res->status = status;
    res->content_type = (char *)(content_type ? content_type : "text/plain; charset=utf-8");
    res->body = body;
    res->len = len;
}

static const char *status_text(int code) {
    switch (code) {
        case 200: return "OK";
        case 201: return "Created";
        case 204: return "No Content";
        case 400: return "Bad Request";
        case 404: return "Not Found";
        case 405: return "Method Not Allowed";
        case 500: return "Internal Server Error";
        default: return "OK";
    }
}

static int send_all(SOCKET s, const char *data, size_t len) {
    while (len > 0) {
        int n = send(s, data, (int)len, 0);
        if (n <= 0) {
            return 0;
        }
        data += n;
        len -= (size_t)n;
    }
    return 1;
}

static size_t read_headers(SOCKET s, char *buf, size_t cap, int *complete) {
    size_t len = 0;
    *complete = 0;
    while (len < cap - 1) {
        int got = recv(s, buf + len, (int)(cap - 1 - len), 0);
        if (got <= 0) {
            break;
        }
        len += (size_t)got;
        buf[len] = '\0';
        if (strstr(buf, "\r\n\r\n")) {
            *complete = 1;
            break;
        }
    }
    return len;
}

static int header_value(const char *headers, const char *name, char *out, size_t cap) {
    const char *p = headers;
    size_t name_len = strlen(name);
    while (p && *p) {
        const char *line_end = strstr(p, "\r\n");
        if (!line_end) {
            break;
        }
        if (_strnicmp(p, name, (int)name_len) == 0 && p[name_len] == ':') {
            const char *v = p + name_len + 1;
            while (*v == ' ') v++;
            size_t n = (size_t)(line_end - v);
            if (n >= cap) n = cap - 1;
            memcpy(out, v, n);
            out[n] = '\0';
            return 1;
        }
        p = line_end + 2;
    }
    return 0;
}

static void parse_request(const char *headers, http_request *req) {
    memset(req, 0, sizeof(*req));
    const char *sp1 = strchr(headers, ' ');
    if (!sp1) {
        return;
    }
    size_t mlen = (size_t)(sp1 - headers);
    if (mlen >= sizeof(req->method)) mlen = sizeof(req->method) - 1;
    memcpy(req->method, headers, mlen);
    req->method[mlen] = '\0';

    const char *start = sp1 + 1;
    const char *sp2 = strchr(start, ' ');
    if (!sp2) {
        return;
    }
    size_t plen = (size_t)(sp2 - start);
    if (plen >= sizeof(req->path)) plen = sizeof(req->path) - 1;
    memcpy(req->path, start, plen);
    req->path[plen] = '\0';

    char *q = strchr(req->path, '?');
    if (q) {
        size_t qlen = strlen(q + 1);
        if (qlen >= sizeof(req->query)) qlen = sizeof(req->query) - 1;
        memcpy(req->query, q + 1, qlen);
        req->query[qlen] = '\0';
        *q = '\0';
    }
}

static void handle_connection(SOCKET s, http_handler handler) {
    char *buf = (char *)malloc(HEADER_MAX);
    if (!buf) {
        closesocket(s);
        return;
    }
    int complete = 0;
    size_t len = read_headers(s, buf, HEADER_MAX, &complete);
    if (!complete) {
        free(buf);
        closesocket(s);
        return;
    }

    http_request req;
    parse_request(buf, &req);

    char tmp[64];
    size_t content_len = 0;
    if (header_value(buf, "Content-Length", tmp, sizeof(tmp))) {
        content_len = (size_t)strtoull(tmp, NULL, 10);
        if (content_len > BODY_MAX) {
            content_len = BODY_MAX;
        }
    }

    const char *body_start = strstr(buf, "\r\n\r\n");
    size_t header_size = body_start ? (size_t)(body_start - buf) + 4 : len;
    size_t have_body = len > header_size ? len - header_size : 0;

    if (content_len > 0) {
        req.body = (char *)malloc(content_len + 1);
        if (req.body) {
            size_t copied = have_body < content_len ? have_body : content_len;
            memcpy(req.body, buf + header_size, copied);
            while (copied < content_len) {
                int got = recv(s, req.body + copied, (int)(content_len - copied), 0);
                if (got <= 0) {
                    break;
                }
                copied += (size_t)got;
            }
            req.body_len = copied;
            req.body[copied] = '\0';
        }
    } else if (have_body > 0) {
        req.body = (char *)malloc(have_body + 1);
        if (req.body) {
            memcpy(req.body, buf + header_size, have_body);
            req.body[have_body] = '\0';
            req.body_len = have_body;
        }
    }
    free(buf);

    http_response res;
    memset(&res, 0, sizeof(res));
    res.status = 404;
    res.content_type = "text/plain; charset=utf-8";
    res.body = "not found";
    res.len = 9;

    handler(&req, &res);

    char head[1024];
    snprintf(head, sizeof(head),
             "HTTP/1.1 %d %s\r\n"
             "Content-Type: %s\r\n"
             "Content-Length: %llu\r\n"
             "Connection: close\r\n"
             "Cache-Control: no-store\r\n"
             "Access-Control-Allow-Origin: *\r\n"
             "\r\n",
             res.status, status_text(res.status), res.content_type,
             (unsigned long long)res.len);
    send_all(s, head, strlen(head));
    if (res.len > 0 && res.body) {
        send_all(s, res.body, res.len);
    }

    free(req.body);
    free(res.body);
    closesocket(s);
}

typedef struct {
    SOCKET sock;
    http_handler handler;
} conn_args;

static DWORD WINAPI conn_thread(LPVOID param) {
    conn_args *args = (conn_args *)param;
    handle_connection(args->sock, args->handler);
    free(args);
    return 0;
}

int http_run(const char *host, int port, http_handler handler) {
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        return 0;
    }
    SOCKET server = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (server == INVALID_SOCKET) {
        WSACleanup();
        return 0;
    }
    BOOL reuse = TRUE;
    setsockopt(server, SOL_SOCKET, SO_REUSEADDR, (const char *)&reuse, sizeof(reuse));

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((u_short)port);
    addr.sin_addr.s_addr = inet_addr(host ? host : "127.0.0.1");

    if (bind(server, (struct sockaddr *)&addr, sizeof(addr)) == SOCKET_ERROR) {
        closesocket(server);
        WSACleanup();
        return 0;
    }
    if (listen(server, SOMAXCONN) == SOCKET_ERROR) {
        closesocket(server);
        WSACleanup();
        return 0;
    }
    printf("rocogi-core listening on http://%s:%d\n", host ? host : "127.0.0.1", port);
    fflush(stdout);

    for (;;) {
        SOCKET client = accept(server, NULL, NULL);
        if (client == INVALID_SOCKET) {
            continue;
        }
        conn_args *args = (conn_args *)malloc(sizeof(conn_args));
        if (!args) {
            closesocket(client);
            continue;
        }
        args->sock = client;
        args->handler = handler;
        HANDLE th = CreateThread(NULL, 0, conn_thread, args, 0, NULL);
        if (th) {
            CloseHandle(th);
        } else {
            conn_thread(args);
        }
    }
}
