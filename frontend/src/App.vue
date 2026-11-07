<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from './components/AppIcon.vue'
import {
  Layout,
  LayoutContent,
  LayoutSider,
  RocoTheme,
  SideNav,
  SideNavHeader,
  SideNavItem,
  SideNavList,
} from './rocoui'
import { appStore, refreshMeta } from './lib/store'
import { api } from './lib/api'
import { toasts, dismiss, notify } from './lib/toast'

const route = useRoute()
const router = useRouter()

const navGroups = [
  {
    label: '开始',
    items: [
      { path: '/launcher', label: '启动', icon: 'play' },
      { path: '/onedragon', label: '一条龙', icon: 'activity' },
      { path: '/realtime', label: '实时任务', icon: 'crosshair' },
    ],
  },
  {
    label: '任务',
    items: [
      { path: '/workflows', label: '独立任务', icon: 'workflow' },
      { path: '/runs', label: '执行记录', icon: 'runs' },
    ],
  },
  {
    label: '工具',
    items: [
      { path: '/tracker', label: '地图追踪', icon: 'target' },
      { path: '/dex', label: '图鉴速查', icon: 'database' },
      { path: '/pet', label: '桌宠工坊', icon: 'spark' },
      { path: '/map', label: '资源地图', icon: 'map' },
      { path: '/battle', label: '对战实验室', icon: 'battle' },
      { path: '/pvp', label: 'PvP 平衡', icon: 'battle' },
      { path: '/resources', label: '资源库', icon: 'resources' },
      { path: '/harness', label: 'AI Harness', icon: 'spark' },
    ],
  },
  {
    label: '配置',
    items: [
      { path: '/engines', label: '引擎参数', icon: 'cpu' },
      { path: '/components', label: '组件图谱', icon: 'node' },
      { path: '/settings', label: '设置', icon: 'settings' },
    ],
  },
]

const activePath = computed(() => {
  if (route.path.startsWith('/workflows')) return '/workflows'
  if (route.path.startsWith('/runs')) return '/runs'
  return route.path
})

const overlayMode = computed(() => route.path === '/pet' && route.query.overlay === '1')

const targetLabel = computed(() => {
  const target = appStore.meta?.target as any
  if (!target) return '检测中'
  if (target.kind === 'windows') return 'Windows 窗口'
  return '模拟目标'
})

function badgeFor(item: { path: string }): number | boolean | undefined {
  if (item.path === '/runs' && appStore.meta?.runCount) return appStore.meta.runCount
  if (item.path === '/workflows' && appStore.meta?.workflowCount) return appStore.meta.workflowCount
  if (item.path === '/realtime' && appStore.meta?.realtime?.running) return true
  if (item.path === '/tracker' && appStore.meta?.tracker?.running) return true
  return undefined
}

function liveTitle(item: { path: string }): string | undefined {
  if (item.path === '/realtime') return '实时任务运行中'
  if (item.path === '/tracker') return '地图追踪运行中'
  return undefined
}

function go(path: string) {
  router.push(path)
}

// --------------------------------------------------------------- 热键（F9/F10/F11）
// 后端 backend/app/hotkeys.py 用 Windows RegisterHotKey 做系统级热键；浏览器端
// 只能拿到页面焦点内的按键，所以这里再做一层同语义的网页热键，方便演示与
// 在 Web 工作台里直接起停实时任务 / 地图追踪（输入框聚焦时不拦截）。
const hotkeyState = reactive({ busy: false, last: '' })

function isTypingTarget(target: EventTarget | null): boolean {
  const node = target as HTMLElement | null
  if (!node || !node.tagName) return false
  const tag = node.tagName.toLowerCase()
  return tag === 'input' || tag === 'textarea' || tag === 'select' || node.isContentEditable
}

async function hotkeyRealtimeStart() {
  if (hotkeyState.busy) return
  hotkeyState.busy = true
  try {
    // 用本机设置里的实时任务配置启动，和 /realtime 页面里保存的一致
    let config: Record<string, unknown> = {}
    try {
      const data = await api<{ settings?: { realtime?: Record<string, unknown> } }>('/api/settings')
      config = data.settings?.realtime || {}
    } catch {
      /* 读不到设置就用后端默认值 */
    }
    await api('/api/realtime/start', { method: 'POST', body: JSON.stringify({ config }) })
    hotkeyState.last = 'F9 启动实时任务'
    notify('F9 · 实时任务已启动', 'success')
    refreshMeta()
  } catch (error) {
    notify(`F9 启动失败：${error}`, 'error')
  } finally {
    hotkeyState.busy = false
  }
}

async function hotkeyStopAll() {
  if (hotkeyState.busy) return
  hotkeyState.busy = true
  try {
    const stopped: string[] = []
    if (appStore.meta?.realtime?.running) {
      await api('/api/realtime/stop', { method: 'POST', body: '{}' })
      stopped.push('实时任务')
    }
    if (appStore.meta?.tracker?.running) {
      await api('/api/tracker/stop', { method: 'POST', body: '{}' })
      stopped.push('地图追踪')
    }
    hotkeyState.last = stopped.length ? `F10 停止${stopped.join(' / ')}` : 'F10 无运行中的会话'
    notify(stopped.length ? `F10 · 已停止${stopped.join(' / ')}` : 'F10 · 当前没有运行中的会话', stopped.length ? 'info' : 'info')
    refreshMeta()
  } catch (error) {
    notify(`F10 停止失败：${error}`, 'error')
  } finally {
    hotkeyState.busy = false
  }
}

async function hotkeyTrackerToggle() {
  if (hotkeyState.busy) return
  hotkeyState.busy = true
  try {
    const running = Boolean(appStore.meta?.tracker?.running)
    const status = (await api<any>(running ? '/api/tracker/stop' : '/api/tracker/start', {
      method: 'POST',
      body: JSON.stringify({ config: {} }),
    })) as any
    hotkeyState.last = running ? 'F11 停止地图追踪' : 'F11 启动地图追踪'
    notify(running ? 'F11 · 地图追踪已停止' : `F11 · 地图追踪${status?.status === 'building' ? '正在建立锚点' : '已启动'}`, 'success')
    refreshMeta()
  } catch (error) {
    notify(`F11 切换追踪失败：${error}`, 'error')
  } finally {
    hotkeyState.busy = false
  }
}

function onHotkey(event: KeyboardEvent) {
  if (event.repeat || event.altKey || event.ctrlKey || event.metaKey) return
  if (isTypingTarget(event.target)) return
  if (overlayMode.value) return
  if (event.key === 'F9') {
    event.preventDefault()
    hotkeyRealtimeStart()
  } else if (event.key === 'F10') {
    event.preventDefault()
    hotkeyStopAll()
  } else if (event.key === 'F11') {
    event.preventDefault()
    hotkeyTrackerToggle()
  }
}

onMounted(() => {
  refreshMeta()
  window.addEventListener('keydown', onHotkey)
  requestAnimationFrame(() => {
    document.querySelector('.rk-side-nav-item.rk-side-nav-item-active')?.scrollIntoView({ block: 'nearest' })
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onHotkey)
})

watch(
  () => route.fullPath,
  () => {
    requestAnimationFrame(() => {
      document.querySelector('.rk-side-nav-item.rk-side-nav-item-active')?.scrollIntoView({ block: 'nearest' })
    })
  },
)
</script>

<template>
  <RocoTheme class="rk-app-root">
    <Layout v-if="!overlayMode" direction="horizontal" full-height class="rk-app-shell">
      <LayoutSider class="app-sider" collapsed-width="64px" width="248px">
        <div class="sider-inner">
          <SideNavHeader icon eyebrow title>
            <template #icon>
              <img class="brand-mark" src="/brand/rocogi-icon-256.png" alt="" aria-hidden="true" />
            </template>
            <template #eyebrow>洛克工坊</template>
            <template #title>Rocogi</template>
          </SideNavHeader>

          <SideNav variant="stack" class="nav-wrap">
            <div v-for="group in navGroups" :key="group.label" class="nav-group">
              <div class="nav-group-label">{{ group.label }}</div>
              <SideNavList>
                <SideNavItem
                  v-for="item in group.items"
                  :key="item.path"
                  icon
                  :active="activePath === item.path"
                  :badge="badgeFor(item)"
                  :title="liveTitle(item)"
                  @click="go(item.path)"
                >
                  <template #icon>
                    <AppIcon :name="item.icon" :size="17" />
                  </template>
                  {{ item.label }}
                </SideNavItem>
              </SideNavList>
            </div>
          </SideNav>
        </div>

        <div class="sidebar-foot">
          <div class="env-card">
            <div class="env-row">
              <span>目标</span>
              <span class="env-value">
                <span class="status-dot" :class="appStore.meta?.target?.kind === 'windows' ? 'succeeded' : 'running'" />
                {{ targetLabel }}
              </span>
            </div>
            <div class="env-row">
              <span>定位</span>
              <span class="env-value">
                <span class="status-dot" :class="appStore.meta?.platform?.sift ? 'succeeded' : 'failed'" />
                SIFT
              </span>
            </div>
            <div class="env-row">
              <span>对战引擎</span>
              <span class="env-value mono">MCTS</span>
            </div>
          </div>
          <div class="hotkey-bar" :title="hotkeyState.last || 'F9 启动实时任务 · F10 停止 · F11 切换地图追踪'">
            <div class="hotkey-row">
              <kbd>F9</kbd>
              <span>启动实时</span>
            </div>
            <div class="hotkey-row">
              <kbd>F10</kbd>
              <span>停止</span>
            </div>
            <div class="hotkey-row">
              <kbd>F11</kbd>
              <span>地图追踪</span>
            </div>
          </div>
          <div class="sidebar-note">
            Rocogi v{{ appStore.meta?.version || '0.1.0' }} · {{ appStore.meta?.map?.pointCount || 0 }} 个点位 ·
            本地优先
          </div>
        </div>
      </LayoutSider>

      <LayoutContent :padded="false" class="app-main">
        <RouterView />
      </LayoutContent>
    </Layout>

    <main v-else class="overlay-main">
      <RouterView />
    </main>

    <div class="toast-stack">
      <div v-for="item in toasts" :key="item.id" class="toast" :class="item.kind" @click="dismiss(item.id)">
        {{ item.message }}
      </div>
    </div>
  </RocoTheme>
</template>

<style scoped>
.rk-app-root {
  height: 100%;
}

.rk-app-shell {
  height: 100%;
}

.app-sider {
  min-width: 0;
}

.sider-inner {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
  padding: 14px 12px 8px;
}

.brand-mark {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  object-fit: contain;
  display: block;
}

.nav-wrap {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  /* The upstream SideNav is authored for a 320px demo sidebar; this workbench
     uses a 248px rail, so the nav stretches to the sider content box. */
  width: 100%;
  max-width: 100%;
  min-width: 0;
  gap: 4px;
}

.sider-inner :deep(.rk-side-nav-header) {
  min-width: 0;
  width: 100%;
  padding: 6px 8px;
}

.sider-inner :deep(.rk-side-nav-header [class*="headerContent"]) {
  min-height: 0;
  gap: 8px;
}

.sider-inner :deep(.rk-side-nav-header [class*="headerIcon"]) {
  font-size: 0;
  width: 30px;
  height: 30px;
}

.sider-inner :deep(.rk-side-nav-header [class*="headerEyebrow"]) {
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  opacity: 0.72;
}

.sider-inner :deep(.rk-side-nav-header [class*="headerTitle"]) {
  font-size: 17px;
  font-weight: 700;
  line-height: 1.1;
}

.nav-wrap :deep(.rk-side-nav-list) {
  gap: 2px;
  width: 100%;
  min-width: 0;
}

.nav-wrap :deep(.rk-side-nav-item) {
  width: 100%;
  min-width: 0;
  height: 32px;
  padding: 0 10px;
  gap: 8px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  background: transparent;
  color: color-mix(in srgb, var(--rk-on-stone) 78%, transparent);
}

.nav-wrap :deep(.rk-side-nav-item:hover) {
  background: color-mix(in srgb, var(--rk-on-stone) 10%, transparent);
  color: var(--rk-on-stone);
}

.nav-wrap :deep(.rk-side-nav-item-active) {
  background: var(--rk-paper);
  color: var(--rk-on-paper);
  font-weight: 600;
}

.nav-wrap :deep(.rk-side-nav-item [class*="itemIcon"]) {
  width: 16px;
  height: 16px;
  font-size: 16px;
  flex: none;
}

.nav-wrap :deep(.rk-side-nav-item [class*="itemLabel"]) {
  flex: 1 1 auto;
  min-width: 0;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-group + .nav-group {
  padding-top: 8px;
}

.nav-group-label {
  padding: 0 10px 4px;
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--rk-on-stone) 45%, transparent);
}

.sidebar-foot {
  flex: none;
  padding: 0 12px 14px;
}

.hotkey-bar {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-bottom: 8px;
  padding: 7px 8px;
  border: 1px solid color-mix(in srgb, var(--rk-on-stone) 12%, transparent);
  border-radius: 7px;
  background: color-mix(in srgb, var(--rk-on-stone) 5%, transparent);
}

.hotkey-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: color-mix(in srgb, var(--rk-on-stone) 62%, transparent);
}

.hotkey-row kbd {
  min-width: 30px;
  padding: 1px 5px;
  border: 1px solid color-mix(in srgb, var(--rk-on-stone) 22%, transparent);
  border-radius: 4px;
  font-family: var(--rk-font-mono, ui-monospace, monospace);
  font-size: 10px;
  line-height: 15px;
  text-align: center;
  background: color-mix(in srgb, var(--rk-on-stone) 10%, transparent);
  color: var(--rk-on-stone);
}

.app-main {
  height: 100%;
  min-width: 0;
}

.app-main.overlay-main {
  overflow: hidden;
}

.overlay-main {
  height: 100%;
}
</style>
