#include "static.h"

#include <stdlib.h>
#include <string.h>

#include "host.h"

static const char *mime_for(const char *path) {
    const char *dot = strrchr(path, '.');
    if (!dot) return "application/octet-stream";
    if (_stricmp(dot, ".html") == 0) return "text/html; charset=utf-8";
    if (_stricmp(dot, ".js") == 0) return "text/javascript; charset=utf-8";
    if (_stricmp(dot, ".css") == 0) return "text/css; charset=utf-8";
    if (_stricmp(dot, ".json") == 0) return "application/json; charset=utf-8";
    if (_stricmp(dot, ".png") == 0) return "image/png";
    if (_stricmp(dot, ".jpg") == 0 || _stricmp(dot, ".jpeg") == 0) return "image/jpeg";
    if (_stricmp(dot, ".svg") == 0) return "image/svg+xml";
    if (_stricmp(dot, ".ico") == 0) return "image/x-icon";
    if (_stricmp(dot, ".woff2") == 0) return "font/woff2";
    if (_stricmp(dot, ".map") == 0) return "application/json; charset=utf-8";
    if (_stricmp(dot, ".txt") == 0) return "text/plain; charset=utf-8";
    return "application/octet-stream";
}

int static_serve(const char *root, const char *url_path, http_response *res) {
    if (!root || !url_path) {
        return 0;
    }
    const char *rel = url_path;
    while (*rel == '/') rel++;
    if (strstr(rel, "..")) {
        return 0;
    }
    if (!*rel) {
        rel = "index.html";
    }

    char *full = host_path_join(root, rel);
    if (!full) {
        return 0;
    }
    char *data = NULL;
    size_t len = 0;
    if (!host_read_file(full, &data, &len)) {
        free(full);
        return 0;
    }
    http_reply_alloc(res, 200, mime_for(rel), data, len);
    free(full);
    return 1;
}
