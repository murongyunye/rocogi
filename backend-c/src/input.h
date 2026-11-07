#ifndef ROCogi_INPUT_H
#define ROCogi_INPUT_H

#include <windows.h>

/* window_mode: 0=屏幕绝对坐标 1=窗口相对坐标 */
int input_move(int x, int y, int window_mode, HWND hwnd, int duration_ms);
int input_click(int x, int y, int window_mode, HWND hwnd, int button, int clicks);
int input_key(const char *combo);
int input_type_text(const char *utf8_text);
int input_wheel(int delta);
int input_focus_window(HWND hwnd);
int input_clipboard_text(const char *utf8_text);
int input_paste(void);

/* 输入文本：纯 ASCII 走 SendInput Unicode；含中文/CJK 走剪贴板 + Ctrl+V 降级 */
int input_text_any(const char *utf8_text);

#endif
