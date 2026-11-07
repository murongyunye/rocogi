#ifndef ROCogi_HOST_H
#define ROCogi_HOST_H

#include <stddef.h>

const char *host_exe_dir(void);
char *host_path_join(const char *a, const char *b);
int host_read_file(const char *path, char **data, size_t *len);
int host_file_exists(const char *path);
long long host_file_size(const char *path);
int host_count_files(const char *dir, const char *ext);

#endif
