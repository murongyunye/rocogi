#ifndef ROCogi_PNGIO_H
#define ROCogi_PNGIO_H

/* 写 BGRA 像素为 PNG；成功返回 1 */
int png_write_bgra(const char *path, int width, int height, const unsigned char *bgra);

/* 读取图片并转换为灰度（8 位），失败返回 NULL；调用方 free */
unsigned char *img_load_gray(const char *path, int *width, int *height);

#endif
