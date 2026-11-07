import { reactive } from 'vue'
import { api } from './api'
import type { AppMeta } from '../types'

export const appStore = reactive<{
  meta: AppMeta | null
  loading: boolean
  error: string
}>({
  meta: null,
  loading: true,
  error: '',
})

let inflight: Promise<AppMeta | null> | null = null

export async function refreshMeta(force = false) {
  if (inflight && !force) return inflight
  if (!appStore.meta) appStore.loading = true
  inflight = api<AppMeta>('/api/meta')
    .then((meta) => {
      appStore.meta = meta
      appStore.error = ''
      return meta
    })
    .catch((error) => {
      appStore.error = String(error)
      return null
    })
    .finally(() => {
      appStore.loading = false
      inflight = null
    })
  return inflight
}
