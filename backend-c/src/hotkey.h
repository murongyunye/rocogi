#ifndef ROCogi_HOTKEY_H
#define ROCogi_HOTKEY_H

/* 注册全局热键 F9/F10/F11 并启动监听线程，返回成功注册数量 */
int hotkey_start(void);
void hotkey_stop(void);
/* 最近触发的热键 id：1=start(F9) 2=stop(F10) 3=tracker(F11)，0=无 */
int hotkey_last_id(void);
int hotkey_count(void);
/* 实际注册使用的修饰键：0=无，非 0=Ctrl+Alt（普通 F9-F11 被占用时的降级） */
int hotkey_modifiers(void);

#endif
