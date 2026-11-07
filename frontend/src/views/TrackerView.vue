<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../lib/api'
import { refreshMeta } from '../lib/store'
import { notify } from '../lib/toast'
import type { RoutePlan, TrackerStatus } from '../types'

const status = ref<TrackerStatus | null>(null)
const route = ref<RoutePlan | null>(null)
const routeBusy = ref(false)
const routePresets = [
  { id: 'chest', label: '宝箱路线', labels: '宝箱', categories: '' },
  { id: 'gather', label: '植物 + 矿物', labels: '', categories: '植物,矿物' },
  { id: 'spirit', label: '精灵踪迹', labels: '精灵踪迹', categories: '' },
  { id: 'collect', label: '收集路线', labels: '', categories: '收集' },
]
const config = reactive({ interval: 0.5, confidenceMin: 0.25, screenshotEvery: 2 })
const busy = ref(false)
const follow = ref(true)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const wrapRef = ref<HTMLDivElement | null>(null)
const view = reactive({ x: 0, y: 0, scale: 0.22 })
const spatial = reactive({ width: 0, height: 0 })
const image = ref<HTMLImageElement | null>(null)
let ctx: CanvasRenderingContext2D | null = null
let raf = 0
let timer = 0
let resizeObserver: ResizeObserver | null = null
let dragState: { x: number; y: number; ox: number; oy: number; moved: boolean } | null = null

const MAP_W = 6144
const MAP_H = 5888

const current = computed(() => status.value?.current || null)
const trail = computed(() => status.value?.trail || [])
const statusText = computed(() => {
  if (!status.value) return '加载中'
  if (status.value.rebuilding) return '重建锚点'
  if (status.value.status === 'building') return '建立锚点'
  if (status.value.status === 'running') return '追踪中'
  if (status.value.status === 'error') return '出错'
  return '待启动'
})
const statusClass = computed(() => (status.value?.running ? 'running' : status.value?.status === 'error' ? 'failed' : 'idle'))

async function load() {
  try {
    const data = await api<TrackerStatus>('/api/tracker/status')
    status.value = data
    if (data.config) Object.assign(config, data.config)
  } catch (error) {
    notify(`读取追踪状态失败：${error}`, 'error')
  }
}

async function poll() {
  try {
    const data = await api<TrackerStatus>('/api/tracker/status')
    const previousCount = trail.value.length
    status.value = data
    if (!follow.value) return
    if (data.current && (!previousCount || data.status === 'running')) {
      centerOn(data.current.x, data.current.y)
    }
  } catch {
    /* keep last */
  }
}

async function start() {
  busy.value = true
  try {
    status.value = await api<TrackerStatus>('/api/tracker/start', {
      method: 'POST',
      body: JSON.stringify({ config }),
    })
    follow.value = true
    notify('地图追踪已启动，首次定位需要建立 SIFT 锚点', 'success')
    refreshMeta()
  } catch (error) {
    notify(`启动追踪失败：${error}`, 'error')
  } finally {
    busy.value = false
  }
}

async function stop() {
  busy.value = true
  try {
    status.value = await api<TrackerStatus>('/api/tracker/stop', { method: 'POST', body: '{}' })
    notify('地图追踪已停止', 'info')
    refreshMeta()
  } catch (error) {
    notify(`停止失败：${error}`, 'error')
  } finally {
    busy.value = false
  }
}

async function rebuild() {
  busy.value = true
  const startedAt = performance.now()
  try {
    await api('/api/tracker/anchors/rebuild', { method: 'POST', body: '{}' })
    notify('正在重建 SIFT 锚点，正在重新提取特征点…', 'info')
    // 后端把重建放在后台线程里，这里等到 rebuilding 结束，再把锚点数量反馈给用户。
    for (let i = 0; i < 60; i += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 500))
      await poll()
      if (status.value && !status.value.rebuilding) break
    }
    const anchor = status.value?.anchor
    if (status.value?.status === 'error') {
      notify(`重建锚点失败：${status.value.error || '未知错误'}`, 'error')
    } else {
      const elapsed = ((performance.now() - startedAt) / 1000).toFixed(1)
      notify(`锚点已重建 · ${anchor?.points || 0} 个特征点 · ${elapsed}s`, 'success')
    }
    refreshMeta()
  } catch (error) {
    notify(`重建锚点失败：${error}`, 'error')
  } finally {
    busy.value = false
  }
}

async function planPreset(preset: { label: string; labels: string; categories: string }) {
  routeBusy.value = true
  try {
    const start = current.value ? { x: current.value.x, y: current.value.y } : { x: 3072, y: 2944 }
    const plan = await api<RoutePlan>('/api/map/route', {
      method: 'POST',
      body: JSON.stringify({
        start,
        labels: preset.labels ? preset.labels.split(',') : [],
        categories: preset.categories ? preset.categories.split(',') : [],
        limit: 12,
      }),
    })
    route.value = plan
    notify(`${preset.label} · ${plan.count} 个点位 · ${plan.distancePx} px`, 'success')
    fitRoute(plan)
  } catch (error) {
    notify(`规划路线失败：${error}`, 'error')
  } finally {
    routeBusy.value = false
  }
}

function fitRoute(plan: RoutePlan) {
  const wrap = wrapRef.value
  if (!wrap || !plan.route.length) return
  const xs = [plan.start.x, ...plan.route.map((point) => point.x)]
  const ys = [plan.start.y, ...plan.route.map((point) => point.y)]
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const pad = 70
  const scale = Math.min(
    (wrap.clientWidth - pad * 2) / Math.max(maxX - minX, 500),
    (wrap.clientHeight - pad * 2) / Math.max(maxY - minY, 500),
    0.42,
  )
  view.scale = Math.max(0.1, scale)
  view.x = wrap.clientWidth / 2 - ((minX + maxX) / 2) * view.scale
  view.y = wrap.clientHeight / 2 - ((minY + maxY) / 2) * view.scale
  scheduleDraw()
}

function clearRoute() {
  route.value = null
  scheduleDraw()
}

// ------------------------------------------------------------------- canvas
function resize() {
  const wrap = wrapRef.value
  const canvas = canvasRef.value
  if (!wrap || !canvas) return
  const dpr = window.devicePixelRatio || 1
  spatial.width = wrap.clientWidth
  spatial.height = wrap.clientHeight
  canvas.width = Math.round(wrap.clientWidth * dpr)
  canvas.height = Math.round(wrap.clientHeight * dpr)
  canvas.style.width = `${wrap.clientWidth}px`
  canvas.style.height = `${wrap.clientHeight}px`
  ctx = canvas.getContext('2d')
  if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  scheduleDraw()
}

function fitMap() {
  const wrap = wrapRef.value
  if (!wrap) return
  view.scale = Math.min(wrap.clientWidth / MAP_W, wrap.clientHeight / MAP_H) * 0.95
  view.x = (wrap.clientWidth - MAP_W * view.scale) / 2
  view.y = (wrap.clientHeight - MAP_H * view.scale) / 2
  scheduleDraw()
}

function centerOn(x: number, y: number, scale = Math.max(view.scale, 0.2)) {
  const wrap = wrapRef.value
  if (!wrap) return
  view.scale = Math.min(0.36, Math.max(0.14, scale))
  view.x = wrap.clientWidth / 2 - x * view.scale
  view.y = wrap.clientHeight / 2 - y * view.scale
  scheduleDraw()
}

function scheduleDraw() {
  if (raf) return
  raf = window.requestAnimationFrame(() => {
    raf = 0
    draw()
  })
}

function draw() {
  const canvas = canvasRef.value
  if (!ctx || !canvas) return
  const width = spatial.width
  const height = spatial.height
  ctx.clearRect(0, 0, width, height)
  const gradient = ctx.createLinearGradient(0, 0, 0, height)
  gradient.addColorStop(0, '#eef8ff')
  gradient.addColorStop(1, '#f4fbff')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, width, height)

  if (image.value) {
    ctx.save()
    ctx.globalAlpha = 0.88
    ctx.drawImage(image.value, view.x, view.y, MAP_W * view.scale, MAP_H * view.scale)
    ctx.restore()
  }

  const points = trail.value
  if (points.length) {
    ctx.beginPath()
    ctx.strokeStyle = 'rgba(14, 165, 233, 0.55)'
    ctx.lineWidth = 1.6
    ctx.shadowColor = 'rgba(14, 165, 233, 0.45)'
    ctx.shadowBlur = 8
    points.forEach((point, index) => {
      const sx = view.x + point.x * view.scale
      const sy = view.y + point.y * view.scale
      if (index === 0) ctx.moveTo(sx, sy)
      else ctx.lineTo(sx, sy)
    })
    ctx.stroke()
    ctx.shadowBlur = 0
    points.slice(-40).forEach((point, index, list) => {
      const sx = view.x + point.x * view.scale
      const sy = view.y + point.y * view.scale
      ctx.beginPath()
      ctx.fillStyle = `rgba(14, 165, 233, ${0.08 + (index / Math.max(list.length, 1)) * 0.5})`
      ctx.arc(sx, sy, 2, 0, Math.PI * 2)
      ctx.fill()
    })
  }

  if (current.value) {
    const sx = view.x + current.value.x * view.scale
    const sy = view.y + current.value.y * view.scale
    ctx.beginPath()
    ctx.strokeStyle = 'rgba(251, 191, 36, 0.55)'
    ctx.lineWidth = 1
    ctx.arc(sx, sy, 14, 0, Math.PI * 2)
    ctx.stroke()
    ctx.beginPath()
    ctx.fillStyle = '#ffd166'
    ctx.arc(sx, sy, 6, 0, Math.PI * 2)
    ctx.fill()
    ctx.beginPath()
    ctx.fillStyle = '#082f49'
    ctx.arc(sx, sy, 2, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = 'rgba(255, 224, 140, 0.9)'
    ctx.font = '10px "JetBrains Mono", monospace'
    ctx.textAlign = 'left'
    ctx.fillText(`(${Math.round(current.value.x)}, ${Math.round(current.value.y)})`, sx + 16, sy + 4)
  }

  if (route.value?.route?.length) {
    ctx.save()
    ctx.beginPath()
    ctx.strokeStyle = 'rgba(251, 191, 36, 0.82)'
    ctx.lineWidth = 1.8
    ctx.setLineDash([5, 4])
    route.value.route.forEach((point, index) => {
      const sx = view.x + point.x * view.scale
      const sy = view.y + point.y * view.scale
      if (index === 0) ctx.moveTo(sx, sy)
      else ctx.lineTo(sx, sy)
    })
    ctx.stroke()
    ctx.setLineDash([])
    route.value.route.forEach((point, index) => {
      const sx = view.x + point.x * view.scale
      const sy = view.y + point.y * view.scale
      ctx.beginPath()
      ctx.fillStyle = '#e6f7ff'
      ctx.strokeStyle = '#fbbf24'
      ctx.lineWidth = 1.2
      ctx.arc(sx, sy, 5.5, 0, Math.PI * 2)
      ctx.fill()
      ctx.stroke()
      ctx.fillStyle = '#ffe8a3'
      ctx.font = '8px "JetBrains Mono", monospace'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(String(index + 1), sx, sy)
    })
    ctx.restore()
  }
}

function onPointerDown(event: PointerEvent) {
  if (event.button !== 0) return
  dragState = { x: event.clientX, y: event.clientY, ox: view.x, oy: view.y, moved: false }
  canvasRef.value?.setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent) {
  if (!dragState) return
  const dx = event.clientX - dragState.x
  const dy = event.clientY - dragState.y
  if (Math.abs(dx) + Math.abs(dy) > 3) {
    dragState.moved = true
    follow.value = false
  }
  view.x = dragState.ox + dx
  view.y = dragState.oy + dy
  scheduleDraw()
}

function onPointerUp(event: PointerEvent) {
  dragState = null
  canvasRef.value?.releasePointerCapture(event.pointerId)
}

function onWheel(event: WheelEvent) {
  event.preventDefault()
  const rect = canvasRef.value!.getBoundingClientRect()
  const mx = event.clientX - rect.left
  const my = event.clientY - rect.top
  const wx = (mx - view.x) / view.scale
  const wy = (my - view.y) / view.scale
  const next = Math.min(1.2, Math.max(0.08, view.scale * (event.deltaY < 0 ? 1.16 : 0.86)))
  view.scale = next
  view.x = mx - wx * next
  view.y = my - wy * next
  follow.value = false
  scheduleDraw()
}

function toggleFollow() {
  follow.value = !follow.value
  if (follow.value && current.value) centerOn(current.value.x, current.value.y)
}

watch(() => [trail.value.length, current.value, route.value, view.x, view.y, view.scale], scheduleDraw)

onMounted(async () => {
  const img = new Image()
  img.onload = () => {
    image.value = img
    fitMap()
    if (current.value) centerOn(current.value.x, current.value.y)
  }
  img.src = '/api/assets/map/base_map.jpg'
  await load()
  resizeObserver = new ResizeObserver(resize)
  if (wrapRef.value) resizeObserver.observe(wrapRef.value)
  resize()
  timer = window.setInterval(poll, 800)
  refreshMeta()
})

onBeforeUnmount(() => {
  window.clearInterval(timer)
  resizeObserver?.disconnect()
  if (raf) cancelAnimationFrame(raf)
})
</script>

<template>
  <div class="page tracker-page">
    <header class="page-head">
      <div>
        <div class="eyebrow">SIFT Map Tracker</div>
        <div class="title-row">
          <h1>地图追踪</h1>
          <span class="status-dot" :class="statusClass" />
          <span class="chip" :class="statusClass === 'running' ? 'primary' : statusClass === 'failed' ? 'danger' : ''">{{
            statusText
          }}</span>
          <span class="chip mono">SIFT · 本地锚点</span>
        </div>
        <p class="page-sub">
          从小地图截图识别世界坐标并记录轨迹。对应 SIFT Map Tracker 工具，不读取游戏内存，锚点缓存保存在本机。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn" :disabled="busy || status?.running" @click="rebuild">
          <AppIcon name="refresh" :size="14" /> 重建锚点
        </button>
        <button v-if="!status?.running" class="btn btn-primary" :disabled="busy" @click="start">
          <AppIcon name="play" :size="14" /> {{ busy ? '启动中...' : '启动追踪' }}
        </button>
        <button v-else class="btn btn-danger" :disabled="busy" @click="stop">
          <AppIcon name="stop" :size="14" /> 停止
        </button>
      </div>
    </header>

    <div class="tracker-layout">
      <section class="panel map-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="map" :size="15" /> 世界地图轨迹</div>
          <div class="map-head-actions">
            <button class="mini-link" :class="{ active: follow }" @click="toggleFollow">
              <AppIcon name="crosshair" :size="12" /> {{ follow ? '跟随中' : '跟随位置' }}
            </button>
            <button class="mini-link" @click="fitMap"><AppIcon name="fit" :size="12" /> 全图</button>
          </div>
        </div>
        <div ref="wrapRef" class="tracker-map">
          <canvas
            ref="canvasRef"
            class="tracker-canvas"
            @pointerdown="onPointerDown"
            @pointermove="onPointerMove"
            @pointerup="onPointerUp"
            @wheel="onWheel"
          />
          <div class="map-legend">
            <span><i class="legend-dot current" /> 当前位置</span>
            <span><i class="legend-line" /> 轨迹</span>
            <span class="mono">{{ trail.length }} points</span>
          </div>
          <div class="route-overlay">
            <div class="route-head">
              <span><AppIcon name="route" :size="12" /> 路线库</span>
              <button v-if="route" class="mini-link" @click="clearRoute">清除</button>
            </div>
            <div class="route-buttons">
              <button
                v-for="preset in routePresets"
                :key="preset.id"
                class="route-chip"
                :disabled="routeBusy"
                @click="planPreset(preset)"
              >
                {{ preset.label }}
              </button>
            </div>
            <div v-if="route" class="route-info mono">
              {{ route.count }} 点位 · {{ route.distancePx }} px
            </div>
          </div>
          <div class="map-overlay-status">
            <span class="mono">{{ Math.round(view.scale * 100) }}%</span>
            <span>·</span>
            <span>{{ status?.stats.ticks || 0 }} 帧 · {{ status?.stats.located || 0 }} 次定位</span>
          </div>
          <div v-if="status?.status === 'building'" class="map-loading">
            <span class="status-dot running" /> 正在建立 SIFT 锚点，首次可能需要几秒...
          </div>
        </div>
      </section>

      <aside class="side-col">
        <section class="panel coord-panel">
          <div class="panel-head">
            <div class="panel-title"><AppIcon name="crosshair" :size="15" /> 当前坐标</div>
            <span v-if="current" class="chip primary mono">{{ current.source }}</span>
          </div>
          <div class="panel-body">
            <div class="coord-main">
              <div class="coord-value">
                <span class="mono">{{ current ? Math.round(current.x) : '—' }}</span>
                <small>X</small>
              </div>
              <div class="coord-value">
                <span class="mono">{{ current ? Math.round(current.y) : '—' }}</span>
                <small>Y</small>
              </div>
            </div>
            <div class="coord-sub mono">
              lat {{ current?.lat?.toFixed(4) ?? '—' }} · lng {{ current?.lng?.toFixed(4) ?? '—' }}
            </div>
            <div class="coord-grid">
              <div><span class="stat-label">Confidence</span><b class="mono">{{ current?.confidence ?? '—' }}</b></div>
              <div><span class="stat-label">Latency</span><b class="mono">{{ status?.stats.latencyMs ?? 0 }} ms</b></div>
              <div><span class="stat-label">Located</span><b class="mono">{{ status?.stats.located ?? 0 }}</b></div>
              <div><span class="stat-label">Lost</span><b class="mono">{{ status?.stats.lost ?? 0 }}</b></div>
            </div>
          </div>
        </section>

        <section class="panel preview-panel">
          <div class="panel-head">
            <div class="panel-title"><AppIcon name="image" :size="15" /> 小地图预览</div>
            <span class="chip mono">2×</span>
          </div>
          <div class="minimap-preview">
            <img v-if="status?.latestUrl" :src="status.latestUrl" alt="小地图追踪预览" />
            <div v-else class="minimap-empty">启动追踪后显示小地图截图</div>
            <div class="minimap-ring" />
          </div>
        </section>

        <section class="panel config-panel">
          <div class="panel-head">
            <div class="panel-title"><AppIcon name="settings" :size="15" /> 追踪配置</div>
          </div>
          <div class="panel-body">
            <div class="field">
              <div class="field-label">追踪间隔（秒）</div>
              <input v-model.number="config.interval" type="number" min="0.2" max="3" step="0.1" class="input" />
            </div>
            <div class="field">
              <div class="field-label">最低置信度 <span class="mono">{{ config.confidenceMin.toFixed(2) }}</span></div>
              <input v-model.number="config.confidenceMin" type="range" min="0" max="0.9" step="0.01" class="range" />
            </div>
            <div class="field">
              <div class="field-label">截图间隔（帧）</div>
              <input v-model.number="config.screenshotEvery" type="number" min="1" max="10" class="input" />
            </div>
            <div class="anchor-row">
              <div>
                <div class="field-label">锚点缓存</div>
                <div class="field-help">最大边长 {{ status?.anchor.maxEdge || '—' }} px</div>
              </div>
              <span class="chip" :class="status?.anchor.cached ? 'success' : 'amber'">
                {{ status?.anchor.cached ? `${status.anchor.points} points` : '未建立' }}
              </span>
            </div>
            <div class="config-actions">
              <button v-if="!status?.running" class="btn btn-primary" style="width: 100%" :disabled="busy" @click="start">
                <AppIcon name="play" :size="13" /> 应用并启动
              </button>
              <button v-else class="btn btn-danger" style="width: 100%" :disabled="busy" @click="stop">
                <AppIcon name="stop" :size="13" /> 停止追踪
              </button>
            </div>
          </div>
        </section>
      </aside>
    </div>

    <section class="panel log-panel">
      <div class="panel-head">
        <div class="panel-title"><AppIcon name="activity" :size="15" /> 追踪日志</div>
        <span class="chip mono">{{ status?.logs?.length || 0 }}</span>
      </div>
      <div class="panel-body tracker-logs">
        <div v-for="(log, index) in status?.logs || []" :key="index" class="tracker-log" :class="log.kind">
          <span class="mono log-time">{{ new Date(log.ts).toLocaleTimeString('zh-CN', { hour12: false }) }}</span>
          <span class="mono log-kind">{{ log.kind }}</span>
          <span>{{ log.message }}</span>
        </div>
        <div v-if="!status?.logs?.length" class="muted" style="font-size: 11px">
          启动追踪后，这里会显示定位、置信度与丢失信息。
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.tracker-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
}

.map-panel {
  display: flex;
  flex-direction: column;
  height: 620px;
  overflow: hidden;
}

.map-head-actions {
  display: flex;
  gap: 12px;
}

.mini-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  color: var(--faint);
  font-size: 9.5px;
  padding: 0;
}

.mini-link:hover,
.mini-link.active {
  color: var(--primary);
}

.tracker-map {
  position: relative;
  flex: 1;
  min-height: 0;
  background: #f2faff;
}

.tracker-canvas {
  display: block;
  width: 100%;
  height: 100%;
  cursor: grab;
  touch-action: none;
}

.tracker-canvas:active {
  cursor: grabbing;
}

.map-legend {
  position: absolute;
  left: 12px;
  top: 12px;
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 7px 10px;
  border-radius: 7px;
  border: 1px solid rgba(190, 220, 237, 0.7);
  background: rgba(255, 255, 255, 0.8);
  font-size: 9.5px;
  color: var(--muted);
  backdrop-filter: blur(8px);
}

.map-legend > span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.legend-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.legend-dot.current {
  background: #ffd166;
}

.legend-line {
  width: 14px;
  height: 2px;
  background: rgba(14, 165, 233, 0.65);
}

.route-overlay {
  position: absolute;
  right: 12px;
  top: 12px;
  width: 168px;
  padding: 9px 10px;
  border-radius: 8px;
  border: 1px solid rgba(190, 220, 237, 0.7);
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(8px);
}

.route-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 9.5px;
  color: var(--primary);
}

.route-head > span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.route-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 7px;
}

.route-chip {
  padding: 3px 6px;
  border-radius: 5px;
  border: 1px solid rgba(251, 191, 36, 0.16);
  background: rgba(251, 191, 36, 0.05);
  color: #e8cf94;
  font-size: 8.5px;
}

.route-chip:hover:not(:disabled) {
  background: rgba(251, 191, 36, 0.12);
  border-color: rgba(251, 191, 36, 0.32);
}

.route-chip:disabled {
  opacity: 0.45;
}

.route-info {
  margin-top: 6px;
  padding-top: 5px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 8.5px;
  color: var(--faint);
}

.map-overlay-status {
  position: absolute;
  right: 12px;
  bottom: 12px;
  display: flex;
  gap: 6px;
  padding: 6px 9px;
  border-radius: 6px;
  border: 1px solid rgba(190, 220, 237, 0.65);
  background: rgba(255, 255, 255, 0.8);
  font-size: 9px;
  color: var(--faint);
}

.map-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--muted);
  font-size: 11.5px;
  backdrop-filter: blur(4px);
}

.side-col {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.coord-main {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.coord-value {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid var(--border-soft);
  background: rgba(255, 255, 255, 0.02);
}

.coord-value span {
  font-size: 20px;
  font-weight: 600;
  color: var(--primary);
  letter-spacing: -0.03em;
}

.coord-value small {
  font-size: 9px;
  color: var(--faint);
}

.coord-sub {
  margin-top: 8px;
  font-size: 9.5px;
  color: var(--faint);
}

.coord-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-soft);
}

.coord-grid b {
  display: block;
  margin-top: 2px;
  font-size: 13px;
  color: var(--text-soft);
  font-weight: 550;
}

.minimap-preview {
  position: relative;
  height: 170px;
  background: repeating-conic-gradient(rgba(255, 255, 255, 0.025) 0% 25%, transparent 0% 50%) 50% / 18px 18px;
  display: grid;
  place-items: center;
  overflow: hidden;
}

.minimap-preview img {
  width: 78%;
  max-height: 150px;
  object-fit: contain;
  border-radius: 50%;
  box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.25), 0 10px 30px rgba(0, 0, 0, 0.4);
}

.minimap-empty {
  font-size: 10px;
  color: var(--faint);
}

.minimap-ring {
  position: absolute;
  width: 44px;
  height: 44px;
  border: 1px solid rgba(14, 165, 233, 0.35);
  border-radius: 50%;
  pointer-events: none;
}

.anchor-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--border-soft);
}

.config-actions {
  margin-top: 14px;
}

.range {
  width: 100%;
  height: 4px;
  appearance: none;
  background: linear-gradient(90deg, rgba(14, 165, 233, 0.5), rgba(14, 165, 233, 0.12));
  border-radius: 999px;
  outline: none;
  margin-top: 6px;
}

.range::-webkit-slider-thumb {
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--primary-2);
  border: 2px solid #082f49;
}

.log-panel {
  margin-top: 16px;
}

.tracker-logs {
  max-height: 190px;
  overflow: auto;
  font-family: var(--mono);
  font-size: 10px;
  line-height: 1.8;
}

.tracker-log {
  display: grid;
  grid-template-columns: 64px 56px minmax(0, 1fr);
  gap: 8px;
  border-bottom: 1px solid rgba(214, 234, 245, 0.45);
  padding: 2px 0;
  color: var(--text-soft);
}

.tracker-log .log-time {
  color: var(--faint);
}

.tracker-log .log-kind {
  color: var(--primary);
  font-size: 9px;
  text-transform: uppercase;
}

.tracker-log.warn,
.tracker-log.error {
  color: #fca5a5;
}

.tracker-log.warn .log-kind,
.tracker-log.error .log-kind {
  color: var(--danger);
}

@media (max-width: 1150px) {
  .tracker-layout {
    grid-template-columns: 1fr;
  }
  .map-panel {
    height: 440px;
  }
}
</style>
