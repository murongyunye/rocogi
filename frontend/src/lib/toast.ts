import { reactive } from 'vue'

export interface ToastItem {
  id: number
  message: string
  kind: 'info' | 'success' | 'error'
}

export const toasts = reactive<ToastItem[]>([])

let nextId = 1

export function notify(message: string, kind: ToastItem['kind'] = 'info') {
  const id = nextId++
  toasts.push({ id, message, kind })
  window.setTimeout(() => dismiss(id), kind === 'error' ? 6000 : 3200)
}

export function dismiss(id: number) {
  const index = toasts.findIndex((item) => item.id === id)
  if (index >= 0) toasts.splice(index, 1)
}
