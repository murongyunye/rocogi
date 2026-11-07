#include "host.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

const char *host_exe_dir(void) {
    static char dir[MAX_PATH];
    static int ready = 0;
    if (!ready) {
        char full[MAX_PATH];
        DWORD n = GetModuleFileNameA(NULL, full, MAX_PATH);
        if (n == 0) {
            strcpy(dir, ".");
        } else {
            char *slash = strrchr(full, '\\');
            if (slash) {
                *slash = '\0';
            }
            strncpy(dir, full, MAX_PATH - 1);
            dir[MAX_PATH - 1] = '\0';
        }
        ready = 1;
    }
    return dir;
}

char *host_path_join(const char *a, const char *b) {
    if (!a) a = "";
    if (!b) b = "";
    size_t na = strlen(a), nb = strlen(b);
    int need_sep = na > 0 && (a[na - 1] != '\\' && a[na - 1] != '/') && (b[0] != '\\' && b[0] != '/');
    char *out = (char *)malloc(na + nb + 3);
    if (!out) {
        return NULL;
    }
    memcpy(out, a, na);
    size_t k = na;
    if (need_sep) {
        out[k++] = '\\';
    }
    memcpy(out + k, b, nb);
    out[k + nb] = '\0';
    return out;
}

int host_read_file(const char *path, char **data, size_t *len) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        return 0;
    }
    long size = -1;
    if (fseek(f, 0, SEEK_END) == 0) {
        size = ftell(f);
        if (size >= 0 && fseek(f, 0, SEEK_SET) == 0) {
            char *buf = (char *)malloc((size_t)size + 1);
            if (!buf) {
                fclose(f);
                return 0;
            }
            size_t got = size > 0 ? fread(buf, 1, (size_t)size, f) : 0;
            buf[got] = '\0';
            fclose(f);
            *data = buf;
            if (len) {
                *len = got;
            }
            return 1;
        }
    }
    fclose(f);
    return 0;
}

int host_file_exists(const char *path) {
    DWORD attr = GetFileAttributesA(path);
    return attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY);
}

long long host_file_size(const char *path) {
    WIN32_FILE_ATTRIBUTE_DATA info;
    if (!GetFileAttributesExA(path, GetFileExInfoStandard, &info)) {
        return -1;
    }
    return (long long)info.nFileSizeLow;
}

int host_count_files(const char *dir, const char *ext) {
    char pattern[MAX_PATH];
    snprintf(pattern, sizeof(pattern), "%s\\*.%s", dir, ext);
    WIN32_FIND_DATAA fd;
    HANDLE h = FindFirstFileA(pattern, &fd);
    if (h == INVALID_HANDLE_VALUE) {
        return 0;
    }
    int count = 0;
    do {
        if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
            count++;
        }
    } while (FindNextFileA(h, &fd));
    FindClose(h);
    return count;
}
