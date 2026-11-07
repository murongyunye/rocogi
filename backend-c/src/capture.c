#include "capture.h"

#include <d3d11.h>
#include <dxgi1_2.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pngio.h"

#ifndef PW_RENDERFULLCONTENT
#define PW_RENDERFULLCONTENT 0x00000002
#endif

static ID3D11Device *g_dev = NULL;
static ID3D11DeviceContext *g_ctx = NULL;
static IDXGIOutputDuplication *g_dup = NULL;
static int g_dxgi_failed = 0;

static double now_ms(void) {
    LARGE_INTEGER freq, counter;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&counter);
    return (double)counter.QuadPart * 1000.0 / (double)freq.QuadPart;
}

static void dxgi_reset(void) {
    if (g_dup) {
        g_dup->lpVtbl->Release(g_dup);
        g_dup = NULL;
    }
    if (g_ctx) {
        g_ctx->lpVtbl->Release(g_ctx);
        g_ctx = NULL;
    }
    if (g_dev) {
        g_dev->lpVtbl->Release(g_dev);
        g_dev = NULL;
    }
}

static int dxgi_init(void) {
    if (g_dup) {
        return 1;
    }
    if (g_dxgi_failed) {
        return 0;
    }
    D3D_FEATURE_LEVEL levels[] = {
        D3D_FEATURE_LEVEL_11_0, D3D_FEATURE_LEVEL_10_1,
        D3D_FEATURE_LEVEL_10_0, D3D_FEATURE_LEVEL_9_1};
    D3D_FEATURE_LEVEL got;
    HRESULT hr = D3D11CreateDevice(NULL, D3D_DRIVER_TYPE_HARDWARE, NULL,
                                   D3D11_CREATE_DEVICE_BGRA_SUPPORT, levels, 4,
                                   D3D11_SDK_VERSION, &g_dev, &got, &g_ctx);
    if (FAILED(hr) || !g_dev || !g_ctx) {
        g_dxgi_failed = 1;
        return 0;
    }
    IDXGIDevice *dxgi_dev = NULL;
    if (FAILED(g_dev->lpVtbl->QueryInterface(g_dev, &IID_IDXGIDevice, (void **)&dxgi_dev)) || !dxgi_dev) {
        dxgi_reset();
        g_dxgi_failed = 1;
        return 0;
    }
    IDXGIAdapter *adapter = NULL;
    dxgi_dev->lpVtbl->GetAdapter(dxgi_dev, &adapter);
    dxgi_dev->lpVtbl->Release(dxgi_dev);
    if (!adapter) {
        dxgi_reset();
        g_dxgi_failed = 1;
        return 0;
    }
    IDXGIOutput *output = NULL;
    adapter->lpVtbl->EnumOutputs(adapter, 0, &output);
    adapter->lpVtbl->Release(adapter);
    if (!output) {
        dxgi_reset();
        g_dxgi_failed = 1;
        return 0;
    }
    IDXGIOutput1 *output1 = NULL;
    output->lpVtbl->QueryInterface(output, &IID_IDXGIOutput1, (void **)&output1);
    output->lpVtbl->Release(output);
    if (!output1) {
        dxgi_reset();
        g_dxgi_failed = 1;
        return 0;
    }
    hr = output1->lpVtbl->DuplicateOutput(output1, (IUnknown *)g_dev, &g_dup);
    output1->lpVtbl->Release(output1);
    if (FAILED(hr) || !g_dup) {
        dxgi_reset();
        g_dxgi_failed = 1;
        return 0;
    }
    return 1;
}

static int dxgi_grab(capture_result *out) {
    if (!dxgi_init()) {
        return 0;
    }
    double t0 = now_ms();
    IDXGIResource *res = NULL;
    DXGI_OUTDUPL_FRAME_INFO info;
    HRESULT hr = E_FAIL;
    for (int attempt = 0; attempt < 8 && !res; ++attempt) {
        memset(&info, 0, sizeof(info));
        hr = g_dup->lpVtbl->AcquireNextFrame(g_dup, 120, &info, &res);
        if (hr == S_OK) {
            break;
        }
        if (hr == DXGI_ERROR_WAIT_TIMEOUT) {
            continue;
        }
        dxgi_reset();
        g_dxgi_failed = 1;
        return 0;
    }
    if (!res) {
        return 0;
    }

    ID3D11Texture2D *tex = NULL;
    if (FAILED(res->lpVtbl->QueryInterface(res, &IID_ID3D11Texture2D, (void **)&tex)) || !tex) {
        g_dup->lpVtbl->ReleaseFrame(g_dup);
        res->lpVtbl->Release(res);
        return 0;
    }
    res->lpVtbl->Release(res);

    D3D11_TEXTURE2D_DESC desc;
    tex->lpVtbl->GetDesc(tex, &desc);
    desc.Usage = D3D11_USAGE_STAGING;
    desc.BindFlags = 0;
    desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    desc.MiscFlags = 0;

    ID3D11Texture2D *staging = NULL;
    if (FAILED(g_dev->lpVtbl->CreateTexture2D(g_dev, &desc, NULL, &staging)) || !staging) {
        tex->lpVtbl->Release(tex);
        g_dup->lpVtbl->ReleaseFrame(g_dup);
        return 0;
    }
    g_ctx->lpVtbl->CopyResource(g_ctx, (ID3D11Resource *)staging, (ID3D11Resource *)tex);

    D3D11_MAPPED_SUBRESOURCE mapped;
    memset(&mapped, 0, sizeof(mapped));
    if (FAILED(g_ctx->lpVtbl->Map(g_ctx, (ID3D11Resource *)staging, 0, D3D11_MAP_READ, 0, &mapped))) {
        staging->lpVtbl->Release(staging);
        tex->lpVtbl->Release(tex);
        if (g_dup) g_dup->lpVtbl->ReleaseFrame(g_dup);
        return 0;
    }

    int w = (int)desc.Width;
    int h = (int)desc.Height;
    unsigned char *buf = (unsigned char *)malloc((size_t)w * (size_t)h * 4);
    if (buf) {
        for (int y = 0; y < h; ++y) {
            memcpy(buf + (size_t)y * w * 4,
                   (unsigned char *)mapped.pData + (size_t)y * mapped.RowPitch,
                   (size_t)w * 4);
        }
        out->width = w;
        out->height = h;
        out->bgra = buf;
        out->method = 1;
        out->method_name = "dxgi";
        snprintf(out->note, sizeof(out->note), "IDXGIOutputDuplication");
        out->ms = now_ms() - t0;
    }
    g_ctx->lpVtbl->Unmap(g_ctx, (ID3D11Resource *)staging, 0);
    staging->lpVtbl->Release(staging);
    tex->lpVtbl->Release(tex);
    if (g_dup) g_dup->lpVtbl->ReleaseFrame(g_dup);
    return buf != NULL;
}

/* 采样判断位图是否近似纯色（空白） */
static int looks_blank(const unsigned char *bgra, int w, int h) {
    if (!bgra || w <= 0 || h <= 0) {
        return 1;
    }
    int min_l = 255, max_l = 0;
    for (int y = 0; y < 32; ++y) {
        int py = (int)((long long)y * (h - 1) / 31);
        for (int x = 0; x < 32; ++x) {
            int px = (int)((long long)x * (w - 1) / 31);
            const unsigned char *p = bgra + ((size_t)py * w + px) * 4;
            int l = (p[2] * 30 + p[1] * 59 + p[0] * 11) / 100;
            if (l < min_l) min_l = l;
            if (l > max_l) max_l = l;
        }
    }
    return (max_l - min_l) < 4;
}

static int print_window(HWND hwnd, capture_result *out) {
    RECT rc;
    if (!GetWindowRect(hwnd, &rc)) {
        return 0;
    }
    int w = rc.right - rc.left;
    int h = rc.bottom - rc.top;
    if (w <= 0 || h <= 0) {
        return 0;
    }
    double t0 = now_ms();
    HDC screen = GetDC(NULL);
    HDC mem = CreateCompatibleDC(screen);
    BITMAPINFO bi;
    memset(&bi, 0, sizeof(bi));
    bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bi.bmiHeader.biWidth = w;
    bi.bmiHeader.biHeight = -h; /* 自上而下 */
    bi.bmiHeader.biPlanes = 1;
    bi.bmiHeader.biBitCount = 32;
    bi.bmiHeader.biCompression = BI_RGB;
    void *bits = NULL;
    HBITMAP bmp = CreateDIBSection(mem, &bi, DIB_RGB_COLORS, &bits, NULL, 0);
    if (!bmp || !bits) {
        DeleteDC(mem);
        ReleaseDC(NULL, screen);
        return 0;
    }
    HGDIOBJ old = SelectObject(mem, bmp);
    BOOL ok = PrintWindow(hwnd, mem, PW_RENDERFULLCONTENT);
    GdiFlush();
    unsigned char *buf = NULL;
    if (ok) {
        buf = (unsigned char *)malloc((size_t)w * (size_t)h * 4);
        if (buf) {
            memcpy(buf, bits, (size_t)w * (size_t)h * 4);
        }
    }
    SelectObject(mem, old);
    DeleteObject(bmp);
    DeleteDC(mem);
    ReleaseDC(NULL, screen);
    if (!buf) {
        return 0;
    }
    out->width = w;
    out->height = h;
    out->bgra = buf;
    out->method = 2;
    out->method_name = "printwindow";
    snprintf(out->note, sizeof(out->note),
             "PrintWindow(PW_RENDERFULLCONTENT)%s", looks_blank(buf, w, h) ? "（疑似空白，窗口可能已最小化）" : "");
    out->ms = now_ms() - t0;
    return 1;
}

static int bitblt_window(HWND hwnd, capture_result *out) {
    RECT rc;
    if (!GetWindowRect(hwnd, &rc)) {
        return 0;
    }
    int w = rc.right - rc.left;
    int h = rc.bottom - rc.top;
    if (w <= 0 || h <= 0) {
        return 0;
    }
    double t0 = now_ms();
    HDC wdc = GetWindowDC(hwnd);
    if (!wdc) {
        return 0;
    }
    HDC mem = CreateCompatibleDC(wdc);
    BITMAPINFO bi;
    memset(&bi, 0, sizeof(bi));
    bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bi.bmiHeader.biWidth = w;
    bi.bmiHeader.biHeight = -h;
    bi.bmiHeader.biPlanes = 1;
    bi.bmiHeader.biBitCount = 32;
    bi.bmiHeader.biCompression = BI_RGB;
    void *bits = NULL;
    HBITMAP bmp = CreateDIBSection(mem, &bi, DIB_RGB_COLORS, &bits, NULL, 0);
    if (!bmp || !bits) {
        DeleteDC(mem);
        ReleaseDC(hwnd, wdc);
        return 0;
    }
    HGDIOBJ old = SelectObject(mem, bmp);
    BOOL ok = BitBlt(mem, 0, 0, w, h, wdc, 0, 0, SRCCOPY);
    GdiFlush();
    unsigned char *buf = NULL;
    if (ok) {
        buf = (unsigned char *)malloc((size_t)w * (size_t)h * 4);
        if (buf) {
            memcpy(buf, bits, (size_t)w * (size_t)h * 4);
        }
    }
    SelectObject(mem, old);
    DeleteObject(bmp);
    DeleteDC(mem);
    ReleaseDC(hwnd, wdc);
    if (!buf) {
        return 0;
    }
    out->width = w;
    out->height = h;
    out->bgra = buf;
    out->method = 3;
    out->method_name = "bitblt";
    snprintf(out->note, sizeof(out->note),
             "BitBlt(窗口 DC)%s", looks_blank(buf, w, h) ? "（疑似空白，窗口可能被遮挡或最小化）" : "");
    out->ms = now_ms() - t0;
    return 1;
}

static int gdi_desktop(capture_result *out) {
    double t0 = now_ms();
    int w = GetSystemMetrics(SM_CXSCREEN);
    int h = GetSystemMetrics(SM_CYSCREEN);
    HDC screen = GetDC(NULL);
    HDC mem = CreateCompatibleDC(screen);
    BITMAPINFO bi;
    memset(&bi, 0, sizeof(bi));
    bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bi.bmiHeader.biWidth = w;
    bi.bmiHeader.biHeight = -h;
    bi.bmiHeader.biPlanes = 1;
    bi.bmiHeader.biBitCount = 32;
    bi.bmiHeader.biCompression = BI_RGB;
    void *bits = NULL;
    HBITMAP bmp = CreateDIBSection(mem, &bi, DIB_RGB_COLORS, &bits, NULL, 0);
    if (!bmp || !bits) {
        DeleteDC(mem);
        ReleaseDC(NULL, screen);
        return 0;
    }
    HGDIOBJ old = SelectObject(mem, bmp);
    BOOL ok = BitBlt(mem, 0, 0, w, h, screen, 0, 0, SRCCOPY);
    GdiFlush();
    unsigned char *buf = NULL;
    if (ok) {
        buf = (unsigned char *)malloc((size_t)w * (size_t)h * 4);
        if (buf) {
            memcpy(buf, bits, (size_t)w * (size_t)h * 4);
        }
    }
    SelectObject(mem, old);
    DeleteObject(bmp);
    DeleteDC(mem);
    ReleaseDC(NULL, screen);
    if (!buf) {
        return 0;
    }
    out->width = w;
    out->height = h;
    out->bgra = buf;
    out->method = 4;
    out->method_name = "gdi";
    snprintf(out->note, sizeof(out->note), "BitBlt(桌面 DC)");
    out->ms = now_ms() - t0;
    return 1;
}

/* 从桌面帧中裁出窗口区域 */
static int crop_from_desktop(HWND hwnd, capture_result *out) {
    RECT rc;
    if (!GetWindowRect(hwnd, &rc)) {
        return 0;
    }
    int w = rc.right - rc.left;
    int h = rc.bottom - rc.top;
    if (w <= 0 || h <= 0) {
        return 0;
    }
    capture_result desk;
    memset(&desk, 0, sizeof(desk));
    if (!dxgi_grab(&desk)) {
        return 0;
    }
    if (rc.left < 0 || rc.top < 0 || rc.right > desk.width || rc.bottom > desk.height) {
        capture_free(&desk);
        return 0;
    }
    unsigned char *buf = (unsigned char *)malloc((size_t)w * (size_t)h * 4);
    if (!buf) {
        capture_free(&desk);
        return 0;
    }
    for (int y = 0; y < h; ++y) {
        memcpy(buf + (size_t)y * w * 4,
               desk.bgra + ((size_t)(rc.top + y) * desk.width + rc.left) * 4,
               (size_t)w * 4);
    }
    out->width = w;
    out->height = h;
    out->bgra = buf;
    out->method = 1;
    out->method_name = "dxgi";
    snprintf(out->note, sizeof(out->note), "DXGI 桌面帧裁剪（窗口需可见且未被遮挡）");
    out->ms = desk.ms;
    capture_free(&desk);
    return 1;
}

int capture_window(HWND hwnd, capture_result *out) {
    memset(out, 0, sizeof(*out));
    if (!hwnd || !IsWindow(hwnd)) {
        return 0;
    }
    if (print_window(hwnd, out)) {
        return 1;
    }
    if (crop_from_desktop(hwnd, out)) {
        return 1;
    }
    if (bitblt_window(hwnd, out)) {
        return 1;
    }
    return 0;
}

int capture_window_bitblt(HWND hwnd, capture_result *out) {
    memset(out, 0, sizeof(*out));
    if (!hwnd || !IsWindow(hwnd)) {
        return 0;
    }
    return bitblt_window(hwnd, out);
}

int capture_desktop(capture_result *out) {
    memset(out, 0, sizeof(*out));
    if (dxgi_grab(out)) {
        return 1;
    }
    return gdi_desktop(out);
}

void capture_free(capture_result *out) {
    if (!out) return;
    free(out->bgra);
    out->bgra = NULL;
    out->width = 0;
    out->height = 0;
}

int capture_save_png(const capture_result *cap, const char *path) {
    if (!cap || !cap->bgra) {
        return 0;
    }
    return png_write_bgra(path, cap->width, cap->height, cap->bgra);
}

int capture_is_blank(const capture_result *cap) {
    if (!cap || !cap->bgra) {
        return 1;
    }
    return looks_blank(cap->bgra, cap->width, cap->height);
}

double capture_diff(const capture_result *a, const capture_result *b) {
    if (!a || !b || !a->bgra || !b->bgra) {
        return -1;
    }
    if (a->width != b->width || a->height != b->height) {
        return -1;
    }
    size_t count = (size_t)a->width * (size_t)a->height;
    unsigned long long sum = 0;
    for (size_t i = 0; i < count; ++i) {
        const unsigned char *pa = a->bgra + i * 4;
        const unsigned char *pb = b->bgra + i * 4;
        int d0 = pa[0] > pb[0] ? pa[0] - pb[0] : pb[0] - pa[0];
        int d1 = pa[1] > pb[1] ? pa[1] - pb[1] : pb[1] - pa[1];
        int d2 = pa[2] > pb[2] ? pa[2] - pb[2] : pb[2] - pa[2];
        sum += (unsigned long long)((d0 + d1 + d2) / 3);
    }
    return (double)sum / (double)count;
}
