<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { api, assetUrl } from '../lib/api'
import { refreshMeta } from '../lib/store'
import { notify } from '../lib/toast'
import type { MapMeta, PoiPoint, RoutePlan } from '../types'

const canvasRef = ref<HTMLCanvasElement | null>(null)
const wrapRef = ref<HTMLDivElement | null>(null)
const loading = ref(true)
const meta = ref<MapMeta | null>(null)
const points = ref<PoiPoint[]>([])
const image = ref<HTMLImageElement | null>(null)
const selectedCategories = ref<Set<string>>(new Set())
const labelQuery = ref('')
const selectedPoint = ref<PoiPoint | null>(null)
const hoverPoint = ref<PoiPoint | null>(null)
const hoverPos = reactive({ x: 0, y: 0 })
const position = reactive({ x: 3072, y: 2944, source: 'mock' })
const routePlan = ref<RoutePlan | null>(null)
const planning = ref(false)
const locating = ref(false)
const routeLimit = ref(15)
const roundtrip = ref(false)
const routeLabelsInput = ref('')
const view = reactive({ x: 0, y: 0, scale: 1 })
const spatial = reactive({ width: 0, height: 0 })
let ctx: CanvasRenderingContext2D | null = null
let raf = 0
let dragState: { x: number; y: number; ox: number; oy: number; moved: boolean } | null = null
let resizeObserver: ResizeObserver | null = null

const MAP_W = 6144
const MAP_H = 5888

const categoryList = computed(() => meta.value?.categories || [])

const visiblePoints = computed(() => {
  const categories = selectedCategories.value
  const keyword = labelQuery.value.trim().toLowerCase()
  return points.value.filter((point) => {
    if (!categories.has(point.category)) return false
    if (keyword && !point.label.toLowerCase().includes(keyword) && !point.title.toLowerCase().includes(keyword)) return false
    return true
  })
})

const playerScreen = computed(() => ({
  x: view.x + position.x * view.scale,
  y: view.y + position.y * view.scale,
}))

const routeScreen = computed(() => {
  if (!routePlan.value) return []
  return routePlan.value.route.map((point: any, index: number) => ({
    ...point,
    index,
    sx: view.x + point.x * view.scale,
    sy: view.y + point.y * view.scale,
  }))
})

const startScreen = computed(() => ({
  x: view.x + (routePlan.value?.start.x ?? position.x) * view.scale,
  y: view.y + (routePlan.value?.start.y ?? position.y) * view.scale,
}))

// ------------------------------------------------------------------- loading
async function load() {
  try {
    const [mapMeta, pointData] = await Promise.all([
      api<MapMeta>('/api/map/meta'),
      api<{ points: PoiPoint[] }>('/api/map/points?limit=20000'),
    ])
    meta.value = mapMeta
    points.value = pointData.points
    selectedCategories.value = new Set(mapMeta.categories.map((category) => category.id))
    const img = new Image()
    img.onload = () => {
      image.value = img
      focusPosition()
      scheduleDraw()
    }
    img.src = assetUrl(mapMeta.baseMap)
  } catch (error) {
    notify(`地图加载失败：${error}`, 'error')
  } finally {
    loading.value = false
  }
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

function fitView() {
  const wrap = wrapRef.value
  if (!wrap) return
  const scale = Math.min(wrap.clientWidth / MAP_W, wrap.clientHeight / MAP_H) * 0.96
  view.scale = scale
  view.x = (wrap.clientWidth - MAP_W * scale) / 2
  view.y = (wrap.clientHeight - MAP_H * scale) / 2
  scheduleDraw()
}

function focusPosition(scale = 0.22) {
  const wrap = wrapRef.value
  if (!wrap) return
  view.scale = Math.min(0.42, Math.max(0.16, scale))
  view.x = wrap.clientWidth / 2 - position.x * view.scale
  view.y = wrap.clientHeight / 2 - position.y * view.scale
  scheduleDraw()
}

function screenToWorld(clientX: number, clientY: number) {
  const rect = canvasRef.value!.getBoundingClientRect()
  return {
    x: (clientX - rect.left - view.x) / view.scale,
    y: (clientY - rect.top - view.y) / view.scale,
  }
}

function colorOf(category: string): string {
  return categoryList.value.find((item) => item.id === category)?.color || '#94a3b8'
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
    ctx.globalAlpha = 0.9
    ctx.drawImage(image.value, view.x, view.y, MAP_W * view.scale, MAP_H * view.scale)
    ctx.restore()
  }

  const scale = view.scale
  const radius = Math.min(4.2, Math.max(1.2, 1.9 * Math.sqrt(scale * 4)))
  for (const point of visiblePoints.value) {
    const sx = view.x + point.x * scale
    const sy = view.y + point.y * scale
    if (sx < -10 || sy < -10 || sx > width + 10 || sy > height + 10) continue
    ctx.beginPath()
    ctx.fillStyle = `${colorOf(point.category)}${selectedPoint.value?.id === point.id ? 'ff' : 'c8'}`
    ctx.arc(sx, sy, selectedPoint.value?.id === point.id ? radius + 2 : radius, 0, Math.PI * 2)
    ctx.fill()
  }

  if (routePlan.value) {
    const start = startScreen.value
    ctx.save()
    ctx.lineWidth = 2
    ctx.strokeStyle = 'rgba(14, 165, 233, 0.9)'
    ctx.shadowColor = 'rgba(14, 165, 233, 0.45)'
    ctx.shadowBlur = 10
    ctx.beginPath()
    ctx.moveTo(start.x, start.y)
    for (const point of routeScreen.value) ctx.lineTo(point.sx, point.sy)
    ctx.stroke()
    ctx.restore()

    for (const point of routeScreen.value) {
      ctx.beginPath()
      ctx.fillStyle = '#e6f7ff'
      ctx.strokeStyle = '#0ea5e9'
      ctx.lineWidth = 1.6
      ctx.arc(point.sx, point.sy, 8, 0, Math.PI * 2)
      ctx.fill()
      ctx.stroke()
      ctx.fillStyle = '#38bdf8'
      ctx.font = '600 9px "JetBrains Mono", monospace'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(String(point.index + 1), point.sx, point.sy)
    }
  }
}

// ------------------------------------------------------------------- events
function onPointerDown(event: PointerEvent) {
  if (event.button !== 0) return
  dragState = { x: event.clientX, y: event.clientY, ox: view.x, oy: view.y, moved: false }
  canvasRef.value?.setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent) {
  if (dragState) {
    const dx = event.clientX - dragState.x
    const dy = event.clientY - dragState.y
    if (Math.abs(dx) + Math.abs(dy) > 3) dragState.moved = true
    view.x = dragState.ox + dx
    view.y = dragState.oy + dy
    scheduleDraw()
    return
  }
  const rect = canvasRef.value?.getBoundingClientRect()
  if (!rect) return
  const sx = event.clientX - rect.left
  const sy = event.clientY - rect.top
  hoverPos.x = sx
  hoverPos.y = sy
  let nearest: PoiPoint | null = null
  let best = 12
  for (const point of visiblePoints.value) {
    const px = view.x + point.x * view.scale
    const py = view.y + point.y * view.scale
    const distance = Math.hypot(px - sx, py - sy)
    if (distance < best) {
      best = distance
      nearest = point
    }
  }
  hoverPoint.value = nearest
}

function onPointerUp(event: PointerEvent) {
  const wasClick = dragState && !dragState.moved
  dragState = null
  canvasRef.value?.releasePointerCapture(event.pointerId)
  if (!wasClick) return
  const rect = canvasRef.value?.getBoundingClientRect()
  if (!rect) return
  const sx = event.clientX - rect.left
  const sy = event.clientY - rect.top
  let nearest: PoiPoint | null = null
  let best = 16
  for (const point of visiblePoints.value) {
    const px = view.x + point.x * view.scale
    const py = view.y + point.y * view.scale
    const distance = Math.hypot(px - sx, py - sy)
    if (distance < best) {
      best = distance
      nearest = point
    }
  }
  selectedPoint.value = nearest
}

function onWheel(event: WheelEvent) {
  event.preventDefault()
  const rect = canvasRef.value!.getBoundingClientRect()
  const mx = event.clientX - rect.left
  const my = event.clientY - rect.top
  const wx = (mx - view.x) / view.scale
  const wy = (my - view.y) / view.scale
  const next = Math.min(4, Math.max(0.12, view.scale * (event.deltaY < 0 ? 1.16 : 0.86)))
  view.scale = next
  view.x = mx - wx * next
  view.y = my - wy * next
  scheduleDraw()
}

function zoomBy(factor: number) {
  const wrap = wrapRef.value
  if (!wrap) return
  const mx = wrap.clientWidth / 2
  const my = wrap.clientHeight / 2
  const wx = (mx - view.x) / view.scale
  const wy = (my - view.y) / view.scale
  view.scale = Math.min(4, Math.max(0.12, view.scale * factor))
  view.x = mx - wx * view.scale
  view.y = my - wy * view.scale
  scheduleDraw()
}

function toggleCategory(category: string) {
  const next = new Set(selectedCategories.value)
  if (next.has(category)) next.delete(category)
  else next.add(category)
  selectedCategories.value = next
}

function selectAllCategories() {
  selectedCategories.value = new Set(categoryList.value.map((category) => category.id))
}

function clearCategories() {
  selectedCategories.value = new Set()
}

// ------------------------------------------------------------------- route
async function locate() {
  locating.value = true
  try {
    const result = await api<{ ok: boolean; position: any }>('/api/map/position', { method: 'POST', body: '{}' })
    if (result.ok && result.position?.x) {
      position.x = result.position.x
      position.y = result.position.y
      position.source = result.position.source || 'sift'
      routePlan.value = null
      notify(`定位成功 · ${position.source} · (${Math.round(position.x)}, ${Math.round(position.y)})`, 'success')
      focusPosition()
      scheduleDraw()
    } else {
      notify('定位失败，请检查定位源设置', 'error')
    }
  } catch (error) {
    notify(`定位失败：${error}`, 'error')
  } finally {
    locating.value = false
  }
}

async function planRoute() {
  planning.value = true
  try {
    const labels = routeLabelsInput.value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
    const result = await api<RoutePlan>('/api/map/route', {
      method: 'POST',
      body: JSON.stringify({
        start: { x: position.x, y: position.y },
        categories: Array.from(selectedCategories.value),
        labels,
        limit: routeLimit.value,
        roundtrip: roundtrip.value,
      }),
    })
    routePlan.value = result
    selectedPoint.value = null
    notify(`已规划 ${result.count} 个点位 · 相对距离 ${result.distancePx} px`, 'success')
    scheduleDraw()
  } catch (error) {
    notify(`路线规划失败：${error}`, 'error')
  } finally {
    planning.value = false
  }
}

function clearRoute() {
  routePlan.value = null
  scheduleDraw()
}

function usePointAsStart() {
  if (!selectedPoint.value) return
  position.x = selectedPoint.value.x
  position.y = selectedPoint.value.y
  position.source = 'manual'
  routePlan.value = null
  notify(`起点已设为「${selectedPoint.value.title || selectedPoint.value.label}」`, 'success')
  scheduleDraw()
}

watch(
  () => [visiblePoints.value.length, selectedPoint.value, routePlan.value, view.x, view.y, view.scale, selectedCategories.value],
  scheduleDraw,
)

watch(() => labelQuery.value, scheduleDraw)

onMounted(async () => {
  await load()
  resizeObserver = new ResizeObserver(() => resize())
  if (wrapRef.value) resizeObserver.observe(wrapRef.value)
  resize()
  refreshMeta()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  if (raf) cancelAnimationFrame(raf)
})
</script>

<template>
  <div class="map-page">
    <header class="map-header">
      <div>
        <div class="eyebrow">World Map</div>
        <div class="map-title-row">
          <h1>资源地图</h1>
          <span class="chip mono">{{ meta?.pointCount || 0 }} POI</span>
          <span class="chip mono">{{ meta?.categoryCount || 0 }} 分类</span>
        </div>
      </div>
      <div class="page-actions">
        <button class="btn" :disabled="locating" @click="locate">
          <AppIcon name="crosshair" :size="14" /> {{ locating ? '定位中' : '从游戏定位' }}
        </button>
        <button class="btn" @click="fitView"><AppIcon name="fit" :size="14" /> 适配视图</button>
      </div>
    </header>

    <div ref="wrapRef" class="map-wrap">
      <canvas
        ref="canvasRef"
        class="map-canvas"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointerleave="hoverPoint = null"
        @wheel="onWheel"
      />

      <div class="map-panel filters-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="filter" :size="14" /> 资源筛选</div>
          <span class="mono faint" style="font-size: 9px">{{ visiblePoints.length }} 显示</span>
        </div>
        <div class="panel-body">
          <div class="label-search">
            <AppIcon name="search" :size="13" />
            <input v-model="labelQuery" placeholder="搜索点位名称..." />
          </div>
          <div class="cat-actions">
            <button class="mini-link" @click="selectAllCategories">全选</button>
            <button class="mini-link" @click="clearCategories">全不选</button>
          </div>
          <div class="cat-list">
            <button
              v-for="category in categoryList"
              :key="category.id"
              class="cat-toggle"
              :class="{ on: selectedCategories.has(category.id) }"
              @click="toggleCategory(category.id)"
            >
              <span class="cat-check" :style="{ borderColor: category.color, background: selectedCategories.has(category.id) ? category.color : 'transparent' }" />
              <span class="cat-name">{{ category.label }}</span>
              <span class="cat-count mono">{{ category.count }}</span>
            </button>
          </div>
        </div>
      </div>

      <div class="map-panel planner-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="route" :size="14" /> 路线规划</div>
          <button v-if="routePlan" class="mini-link" @click="clearRoute">清除</button>
        </div>
        <div class="panel-body">
          <div class="start-row">
            <div class="start-coord">
              <span class="stat-label">起点</span>
              <span class="mono">{{ Math.round(position.x) }}, {{ Math.round(position.y) }}</span>
            </div>
            <span class="chip" :class="position.source === 'sift' ? 'primary' : ''">{{ position.source }}</span>
          </div>
          <div class="field">
            <div class="field-label">资源名称（可留空）</div>
            <input v-model="routeLabelsInput" class="input" placeholder="宝箱, 魔法石" />
          </div>
          <div class="field">
            <div class="field-label">最多访问点 <span class="mono">{{ routeLimit }}</span></div>
            <input v-model.number="routeLimit" type="range" min="3" max="40" step="1" class="range" />
          </div>
          <div class="toggle-row" style="padding: 6px 0">
            <span class="field-label">返回起点</span>
            <div class="toggle" :class="{ on: roundtrip }" @click="roundtrip = !roundtrip" />
          </div>
          <button class="btn btn-primary plan-btn" :disabled="planning" @click="planRoute">
            <AppIcon name="route" :size="14" /> {{ planning ? '规划中...' : '规划路线' }}
          </button>

          <div v-if="routePlan" class="plan-result">
            <div class="plan-stats">
              <div><span class="stat-label">Points</span><b class="mono">{{ routePlan.count }}</b></div>
              <div><span class="stat-label">Distance</span><b class="mono">{{ routePlan.distancePx }} px</b></div>
              <div><span class="stat-label">Est.</span><b class="mono">{{ routePlan.estimatedMinutes }} min</b></div>
            </div>
            <div class="route-list">
              <div v-for="(point, index) in routePlan.route" :key="point.id" class="route-item">
                <span class="route-index mono">{{ index + 1 }}</span>
                <span class="route-name">{{ point.title || point.label }}</span>
                <span class="route-label">{{ point.label }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="selectedPoint" class="map-panel detail-panel">
        <div class="detail-head">
          <div class="detail-dot" :style="{ background: colorOf(selectedPoint.category) }" />
          <div class="detail-title">{{ selectedPoint.title || selectedPoint.label }}</div>
          <button class="mini-link" @click="selectedPoint = null"><AppIcon name="close" :size="12" /></button>
        </div>
        <div class="detail-meta">
          <span>{{ selectedPoint.category }}</span>
          <span>·</span>
          <span>{{ selectedPoint.label }}</span>
          <span>·</span>
          <span class="mono">{{ Math.round(selectedPoint.x) }}, {{ Math.round(selectedPoint.y) }}</span>
        </div>
        <div class="detail-actions">
          <button class="btn btn-sm btn-primary" @click="usePointAsStart">设为起点</button>
          <span class="chip mono">{{ selectedPoint.source }}</span>
        </div>
      </div>

      <div class="map-controls">
        <button class="tool-btn" @click="zoomBy(1.2)"><AppIcon name="zoomIn" :size="14" /></button>
        <button class="tool-btn" @click="zoomBy(0.83)"><AppIcon name="zoomOut" :size="14" /></button>
        <button class="tool-btn" @click="fitView"><AppIcon name="fit" :size="14" /></button>
      </div>

      <div class="map-status">
        <span>缩放 {{ Math.round(view.scale * 100) }}%</span>
        <span>·</span>
        <span>{{ visiblePoints.length }} 个点</span>
        <span>·</span>
        <span>拖拽平移 · 滚轮缩放</span>
      </div>

      <div
        class="player-marker"
        :style="{ left: `${playerScreen.x}px`, top: `${playerScreen.y}px` }"
        title="当前位置"
      >
        <span class="player-ring" />
        <span class="player-core"><AppIcon name="crosshair" :size="12" /></span>
      </div>

      <div
        v-if="hoverPoint"
        class="map-tooltip"
        :style="{ left: `${hoverPos.x + 14}px`, top: `${hoverPos.y + 14}px` }"
      >
        <div class="tooltip-title">{{ hoverPoint.title || hoverPoint.label }}</div>
        <div class="tooltip-meta">{{ hoverPoint.category }} · {{ hoverPoint.label }}</div>
      </div>

      <div v-if="loading" class="map-loading">正在加载地图与点位...</div>
    </div>
  </div>
</template>

<style scoped>
.map-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f7fcff;
}

.map-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 24px 30px 18px;
  border-bottom: 1px solid var(--border-soft);
  flex: none;
}

.map-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.map-title-row h1 {
  font-size: 28px;
}

.map-wrap {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: #f2faff;
}

.map-canvas {
  display: block;
  width: 100%;
  height: 100%;
  cursor: grab;
  touch-action: none;
}

.map-canvas:active {
  cursor: grabbing;
}

.map-panel {
  position: absolute;
  border: 1px solid rgba(190, 220, 237, 0.78);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(14px);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.4);
  z-index: 3;
}

.filters-panel {
  left: 18px;
  top: 18px;
  width: 248px;
  max-height: calc(100% - 36px);
  display: flex;
  flex-direction: column;
}

.filters-panel .panel-body {
  padding: 12px 13px 14px;
  overflow: auto;
}

.label-search {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 30px;
  padding: 0 9px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.55);
  color: var(--faint);
}

.label-search input {
  width: 100%;
  border: none;
  background: transparent;
  outline: none;
  font-size: 11px;
  color: var(--text);
}

.label-search input::placeholder {
  color: var(--faint);
}

.cat-actions {
  display: flex;
  gap: 12px;
  margin: 9px 2px 6px;
}

.mini-link {
  border: none;
  background: transparent;
  color: var(--faint);
  font-size: 9.5px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.mini-link:hover {
  color: var(--primary);
}

.cat-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.cat-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 6px;
  border: none;
  border-radius: 6px;
  background: transparent;
  text-align: left;
  color: var(--muted);
}

.cat-toggle:hover {
  background: rgba(255, 255, 255, 0.03);
  color: var(--text);
}

.cat-toggle.on .cat-name {
  color: var(--text-soft);
}

.cat-check {
  width: 11px;
  height: 11px;
  border-radius: 3px;
  border: 1px solid var(--faint);
  flex: none;
}

.cat-name {
  font-size: 11px;
}

.cat-count {
  margin-left: auto;
  font-size: 9px;
  color: var(--faint);
}

.planner-panel {
  right: 18px;
  top: 18px;
  width: 300px;
  max-height: calc(100% - 36px);
  display: flex;
  flex-direction: column;
}

.planner-panel .panel-body {
  padding: 13px;
  overflow: auto;
}

.start-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-soft);
  background: rgba(255, 255, 255, 0.02);
  margin-bottom: 12px;
}

.start-coord {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 10.5px;
  color: var(--text-soft);
}

.start-coord .stat-label {
  font-size: 9px;
}

.range {
  width: 100%;
  height: 4px;
  appearance: none;
  background: linear-gradient(90deg, rgba(14, 165, 233, 0.5), rgba(14, 165, 233, 0.12));
  border-radius: 999px;
  outline: none;
}

.range::-webkit-slider-thumb {
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #38bdf8;
  border: 2px solid #082f49;
  cursor: pointer;
}

.plan-btn {
  width: 100%;
  margin-top: 12px;
}

.plan-result {
  margin-top: 13px;
  border-top: 1px solid var(--border-soft);
  padding-top: 12px;
}

.plan-stats {
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.plan-stats > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.plan-stats b {
  font-size: 13px;
  font-weight: 600;
  color: var(--primary);
}

.plan-stats .stat-label {
  font-size: 8.5px;
}

.route-list {
  margin-top: 10px;
  max-height: 180px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.route-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 5px;
  border-radius: 5px;
  font-size: 10px;
}

.route-item:hover {
  background: rgba(255, 255, 255, 0.03);
}

.route-index {
  width: 17px;
  height: 17px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(14, 165, 233, 0.35);
  color: var(--primary);
  font-size: 8px;
  flex: none;
}

.route-name {
  color: var(--text-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.route-label {
  margin-left: auto;
  font-size: 8.5px;
  color: var(--faint);
  flex: none;
}

.detail-panel {
  left: 18px;
  bottom: 18px;
  width: 300px;
  padding: 12px 14px;
}

.detail-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.detail-title {
  font-size: 12.5px;
  font-weight: 600;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-meta {
  margin-top: 6px;
  font-size: 9.5px;
  color: var(--faint);
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.detail-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}

.map-controls {
  position: absolute;
  right: 18px;
  bottom: 18px;
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: 9px;
  border: 1px solid rgba(190, 220, 237, 0.75);
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  z-index: 3;
}

.tool-btn {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
}

.tool-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text);
}

.map-status {
  position: absolute;
  left: 50%;
  bottom: 16px;
  transform: translateX(-50%);
  display: flex;
  gap: 7px;
  padding: 6px 11px;
  border-radius: 7px;
  border: 1px solid rgba(190, 220, 237, 0.65);
  background: rgba(255, 255, 255, 0.78);
  font-size: 9.5px;
  color: var(--faint);
  z-index: 3;
  white-space: nowrap;
}

.player-marker {
  position: absolute;
  width: 0;
  height: 0;
  z-index: 4;
  pointer-events: none;
}

.player-ring {
  position: absolute;
  left: -16px;
  top: -16px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid rgba(251, 191, 36, 0.5);
  animation: player-pulse 2s ease-out infinite;
}

.player-core {
  position: absolute;
  left: -9px;
  top: -9px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #082f49;
  background: #ffd166;
  box-shadow: 0 0 0 2px rgba(6, 35, 31, 0.7), 0 0 18px rgba(251, 191, 36, 0.5);
}

@keyframes player-pulse {
  0% {
    transform: scale(0.5);
    opacity: 0.9;
  }
  100% {
    transform: scale(1.6);
    opacity: 0;
  }
}

.map-tooltip {
  position: absolute;
  z-index: 5;
  pointer-events: none;
  padding: 7px 9px;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.45);
}

.tooltip-title {
  font-size: 10.5px;
  font-weight: 550;
  color: var(--text);
}

.tooltip-meta {
  margin-top: 2px;
  font-size: 9px;
  color: var(--faint);
}

.map-loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--faint);
  font-size: 12px;
  background: rgba(255, 255, 255, 0.6);
  z-index: 6;
}

@media (max-width: 1180px) {
  .filters-panel {
    width: 210px;
  }
  .planner-panel {
    width: 260px;
  }
}
</style>
