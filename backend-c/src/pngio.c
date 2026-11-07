#include "pngio.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#define STBI_NO_STDIO
#include "stb_image.h"

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

int png_write_bgra(const char *path, int width, int height, const unsigned char *bgra) {
    if (width <= 0 || height <= 0 || !bgra) {
        return 0;
    }
    size_t count = (size_t)width * (size_t)height;
    unsigned char *rgba = (unsigned char *)malloc(count * 4);
    if (!rgba) {
        return 0;
    }
    for (size_t i = 0; i < count; ++i) {
        rgba[i * 4 + 0] = bgra[i * 4 + 2];
        rgba[i * 4 + 1] = bgra[i * 4 + 1];
        rgba[i * 4 + 2] = bgra[i * 4 + 0];
        rgba[i * 4 + 3] = bgra[i * 4 + 3] ? bgra[i * 4 + 3] : 255;
    }
    int ok = stbi_write_png(path, width, height, 4, rgba, width * 4);
    free(rgba);
    return ok;
}

unsigned char *img_load_gray(const char *path, int *width, int *height) {
    int w = 0, h = 0, comp = 0;
    /* 先读原始字节，再交给内存解码，避免 stb 的 stdio 分支 */
    FILE *f = fopen(path, "rb");
    if (!f) {
        return NULL;
    }
    long size = -1;
    if (fseek(f, 0, SEEK_END) == 0) {
        size = ftell(f);
        if (size > 0 && fseek(f, 0, SEEK_SET) == 0) {
            unsigned char *raw = (unsigned char *)malloc((size_t)size);
            if (raw) {
                size_t got = fread(raw, 1, (size_t)size, f);
                unsigned char *pixels = stbi_load_from_memory(raw, (int)got, &w, &h, &comp, 1);
                free(raw);
                if (pixels) {
                    *width = w;
                    *height = h;
                    fclose(f);
                    return pixels;
                }
            }
        }
    }
    fclose(f);
    return NULL;
}
