<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../lib/api'
import { refreshMeta } from '../lib/store'
import { notify } from '../lib/toast'
import type { RealtimeStatus } from '../types'

const status = ref<RealtimeStatus | null>(null)
const busy = ref(false)
const config = reactive({
  interval: 0.6,
  auto_ball: true,
  battle_response: true,
  party_confirm: true,
  normal_strategy: 'gather',
  polluted_strategy: 'escape',
  threshold: 0.45,
  save_screenshots: true,
  capture_retries: 3,
  capture_verify: 1.2,
  capture_pan: true,
  capture_pan_steps: 6,
  capture_pan_pixels: 90,
})
let timer = 0
let configLoaded = false

const sceneLabels: Record<string, string> = {
  field_pet: '野外 · 可捕捉精灵',
  battle_normal: '普通战斗',
  battle_polluted: '污染战斗',
  party_confirm: '同行请求',
  field: '野外',
  map: '地图',
  unknown: '未知',
}

const previewUrl = computed(() => status.value?.latestUrl || '')

const scoreRows = computed(() => {
  const scores = status.value?.scores || {}
  return Object.entries(scores)
    .map(([key, value]) => ({ key, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 4)
})

async function load() {
  try {
    const data = await api<RealtimeStatus>('/api/realtime/status')
    status.value = data
    if (!configLoaded && data.config) {
      Object.assign(config, data.config)
      configLoaded = true
    }
  } catch (error) {
    notify(`读取实时任务状态失败：${error}`, 'error')
  }
}

async function poll() {
  try {
    const data = await api<RealtimeStatus>('/api/realtime/status')
    status.value = data
  } catch {
    /* keep last */
  }
}

async function start() {
  busy.value = true
  try {
    // 本地优先：把当前捕获配置写回本机设置，F9 热键启动与下次进入页面都用这一份
    try {
      await api('/api/settings', { method: 'PUT', body: JSON.stringify({ realtime: { ...config } }) })
    } catch {
      /* 设置写回失败不阻塞启动 */
    }
    status.value = await api<RealtimeStatus>('/api/realtime/start', {
      method: 'POST',
      body: JSON.stringify({ config }),
    })
    notify('实时任务已启动', 'success')
    refreshMeta()
  } catch (error) {
    notify(`启动失败：${error}`, 'error')
  } finally {
    busy.value = false
  }
}

async function stop() {
  busy.value = true
  try {
    status.value = await api<RealtimeStatus>('/api/realtime/stop', { method: 'POST', body: '{}' })
    notify('实时任务已停止', 'info')
    refreshMeta()
  } catch (error) {
    notify(`停止失败：${error}`, 'error')
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  await load()
  timer = window.setInterval(poll, 1000)
})

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <div class="page realtime-page">
    <header class="page-head">
      <div>
        <div class="eyebrow">Real-time Triggers</div>
        <div class="title-row">
          <h1>实时任务</h1>
          <span class="status-dot" :class="status?.running ? 'running' : 'idle'" />
          <span class="chip" :class="status?.running ? 'primary' : ''">{{
            status?.running ? '运行中' : '待启动'
          }}</span>
        </div>
        <p class="page-sub">
          持续截取当前目标，识别普通/污染战斗、可捕捉精灵与同行请求，并按配置自动执行按键或点击。对应 BetterGI 的实时触发页。
        </p>
      </div>
      <div class="page-actions">
        <button v-if="!status?.running" class="btn btn-primary" :disabled="busy" @click="start">
          <AppIcon name="play" :size="14" /> {{ busy ? '启动中...' : '启动实时任务' }}
        </button>
        <button v-else class="btn btn-danger" :disabled="busy" @click="stop">
          <AppIcon name="stop" :size="14" /> 停止
        </button>
      </div>
    </header>

    <div class="stat-grid" :class="{ 'stat-grid-stale': !status?.running && (status?.counters.ticks || 0) > 0 }" style="margin-bottom: 18px">
      <div v-if="!status?.running && (status?.counters.ticks || 0) > 0" class="stat-stale-badge">上次会话</div>
      <div class="stat-cell">
        <div class="stat-label">Frames</div>
        <div class="stat-value">{{ status?.counters.ticks || 0 }}<small>识别帧</small></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">Actions</div>
        <div class="stat-value">{{ status?.counters.actions || 0 }}<small>键鼠动作</small></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">Battles</div>
        <div class="stat-value">{{ status?.counters.battles || 0 }}<small>战斗处理</small></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">Balls</div>
        <div class="stat-value">{{ status?.counters.balls || 0 }}<small>自动丢球</small></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">Confirms</div>
        <div class="stat-value">{{ status?.counters.confirms || 0 }}<small>同行确认</small></div>
      </div>
    </div>

    <div class="realtime-grid">
      <section class="panel preview-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="image" :size="15" /> 实时画面</div>
          <div class="preview-badges">
            <span class="chip primary">{{ sceneLabels[status?.scene || 'unknown'] || status?.scene }}</span>
            <span v-if="status?.phase" class="chip mono">{{ status.phase }}</span>
            <span v-if="status?.running" class="chip"><span class="status-dot running" /> 持续采集中</span>
          </div>
        </div>
        <div class="preview-body">
          <img v-if="previewUrl" :src="previewUrl" class="live-image" alt="实时识别画面" />
          <div v-else class="preview-empty">
            <div class="preview-empty-icon"><AppIcon name="crosshair" :size="28" /></div>
            <div>启动实时任务后，这里会显示最新识别画面与命中框。</div>
            <div class="faint mono">模拟目标会自动轮播野外、战斗与同行请求场景</div>
          </div>
          <div v-if="status?.error" class="preview-error">{{ status.error }}</div>
          <div v-if="status?.running" class="scan-line" />
          <div class="preview-overlay">
            <span class="mono">{{ status?.startedAt ? 'LIVE' : 'STANDBY' }}</span>
            <span class="mono">{{ status?.counters.ticks || 0 }} frames</span>
          </div>
        </div>
      </section>

      <section class="panel config-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="settings" :size="15" /> 触发配置</div>
          <span class="chip mono">{{ config.interval.toFixed(1) }}s</span>
        </div>
        <div class="panel-body">
          <div class="toggle-row">
            <div>
              <div class="field-label">自动丢球</div>
              <div class="field-help">识别到可捕捉精灵或交易请求时按 X。</div>
            </div>
            <div class="toggle" :class="{ on: config.auto_ball }" @click="config.auto_ball = !config.auto_ball" />
          </div>
          <div class="toggle-row">
            <div>
              <div class="field-label">战斗应对</div>
              <div class="field-help">按普通/污染战斗执行不同策略。</div>
            </div>
            <div class="toggle" :class="{ on: config.battle_response }" @click="config.battle_response = !config.battle_response" />
          </div>
          <div class="toggle-row">
            <div>
              <div class="field-label">同行确认</div>
              <div class="field-help">检测到同行请求时按 F。</div>
            </div>
            <div class="toggle" :class="{ on: config.party_confirm }" @click="config.party_confirm = !config.party_confirm" />
          </div>

          <div class="field" style="margin-top: 14px">
            <div class="field-label">普通战斗策略</div>
            <select v-model="config.normal_strategy" class="select">
              <option value="gather">只聚能（X）</option>
              <option value="skill1_gather">技能1 后聚能</option>
              <option value="escape">逃跑（ESC + 确认）</option>
              <option value="none">不操作</option>
            </select>
          </div>
          <div class="field">
            <div class="field-label">污染战斗策略</div>
            <select v-model="config.polluted_strategy" class="select">
              <option value="escape">逃跑（ESC + 确认）</option>
              <option value="gather">只聚能（X）</option>
              <option value="skill1_gather">技能1 后聚能</option>
              <option value="none">不操作</option>
            </select>
          </div>
          <div class="field">
            <div class="field-label">识别阈值 <span class="mono">{{ config.threshold.toFixed(2) }}</span></div>
            <input v-model.number="config.threshold" type="range" min="0.2" max="0.9" step="0.01" class="range" />
          </div>
          <div class="field">
            <div class="field-label">采帧间隔（秒）</div>
            <input v-model.number="config.interval" type="number" min="0.2" max="5" step="0.1" class="input" />
          </div>

          <div class="config-section-label">
            <AppIcon name="target" :size="12" /> 捕捉策略 · AutoCapture 参考
          </div>
          <div class="field-row">
            <div class="field">
              <div class="field-label">最大丢球次数</div>
              <input v-model.number="config.capture_retries" type="number" min="1" max="10" step="1" class="input" />
            </div>
            <div class="field">
              <div class="field-label">结果验证等待（秒）</div>
              <input v-model.number="config.capture_verify" type="number" min="0.3" max="5" step="0.1" class="input" />
            </div>
          </div>
          <div class="toggle-row">
            <div>
              <div class="field-label">空视野自动搜索</div>
              <div class="field-help">连续空扫描后平移视角寻找精灵。</div>
            </div>
            <div class="toggle" :class="{ on: config.capture_pan }" @click="config.capture_pan = !config.capture_pan" />
          </div>
          <div v-if="config.capture_pan" class="field-row">
            <div class="field">
              <div class="field-label">搜索步数</div>
              <input v-model.number="config.capture_pan_steps" type="number" min="1" max="20" step="1" class="input" />
            </div>
            <div class="field">
              <div class="field-label">每步像素</div>
              <input v-model.number="config.capture_pan_pixels" type="number" min="10" max="600" step="10" class="input" />
            </div>
          </div>
          <div class="capture-status mono">
            phase {{ status?.phase || 'idle' }} · 尝试 {{ status?.capture?.attempts || 0 }} · 空扫描
            {{ status?.capture?.emptyScans || 0 }} · 搜索 {{ status?.capture?.panCount || 0 }}
          </div>

          <div class="config-foot">
            <button v-if="!status?.running" class="btn btn-primary" style="width: 100%" :disabled="busy" @click="start">
              <AppIcon name="play" :size="14" /> 应用并启动
            </button>
            <button v-else class="btn btn-danger" style="width: 100%" :disabled="busy" @click="stop">
              <AppIcon name="stop" :size="14" /> 停止实时任务
            </button>
          </div>
        </div>
      </section>
    </div>

    <div class="lower-grid">
      <section class="panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="activity" :size="15" /> 识别分数</div>
        </div>
        <div class="panel-body">
          <div v-for="row in scoreRows" :key="row.key" class="score-row">
            <span class="score-name mono">{{ row.key }}</span>
            <div class="score-track">
              <span class="score-fill" :style="{ width: `${Math.round(row.value * 100)}%` }" />
            </div>
            <span class="score-value mono">{{ row.value.toFixed(3) }}</span>
          </div>
          <div v-if="!scoreRows.length" class="muted" style="font-size: 11px">启动后会显示各模板的匹配分数。</div>
        </div>
      </section>

      <section class="panel log-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="runs" :size="15" /> 运行日志</div>
          <span class="chip mono">{{ status?.logs?.length || 0 }}</span>
        </div>
        <div class="panel-body log-body">
          <div v-for="(log, index) in status?.logs || []" :key="index" class="log-line" :class="log.kind">
            <span class="mono log-time">{{ new Date(log.ts).toLocaleTimeString('zh-CN', { hour12: false }) }}</span>
            <span class="mono log-kind">{{ log.kind }}</span>
            <span>{{ log.message }}</span>
          </div>
          <div v-if="!status?.logs?.length" class="muted" style="font-size: 11px">
            启动实时任务后，这里会显示识别与动作日志。
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-grid {
  position: relative;
}

/* 停止后计数器保留的是上一轮统计，这里压暗并加角标，避免误读成当前会话。 */
.stat-grid-stale :deep(.stat-value),
.stat-grid-stale .stat-value {
  opacity: 0.5;
}

.stat-stale-badge {
  position: absolute;
  top: -9px;
  right: 10px;
  z-index: 2;
  padding: 1px 7px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--rk-on-paper) 16%, transparent);
  background: var(--rk-paper);
  color: color-mix(in srgb, var(--rk-on-paper) 60%, transparent);
  font-size: 10px;
  letter-spacing: 0.08em;
}

.realtime-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 16px;
}

.preview-panel {
  overflow: hidden;
}

.preview-badges {
  display: flex;
  align-items: center;
  gap: 6px;
}

.preview-body {
  position: relative;
  aspect-ratio: 16 / 8.4;
  min-height: 320px;
  background: #f2faff;
  overflow: hidden;
}

.live-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.preview-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--muted);
  font-size: 12px;
  text-align: center;
  padding: 20px;
}

.preview-empty-icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  color: var(--primary);
  background: rgba(14, 165, 233, 0.07);
  border: 1px solid rgba(14, 165, 233, 0.14);
  margin-bottom: 4px;
}

.preview-overlay {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 10px;
  display: flex;
  justify-content: space-between;
  color: rgba(220, 245, 240, 0.7);
  font-size: 9px;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.8);
  pointer-events: none;
}

.preview-error {
  position: absolute;
  left: 12px;
  right: 12px;
  top: 12px;
  padding: 8px 10px;
  border-radius: 7px;
  background: rgba(225, 29, 72, 0.08);
  border: 1px solid rgba(225, 29, 72, 0.22);
  color: #be123c;
  font-size: 10.5px;
}

.scan-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(14, 165, 233, 0.55), transparent);
  animation: scan 3.2s linear infinite;
  pointer-events: none;
}

@keyframes scan {
  0% {
    top: 8%;
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    top: 92%;
    opacity: 0;
  }
}

.config-panel .panel-body {
  padding-top: 8px;
}

.config-section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 16px 0 8px;
  padding-top: 12px;
  border-top: 1px dashed var(--border-soft);
  font-size: 9.5px;
  letter-spacing: 0.08em;
  color: var(--primary);
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.capture-status {
  margin-top: 10px;
  padding: 7px 9px;
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  background: rgba(246, 252, 255, 0.9);
  font-size: 9px;
  color: var(--faint);
}

.config-foot {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--border-soft);
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
  border: 2px solid #fff;
  box-shadow: 0 2px 6px rgba(14, 116, 144, 0.24);
}

.lower-grid {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 16px;
  margin-top: 16px;
}

.score-row {
  display: grid;
  grid-template-columns: 80px minmax(0, 1fr) 48px;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
}

.score-name {
  font-size: 9px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
}

.score-track {
  height: 4px;
  background: rgba(14, 165, 233, 0.09);
  border-radius: 999px;
  overflow: hidden;
}

.score-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(14, 165, 233, 0.4), var(--primary));
  transition: width 0.3s ease;
}

.score-value {
  font-size: 9px;
  color: var(--faint);
  text-align: right;
}

.log-body {
  max-height: 220px;
  overflow: auto;
  font-family: var(--mono);
  font-size: 10px;
  line-height: 1.8;
}

.log-line {
  display: grid;
  grid-template-columns: 64px 58px minmax(0, 1fr);
  gap: 8px;
  border-bottom: 1px solid rgba(214, 234, 245, 0.45);
  padding: 2px 0;
  color: var(--text-soft);
}

.log-time {
  color: var(--faint);
}

.log-kind {
  color: var(--primary);
  font-size: 9px;
  text-transform: uppercase;
}

.log-line.error,
.log-line.warn {
  color: #be123c;
}

.log-line.error .log-kind,
.log-line.warn .log-kind {
  color: var(--danger);
}

@media (max-width: 1100px) {
  .realtime-grid,
  .lower-grid {
    grid-template-columns: 1fr;
  }
}
</style>
