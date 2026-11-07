<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../lib/api'
import { notify } from '../lib/toast'

interface PetItem {
  name: string
  element: string
  elementColor: string
  stage: string
  total: number
}

interface PetDetail {
  pokemon: {
    name: string
    spiritNo: string
    element: string
    elementColor: string
    stage: string
    total: number
    ability: { name: string; description: string }
    stats: { key: string; label: string; value: number; color: string }[]
  }
  skills: { id: number; name: string; element: string; category: string; power: number; energy: number }[]
}

const route = useRoute()
const overlay = computed(() => route.query.overlay === '1')

const pet = ref<PetItem | null>(null)
const detail = ref<PetDetail | null>(null)
const roster = ref<PetItem[]>([])
const elements = ref<{ name: string; color: string }[]>([])
const search = ref('')
const element = ref('')
const loading = ref(false)
const mood = ref<'idle' | 'happy' | 'sleep'>('idle')
const lineIndex = ref(0)
const size = ref(1)
const bubbleOpen = ref(true)

const position = reactive({ x: 0, y: 0 })
let dragStart = { x: 0, y: 0, px: 0, py: 0 }
let dragging = false
let searchTimer: ReturnType<typeof setTimeout> | null = null

const elementColor = computed(() => pet.value?.elementColor || '#38bdf8')
const stageStyle = computed(() => ({ '--elem': elementColor.value }))

const lines = computed(() => {
  const name = pet.value?.name || 'Rocogi'
  const elem = pet.value?.element || '光'
  const base = [
    `我是${name}，${elem}系的伙伴。`,
    '今天也要一起去抓精灵吗？',
    `按 X 丢球的时候，我会帮你盯着。`,
    '休息一下也没关系，我守着你。',
  ]
  if (mood.value === 'sleep') return ['Zzz...', '呼——呼——', '再睡五分钟...']
  if (mood.value === 'happy') return [`${name} 很开心！`, '转个圈给你看！', '再来一次！']
  return base
})

const bubble = computed(() => lines.value[lineIndex.value % lines.value.length])
const abilityText = computed(() => detail.value?.pokemon.ability.description || '这只精灵还没有特性描述。')

function tapPet() {
  if (mood.value === 'sleep') {
    mood.value = 'idle'
  } else {
    mood.value = 'happy'
  }
  lineIndex.value += 1
  bubbleOpen.value = true
  window.setTimeout(() => {
    if (mood.value === 'happy') mood.value = 'idle'
  }, 900)
}

function setMood(next: 'idle' | 'happy' | 'sleep') {
  mood.value = next
  lineIndex.value += 1
  bubbleOpen.value = true
}

function stepSize(delta: number) {
  size.value = Math.min(1.6, Math.max(0.6, Math.round((size.value + delta) * 100) / 100))
}

async function loadRoster() {
  loading.value = true
  try {
    const params = new URLSearchParams({ limit: '72', sort: 'id', order: 'asc' })
    if (search.value.trim()) params.set('q', search.value.trim())
    if (element.value) params.set('element', element.value)
    const data = await api<{ items: PetItem[] }>(`/api/dex/pokemon?${params.toString()}`)
    roster.value = data.items
  } catch (error) {
    notify(`读取精灵列表失败：${error}`, 'error')
  } finally {
    loading.value = false
  }
}

async function loadDetail(name: string) {
  try {
    detail.value = await api<PetDetail>(`/api/dex/pokemon/${encodeURIComponent(name)}`)
  } catch {
    detail.value = null
  }
}

async function choose(item: PetItem) {
  pet.value = item
  mood.value = 'idle'
  lineIndex.value = 0
  bubbleOpen.value = true
  localStorage.setItem('rocogi.pet', JSON.stringify(item))
  await loadDetail(item.name)
}

function scheduleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(loadRoster, 280)
}

function openPetWindow() {
  if (!pet.value) return
  const pct = Math.round(size.value * 100)
  // 把工作台里选好的状态与尺寸带给桌面伙伴窗口，避免弹出来又回到默认待机尺寸。
  const url =
    `${location.origin}/pet?overlay=1&name=${encodeURIComponent(pet.value.name)}` +
    `&state=${mood.value}&size=${pct}`
  const width = Math.round(380 * size.value)
  const height = Math.round(470 * size.value)
  const win = window.open(url, 'rocogi-pet', `popup=yes,width=${width},height=${height}`)
  if (!win) notify('浏览器拦截了弹窗，请允许本站弹出窗口', 'error')
}

function closeOverlay() {
  window.close()
}

function onPointerDown(event: PointerEvent) {
  if (!overlay.value) return
  dragging = true
  dragStart = { x: event.clientX, y: event.clientY, px: position.x, py: position.y }
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent) {
  if (!dragging) return
  position.x = dragStart.px + event.clientX - dragStart.x
  position.y = dragStart.py + event.clientY - dragStart.y
}

function onPointerUp() {
  dragging = false
}

onMounted(async () => {
  try {
    const meta = await api<{ elements: { name: string; color: string }[] }>('/api/dex/meta')
    elements.value = meta.elements
  } catch {
    /* optional */
  }
  await loadRoster()
  const queryName = String(route.query.name || '')
  const saved = localStorage.getItem('rocogi.pet')
  let initial = queryName || '迪莫'
  if (!queryName && saved) {
    try {
      initial = JSON.parse(saved).name || initial
    } catch {
      /* ignore */
    }
  }
  const found = roster.value.find((item) => item.name === initial)
  if (found) {
    await choose(found)
  } else {
    try {
      const data = await api<PetDetail>(`/api/dex/pokemon/${encodeURIComponent(initial)}`)
      await choose(data.pokemon as unknown as PetItem)
    } catch {
      if (roster.value.length) await choose(roster.value[0])
    }
  }
  const queryMood = String(route.query.state || '')
  if (queryMood === 'idle' || queryMood === 'happy' || queryMood === 'sleep') mood.value = queryMood
  const querySize = Number(route.query.size)
  if (Number.isFinite(querySize) && querySize > 0) {
    size.value = Math.min(1.6, Math.max(0.6, querySize / 100))
  }
  if (overlay.value) document.body.classList.add('pet-overlay-mode')
})

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
  document.body.classList.remove('pet-overlay-mode')
})
</script>

<template>
  <div v-if="overlay" class="pet-overlay" :style="stageStyle" @pointermove="onPointerMove" @pointerup="onPointerUp">
    <div class="overlay-bar">
      <span class="mono overlay-title">{{ pet?.name || 'Rocogi' }} · {{ pet?.element || '光' }}系</span>
      <div class="overlay-states">
        <button
          v-for="option in [
            { id: 'idle', label: '待机' },
            { id: 'happy', label: '跳跃' },
            { id: 'sleep', label: '睡觉' },
          ]"
          :key="option.id"
          class="overlay-state-btn"
          :class="{ active: mood === option.id }"
          :title="`切换到${option.label}`"
          @click.stop="setMood(option.id as 'idle' | 'happy' | 'sleep')"
        >
          {{ option.label }}
        </button>
        <span class="overlay-size">
          <button class="overlay-size-btn" title="缩小" @click.stop="stepSize(-0.1)">−</button>
          <span class="mono">{{ Math.round(size * 100) }}%</span>
          <button class="overlay-size-btn" title="放大" @click.stop="stepSize(0.1)">＋</button>
        </span>
      </div>
      <button class="overlay-close" title="关闭桌宠窗口" @click="closeOverlay">
        <AppIcon name="close" :size="13" />
      </button>
    </div>
    <div
      class="overlay-pet"
      :style="{ transform: `translate(${position.x}px, ${position.y}px) scale(${size})`, '--elem': elementColor }"
      @pointerdown="onPointerDown"
      @click="tapPet"
    >
      <div v-if="bubbleOpen" class="pet-bubble overlay-bubble">{{ bubble }}</div>
      <div class="pet-figure" :class="mood">
        <span class="pet-shadow" />
        <span class="pet-ear left" />
        <span class="pet-ear right" />
        <div class="pet-body">
          <div class="pet-face">
            <span class="pet-eye left" />
            <span class="pet-eye right" />
            <span class="pet-blush left" />
            <span class="pet-blush right" />
            <span class="pet-mouth" />
          </div>
          <span class="pet-element">{{ pet?.element || '光' }}</span>
        </div>
        <span class="pet-tail" />
      </div>
      <div class="overlay-name">{{ pet?.name || 'Rocogi' }}</div>
    </div>
  </div>

  <div v-else class="page pet-page">
    <header class="page-head">
      <div>
        <div class="eyebrow">Pocket Companion</div>
        <h1>桌宠工坊</h1>
        <p class="page-sub">
          从 461 只本地图鉴精灵里挑一只，生成可拖动的桌面伙伴窗口。借鉴 rocom-codex-pets-gen 的精灵选择、动作状态与弹窗交互，纯 CSS 绘制，不依赖游戏素材。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary" :disabled="!pet" @click="openPetWindow">
          <AppIcon name="external" :size="14" /> 弹出桌宠窗口
        </button>
        <a
          class="chip primary"
          href="https://github.com/ElliottZhao666666/rocom-codex-pets-gen"
          target="_blank"
          rel="noreferrer"
        >
          <AppIcon name="external" :size="12" /> 参考仓库
        </a>
      </div>
    </header>

    <div class="pet-layout">
      <section class="panel roster-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="database" :size="15" /> 选择精灵</div>
          <span class="chip mono">{{ roster.length }}</span>
        </div>
        <div class="panel-body roster-body">
          <label class="pet-search">
            <AppIcon name="search" :size="13" />
            <input v-model="search" placeholder="搜索精灵名" @input="scheduleSearch" />
            <span v-if="loading" class="status-dot running" />
          </label>
          <div class="element-row">
            <button class="element-chip" :class="{ active: !element }" @click="element = ''; loadRoster()">全部</button>
            <button
              v-for="item in elements"
              :key="item.name"
              class="element-chip"
              :class="{ active: element === item.name }"
              :style="element === item.name ? { color: item.color, borderColor: `${item.color}44`, background: `${item.color}12` } : {}"
              @click="element = element === item.name ? '' : item.name; loadRoster()"
            >
              <i :style="{ background: item.color }" /> {{ item.name }}
            </button>
          </div>
          <div class="roster-grid">
            <button
              v-for="item in roster"
              :key="item.name"
              class="roster-item"
              :class="{ active: pet?.name === item.name }"
              :style="{ '--elem': item.elementColor }"
              @click="choose(item)"
            >
              <span class="roster-orb">{{ item.element }}</span>
              <strong>{{ item.name }}</strong>
              <span class="mono">{{ item.total }}</span>
            </button>
            <div v-if="!roster.length" class="empty-state roster-empty">
              <AppIcon name="search" :size="22" />
              <div>没有匹配的精灵</div>
            </div>
          </div>
        </div>
      </section>

      <section class="panel stage-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="spark" :size="15" /> 预览</div>
          <div class="stage-actions">
            <span class="chip mono">{{ pet?.stage || '精灵' }}</span>
            <span class="chip" :style="{ color: elementColor, borderColor: `${elementColor}44` }">{{ pet?.element || '光' }}系</span>
          </div>
        </div>
        <div class="pet-stage" :style="stageStyle">
          <div class="cloud cloud-a" />
          <div class="cloud cloud-b" />
          <div class="stage-hint mono">CLICK ME · DRAG IN POPUP</div>
          <div class="pet-figure-wrap" :style="{ transform: `scale(${size})` }">
            <div v-if="bubbleOpen" class="pet-bubble">{{ bubble }}</div>
            <div class="pet-figure" :class="mood" @click="tapPet">
              <span class="pet-shadow" />
              <span class="pet-ear left" />
              <span class="pet-ear right" />
              <div class="pet-body">
                <div class="pet-face">
                  <span class="pet-eye left" />
                  <span class="pet-eye right" />
                  <span class="pet-blush left" />
                  <span class="pet-blush right" />
                  <span class="pet-mouth" />
                </div>
                <span class="pet-element">{{ pet?.element || '光' }}</span>
              </div>
              <span class="pet-tail" />
            </div>
          </div>
          <div class="pet-nameplate">
            <span class="mono">{{ detail?.pokemon.spiritNo || 'NO.001' }}</span>
            <strong>{{ pet?.name || '迪莫' }}</strong>
            <span class="mono">种族值 {{ pet?.total || '—' }}</span>
          </div>
        </div>
        <div class="stage-foot">
          <div class="mood-buttons">
            <button class="btn btn-sm" :class="{ 'btn-primary': mood === 'idle' }" @click="setMood('idle')">待机</button>
            <button class="btn btn-sm" :class="{ 'btn-primary': mood === 'happy' }" @click="setMood('happy')">跳跃</button>
            <button class="btn btn-sm" :class="{ 'btn-primary': mood === 'sleep' }" @click="setMood('sleep')">睡觉</button>
          </div>
          <div class="size-control">
            <span>大小</span>
            <input v-model.number="size" type="range" min="0.72" max="1.35" step="0.01" />
            <span class="mono">{{ Math.round(size * 100) }}%</span>
          </div>
        </div>
      </section>

      <section class="panel info-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="battle" :size="15" /> 伙伴信息</div>
        </div>
        <div class="panel-body">
          <div class="pet-info-head">
            <div class="info-orb" :style="{ '--elem': elementColor }">{{ pet?.element || '光' }}</div>
            <div>
              <h3>{{ pet?.name || '迪莫' }}</h3>
              <div class="info-sub">{{ detail?.pokemon.spiritNo }} · {{ pet?.stage || '—' }}</div>
            </div>
          </div>
          <div class="ability-block">
            <b>{{ detail?.pokemon.ability.name || '暂无特性' }}</b>
            <p>{{ abilityText }}</p>
          </div>
          <div class="mini-stats">
            <div v-for="stat in detail?.pokemon.stats || []" :key="stat.key" class="mini-stat">
              <span>{{ stat.label }}</span>
              <div><i :style="{ width: `${Math.min(100, (stat.value / 200) * 100)}%`, background: stat.color }" /></div>
              <span class="mono">{{ stat.value }}</span>
            </div>
          </div>
          <div class="info-note">
            <AppIcon name="warning" :size="12" />
            弹窗为普通浏览器窗口，是否置顶取决于系统窗口管理器；真正的透明悬浮需要 Electron 或桌面宿主。
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.pet-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr) 280px;
  gap: 16px;
  align-items: start;
}

.roster-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 640px;
}

.pet-search {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 32px;
  padding: 0 9px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #fff;
}

.pet-search svg {
  color: var(--primary);
  flex: none;
}

.pet-search input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-size: 11px;
}

.element-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  max-height: 74px;
  overflow: auto;
}

.element-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 21px;
  padding: 0 7px;
  border: 1px solid var(--border-soft);
  border-radius: 999px;
  background: #fff;
  color: var(--muted);
  font-size: 9px;
}

.element-chip i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}

.element-chip.active {
  border-color: rgba(14, 165, 233, 0.3);
  color: var(--primary);
  background: rgba(14, 165, 233, 0.08);
}

.roster-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px;
  overflow: auto;
  padding-right: 2px;
  flex: 1;
}

.roster-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 6px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: #fff;
  text-align: left;
  transition: border-color 0.14s ease, background 0.14s ease;
}

.roster-item:hover {
  border-color: color-mix(in srgb, var(--elem) 38%, transparent);
}

.roster-item.active {
  border-color: color-mix(in srgb, var(--elem) 55%, transparent);
  background: color-mix(in srgb, var(--elem) 7%, white);
}

.roster-orb {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--elem) 16%, white);
  color: var(--elem);
  font-size: 8px;
  flex: none;
}

.roster-item strong {
  font-size: 9.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.roster-item .mono {
  margin-left: auto;
  font-size: 8px;
  color: var(--faint);
}

.roster-empty {
  grid-column: 1 / -1;
  padding: 24px 10px;
}

.stage-panel {
  overflow: hidden;
}

.stage-actions {
  display: flex;
  gap: 5px;
}

.pet-stage {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 520px;
  padding: 36px 20px 60px;
  background:
    radial-gradient(circle at 50% 22%, rgba(255, 255, 255, 0.9), transparent 34%),
    radial-gradient(circle at 18% 84%, color-mix(in srgb, var(--elem) 18%, transparent), transparent 42%),
    linear-gradient(180deg, #f7fcff 0%, #eaf7ff 58%, #dff1fd 100%);
  overflow: hidden;
}

.pet-stage::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 90px;
  background: linear-gradient(180deg, transparent, rgba(255, 255, 255, 0.72));
}

.cloud {
  position: absolute;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  filter: blur(1px);
}

.cloud-a {
  width: 180px;
  height: 58px;
  left: -30px;
  top: 90px;
  box-shadow: 40px 12px 0 -8px rgba(255, 255, 255, 0.6);
}

.cloud-b {
  width: 140px;
  height: 48px;
  right: -20px;
  top: 160px;
  opacity: 0.75;
}

.stage-hint {
  position: absolute;
  top: 16px;
  left: 18px;
  font-size: 8px;
  letter-spacing: 0.18em;
  color: var(--faint);
}

.pet-figure-wrap {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: transform 0.16s ease;
}

.pet-bubble {
  position: relative;
  max-width: 230px;
  padding: 8px 12px;
  margin-bottom: 16px;
  border: 1px solid color-mix(in srgb, var(--elem) 30%, transparent);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--text-soft);
  font-size: 10.5px;
  line-height: 1.5;
  text-align: center;
  box-shadow: 0 8px 20px rgba(42, 108, 140, 0.1);
}

.pet-bubble::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: -6px;
  width: 10px;
  height: 10px;
  transform: translateX(-50%) rotate(45deg);
  border-right: 1px solid color-mix(in srgb, var(--elem) 30%, transparent);
  border-bottom: 1px solid color-mix(in srgb, var(--elem) 30%, transparent);
  background: #fff;
}

.pet-figure {
  position: relative;
  width: 170px;
  height: 190px;
  cursor: pointer;
  animation: float 4.2s ease-in-out infinite;
  user-select: none;
}

.pet-shadow {
  position: absolute;
  left: 50%;
  bottom: 2px;
  width: 120px;
  height: 20px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--elem) 20%, transparent);
  transform: translateX(-50%);
  filter: blur(5px);
  animation: shadow 4.2s ease-in-out infinite;
}

.pet-body {
  position: absolute;
  left: 50%;
  top: 34px;
  width: 150px;
  height: 140px;
  border-radius: 50% 50% 46% 46%;
  background:
    radial-gradient(circle at 34% 24%, rgba(255, 255, 255, 0.92), transparent 34%),
    color-mix(in srgb, var(--elem) 24%, white);
  border: 1px solid color-mix(in srgb, var(--elem) 38%, transparent);
  transform: translateX(-50%);
  box-shadow:
    inset 0 -14px 26px color-mix(in srgb, var(--elem) 14%, transparent),
    0 16px 30px rgba(42, 108, 140, 0.12);
}

.pet-ear {
  position: absolute;
  top: 16px;
  width: 54px;
  height: 62px;
  background: color-mix(in srgb, var(--elem) 26%, white);
  border: 1px solid color-mix(in srgb, var(--elem) 36%, transparent);
  border-radius: 50% 50% 38% 38%;
  z-index: 0;
}

.pet-ear.left {
  left: 12px;
  transform: rotate(-22deg);
}

.pet-ear.right {
  right: 12px;
  transform: rotate(22deg);
}

.pet-ear::after {
  content: '';
  position: absolute;
  inset: 9px 10px;
  border-radius: inherit;
  background: rgba(255, 255, 255, 0.55);
}

.pet-face {
  position: absolute;
  left: 50%;
  top: 40px;
  width: 100px;
  height: 56px;
  transform: translateX(-50%);
}

.pet-eye {
  position: absolute;
  top: 8px;
  width: 14px;
  height: 16px;
  border-radius: 50%;
  background: #16384c;
  box-shadow: inset 0 -2px 0 rgba(255, 255, 255, 0.65);
}

.pet-eye.left {
  left: 18px;
}

.pet-eye.right {
  right: 18px;
}

.pet-eye::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 3px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #fff;
}

.pet-blush {
  position: absolute;
  top: 34px;
  width: 18px;
  height: 8px;
  border-radius: 50%;
  background: rgba(244, 114, 182, 0.38);
  filter: blur(1px);
}

.pet-blush.left {
  left: 4px;
}

.pet-blush.right {
  right: 4px;
}

.pet-mouth {
  position: absolute;
  left: 50%;
  top: 42px;
  width: 16px;
  height: 7px;
  transform: translateX(-50%);
  border-bottom: 2px solid #16384c;
  border-radius: 0 0 50% 50%;
}

.pet-element {
  position: absolute;
  right: 16px;
  bottom: 14px;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--elem) 38%, transparent);
  background: rgba(255, 255, 255, 0.82);
  color: var(--elem);
  font-size: 13px;
  font-weight: 700;
}

.pet-tail {
  position: absolute;
  right: 4px;
  bottom: 34px;
  width: 54px;
  height: 16px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--elem) 22%, white);
  border: 1px solid color-mix(in srgb, var(--elem) 30%, transparent);
  transform: rotate(-24deg);
  transform-origin: left center;
  animation: tail 2.8s ease-in-out infinite;
}

.pet-figure.happy {
  animation: hop 0.55s ease-in-out 2;
}

.pet-figure.sleep {
  animation: sleep 4.5s ease-in-out infinite;
}

.pet-figure.sleep .pet-eye {
  height: 3px;
  top: 14px;
  border-radius: 4px;
}

.pet-figure.sleep .pet-mouth {
  width: 10px;
  height: 0;
  border-bottom: none;
}

.pet-nameplate {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 24px;
  padding: 7px 12px;
  border: 1px solid var(--border-soft);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  font-size: 9px;
  color: var(--faint);
}

.pet-nameplate strong {
  font-size: 13px;
  color: var(--text);
}

.stage-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-soft);
  flex-wrap: wrap;
}

.mood-buttons {
  display: flex;
  gap: 5px;
}

.size-control {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 9px;
  color: var(--faint);
}

.size-control input {
  width: 90px;
  accent-color: var(--primary);
}

.info-panel .panel-body {
  padding-top: 14px;
}

.pet-info-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.info-orb {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--elem) 36%, transparent);
  background: color-mix(in srgb, var(--elem) 16%, white);
  color: var(--elem);
  font-size: 15px;
  font-weight: 700;
  flex: none;
}

.pet-info-head h3 {
  font-size: 16px;
}

.info-sub {
  margin-top: 2px;
  font-size: 9px;
  color: var(--faint);
}

.ability-block {
  margin-top: 13px;
  padding: 10px 11px;
  border: 1px solid var(--paper-muted);
  border-radius: 9px;
  background: linear-gradient(180deg, var(--paper-soft), #fff);
}

.ability-block b {
  font-size: 11px;
}

.ability-block p {
  margin-top: 3px;
  font-size: 9.5px;
  line-height: 1.6;
  color: var(--muted);
}

.mini-stats {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 13px;
}

.mini-stat {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr) 26px;
  align-items: center;
  gap: 6px;
  font-size: 8.5px;
  color: var(--muted);
}

.mini-stat > div {
  height: 5px;
  border-radius: 999px;
  background: #e6f2fa;
  overflow: hidden;
}

.mini-stat i {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.mini-stat .mono {
  text-align: right;
  font-size: 8px;
  color: var(--faint);
}

.info-note {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 14px;
  padding: 8px 9px;
  border-radius: 7px;
  background: rgba(251, 191, 36, 0.08);
  border: 1px solid rgba(217, 119, 6, 0.16);
  font-size: 8.5px;
  line-height: 1.55;
  color: var(--amber);
}

.info-note svg {
  flex: none;
  margin-top: 1px;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

@keyframes shadow {
  0%,
  100% {
    transform: translateX(-50%) scaleX(1);
    opacity: 0.75;
  }
  50% {
    transform: translateX(-50%) scaleX(0.86);
    opacity: 0.5;
  }
}

@keyframes hop {
  0%,
  100% {
    transform: translateY(0) scale(1);
  }
  45% {
    transform: translateY(-26px) scale(1.04, 0.96);
  }
}

@keyframes sleep {
  0%,
  100% {
    transform: translateY(0) rotate(-2deg);
  }
  50% {
    transform: translateY(4px) rotate(2deg);
  }
}

@keyframes tail {
  0%,
  100% {
    transform: rotate(-24deg);
  }
  50% {
    transform: rotate(-6deg);
  }
}

/* ---------------------------------------------------------------- overlay */
.pet-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at 50% 24%, rgba(255, 255, 255, 0.92), transparent 40%),
    radial-gradient(circle at 20% 86%, color-mix(in srgb, var(--elem) 20%, transparent), transparent 46%),
    linear-gradient(180deg, #f7fcff, #e6f5ff);
  overflow: hidden;
  user-select: none;
  touch-action: none;
}

.overlay-bar {
  position: absolute;
  top: 8px;
  left: 10px;
  right: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 8px;
  color: var(--faint);
}

.overlay-close {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border: 1px solid var(--border-soft);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.8);
  color: var(--muted);
}

.overlay-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 34%;
}

.overlay-states {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 2px;
  border: 1px solid var(--border-soft);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
}

.overlay-state-btn {
  padding: 2px 6px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--muted);
  font-size: 9px;
  line-height: 13px;
}

.overlay-state-btn:hover {
  color: var(--ink);
}

.overlay-state-btn.active {
  background: color-mix(in srgb, var(--elem) 26%, #fff);
  color: var(--ink);
  font-weight: 600;
}

.overlay-size {
  display: flex;
  align-items: center;
  gap: 2px;
  padding-left: 4px;
  border-left: 1px solid var(--border-soft);
  font-size: 9px;
}

.overlay-size-btn {
  width: 16px;
  height: 16px;
  border: 1px solid var(--border-soft);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  color: var(--muted);
  font-size: 10px;
  line-height: 1;
}

.overlay-size-btn:hover {
  color: var(--ink);
}

.overlay-close:hover {
  color: #be123c;
  border-color: rgba(225, 29, 72, 0.24);
}

.overlay-pet {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: grab;
  touch-action: none;
}

.overlay-pet:active {
  cursor: grabbing;
}

.overlay-bubble {
  margin-bottom: 12px;
}

.overlay-name {
  margin-top: 16px;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid var(--border-soft);
  font-size: 11px;
  font-weight: 600;
  color: var(--text-soft);
}

@media (max-width: 1200px) {
  .pet-layout {
    grid-template-columns: 260px minmax(0, 1fr);
  }

  .info-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 860px) {
  .pet-layout {
    grid-template-columns: 1fr;
  }

  .roster-body {
    max-height: 360px;
  }

  .pet-stage {
    min-height: 440px;
  }
}
</style>
