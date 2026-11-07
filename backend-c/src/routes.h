#ifndef ROCogi_ROUTES_H
#define ROCogi_ROUTES_H

#include "http.h"

void routes_init(const char *root, const char *data_dir, const char *static_dir, const char *workflows_dir);
void routes_handle(const http_request *req, http_response *res);

#endif
