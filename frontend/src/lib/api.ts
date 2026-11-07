const BASE = (import.meta as Record<string, any>).env?.VITE_API_BASE ?? ''

export class ApiError extends Error {
  status: number
  payload: any

  constructor(status: number, payload: any) {
    super(typeof payload === 'string' ? payload : payload?.message || payload?.detail?.message || '请求失败')
    this.status = status
    this.payload = payload
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
    ...init,
  })
  const text = await response.text()
  let payload: any = text
  try {
    payload = text ? JSON.parse(text) : {}
  } catch {
    /* keep text */
  }
  if (!response.ok) {
    throw new ApiError(response.status, payload)
  }
  return payload as T
}

export function wsUrl(path: string): string {
  if (BASE) {
    const url = new URL(BASE, window.location.href)
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${url.host}${path}`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${path}`
}

export function assetUrl(path?: string | null): string {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${BASE}${path}`
}

export function formatTime(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

export function formatDuration(ms?: number | null): string {
  if (!ms || ms < 0) return '—'
  if (ms < 1000) return `${ms} ms`
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toFixed(1)} s`
  return `${Math.floor(seconds / 60)} m ${Math.floor(seconds % 60)} s`
}
