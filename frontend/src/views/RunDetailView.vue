<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { api, wsUrl, formatDuration, formatTime } from '../lib/api'
import { notify } from '../lib/toast'
import type { NodeContract, Run, RunEvent, Workflow } from '../types'

const route = useRoute()
const router = useRouter()
const run = ref<Run | null>(null)
const events = ref<RunEvent[]>([])
const workflow = ref<Workflow | null>(null)
const contracts = ref<NodeContract[]>([])
const tab = ref<'timeline' | 'logs'>('timeline')
const loading = ref(true)
let socket: WebSocket | null = null
let timer = 0

const logs = computed(() => events.value.filter((event) => ['log', 'node.failed', 'run.finished'].includes(event.type)))
const artifacts = computed(() => events.value.filter((event) => event.type === 'artifact'))
const timeline = computed(() =>
  events.value.filter((event) =>
    ['run.started', 'node.started', 'node.finished', 'node.failed', 'node.skipped', 'run.finished'].includes(event.type),
  ),
)

const nodeNames = computed<Record<string, string>>(() => {
  const names: Record<string, string> = {}
  for (const node of workflow.value?.graph.nodes || []) {
    const contract = contracts.value.find((item) => item.type === node.type)
    names[node.id] = node.title || contract?.title || node.type
  }
  return names
})

const stats = computed(() => {
  const raw = (run.value?.summary?.stats || {}) as Record<string, number>
  return [
    { label: 'Steps', value: raw.steps ?? 0, hint: '执行步数' },
    { label: 'Nodes', value: raw.nodeRuns ?? 0, hint: '节点次数' },
    { label: 'Captures', value: raw.captures ?? 0, hint: '截图' },
    { label: 'Actions', value: raw.actions ?? 0, hint: '键鼠动作' },
    { label: 'Matches', value: raw.matches ?? 0, hint: '模板命中' },
    { label: 'Evidence', value: artifacts.value.length, hint: '截图证据' },
  ]
})

const vars = computed(() => (run.value?.summary?.vars || {}) as Record<string, unknown>)
const nodeOutputs = computed(() => (run.value?.summary?.nodeOutputs || {}) as Record<string, Record<string, unknown>>)

const statusText = computed(
  () => ({ running: '运行中', succeeded: '已完成', failed: '失败', stopped: '已停止' })[run.value?.status || ''] || '加载中',
)

async function load() {
  const runId = String(route.params.id)
  try {
    const [detail, eventList] = await Promise.all([
      api<Run>(`/api/runs/${runId}`),
      api<RunEvent[]>(`/api/runs/${runId}/events`),
    ])
    run.value = detail
    events.value = eventList
    const [wf, catalog] = await Promise.all([
      api<Workflow>(`/api/workflows/${detail.workflowId}`),
      api<{ nodes: NodeContract[] }>('/api/nodes'),
    ])
    workflow.value = wf
    contracts.value = catalog.nodes
    if (detail.status === 'running') subscribe(runId)
  } catch (error) {
    notify(`加载运行详情失败：${error}`, 'error')
  } finally {
    loading.value = false
  }
}

function subscribe(runId: string) {
  if (socket) {
    socket.onclose = null
    socket.close()
  }
  socket = new WebSocket(wsUrl(`/api/ws/runs/${runId}?after=${events.value.length ? events.value[events.value.length - 1].seq : 0}`))
  socket.onmessage = (message) => {
    try {
      const event = JSON.parse(message.data) as RunEvent
      if (events.value.some((item) => item.seq === event.seq)) return
      events.value.push(event)
      if (event.type === 'run.finished') {
        const status = (event.data as any)?.status || 'succeeded'
        if (run.value) run.value = { ...run.value, status }
        window.setTimeout(() => refreshRun(runId), 400)
        socket?.close()
      }
    } catch {
      /* ignore */
    }
  }
  timer = window.setInterval(() => {
    if (run.value?.status === 'running') refreshRun(runId)
  }, 2500)
}

async function refreshRun(runId: string) {
  try {
    const detail = await api<Run>(`/api/runs/${runId}`)
    run.value = detail
    if (detail.status !== 'running') {
      window.clearInterval(timer)
      const eventList = await api<RunEvent[]>(`/api/runs/${runId}/events`)
      events.value = eventList
    }
  } catch {
    /* ignore */
  }
}

async function stopRun() {
  if (!run.value) return
  try {
    await api(`/api/runs/${run.value.id}/stop`, { method: 'POST', body: '{}' })
    notify('已发送停止请求', 'info')
  } catch (error) {
    notify(`停止失败：${error}`, 'error')
  }
}

function timeOf(ts: string): string {
  const date = new Date(ts)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleTimeString('zh-CN', { hour12: false })
}

function iconFor(event: RunEvent): string {
  if (event.type === 'node.failed') return 'warning'
  if (event.type === 'run.finished') return 'check'
  if (event.type === 'node.started') return 'play'
  if (event.type === 'artifact') return 'image'
  return 'dot'
}

function nameOf(nodeId?: string | null): string {
  if (!nodeId) return '运行'
  return nodeNames.value[nodeId] || nodeId
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

onMounted(load)

onBeforeUnmount(() => {
  window.clearInterval(timer)
  if (socket) {
    socket.onclose = null
    socket.close()
  }
})
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <div class="eyebrow">Run Evidence</div>
        <div class="title-row">
          <button class="icon-btn" title="返回运行记录" @click="router.push('/runs')">
            <AppIcon name="arrowLeft" :size="16" />
          </button>
          <h1 class="run-title">{{ run?.workflowName || '运行详情' }}</h1>
          <span class="status-dot" :class="run?.status || 'running'" />
          <span class="chip" :class="run?.status === 'running' ? 'primary' : run?.status === 'failed' ? 'danger' : 'success'">{{ statusText }}</span>
        </div>
        <p class="page-sub mono run-meta">
          {{ run?.id }} · 开始 {{ formatTime(run?.startedAt) }} · 耗时 {{ formatDuration(run?.durationMs) }}
        </p>
      </div>
      <div class="page-actions">
        <button v-if="run?.status === 'running'" class="btn btn-danger" @click="stopRun">
          <AppIcon name="stop" :size="14" /> 停止
        </button>
        <button class="btn" @click="refreshRun(String(route.params.id))">
          <AppIcon name="refresh" :size="14" /> 刷新
        </button>
        <button class="btn btn-primary" @click="router.push(`/workflows/${run?.workflowId}`)">
          <AppIcon name="panel" :size="14" /> 打开工作流
        </button>
      </div>
    </header>

    <div v-if="run?.error" class="error-banner">
      <AppIcon name="warning" :size="16" />
      <div>
        <div class="error-title">运行失败</div>
        <div class="error-msg">{{ run.error }}</div>
      </div>
    </div>

    <div class="stat-grid" style="margin-bottom: 20px">
      <div v-for="stat in stats" :key="stat.label" class="stat-cell">
        <div class="stat-label">{{ stat.label }}</div>
        <div class="stat-value">{{ stat.value }}<small>{{ stat.hint }}</small></div>
      </div>
    </div>

    <div class="detail-layout">
      <section class="panel timeline-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="activity" :size="15" /> 运行轨迹</div>
          <div class="tab-switch">
            <button :class="{ active: tab === 'timeline' }" @click="tab = 'timeline'">时间线</button>
            <button :class="{ active: tab === 'logs' }" @click="tab = 'logs'">日志</button>
          </div>
        </div>
        <div class="panel-body scroll-body">
          <div v-if="tab === 'timeline'" class="timeline">
            <div v-for="event in timeline" :key="event.seq" class="timeline-row" :class="event.type">
              <span class="tl-seq mono">{{ String(event.seq).padStart(3, '0') }}</span>
              <span class="tl-time mono">{{ timeOf(event.ts) }}</span>
              <span class="tl-icon"><AppIcon :name="iconFor(event)" :size="13" /></span>
              <span class="tl-node">{{ nameOf(event.nodeId) }}</span>
              <span class="tl-msg">{{ event.message }}</span>
              <span class="tl-dur mono">{{ (event.data as any)?.durationMs ? `${(event.data as any).durationMs}ms` : '' }}</span>
            </div>
            <div v-if="!timeline.length" class="empty-state">没有节点事件。</div>
          </div>
          <div v-else class="console">
            <div v-for="event in logs" :key="event.seq" class="console-line" :class="event.type">
              <span class="mono console-time">{{ timeOf(event.ts) }}</span>
              <span class="mono console-level">{{ event.type === 'log' ? ((event.data as any)?.level || 'info') : event.type }}</span>
              <span>{{ event.message }}</span>
            </div>
            <div v-if="!logs.length" class="empty-state">没有日志。</div>
          </div>
        </div>
      </section>

      <aside class="side-col">
        <section class="panel">
          <div class="panel-head">
            <div class="panel-title"><AppIcon name="database" :size="15" /> 运行变量</div>
            <span class="chip mono">{{ Object.keys(vars).length }}</span>
          </div>
          <div class="panel-body">
            <div v-if="Object.keys(vars).length" class="var-list">
              <div v-for="(value, key) in vars" :key="String(key)" class="var-row">
                <span class="mono var-key">{{ key }}</span>
                <span class="mono var-value">{{ formatValue(value) }}</span>
              </div>
            </div>
            <div v-else class="muted" style="font-size: 11px">没有写入变量。</div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div class="panel-title"><AppIcon name="workflow" :size="15" /> 节点输出</div>
            <span class="chip mono">{{ Object.keys(nodeOutputs).length }}</span>
          </div>
          <div class="panel-body output-scroll">
            <div v-for="(output, nodeId) in nodeOutputs" :key="String(nodeId)" class="node-output">
              <div class="output-head">
                <span class="output-node">{{ nameOf(String(nodeId)) }}</span>
                <span class="mono faint">{{ nodeId }}</span>
              </div>
              <div v-for="(value, key) in output" :key="String(key)" class="output-line">
                <span class="mono output-key">{{ key }}</span>
                <span class="mono output-val">{{ formatValue(value) }}</span>
              </div>
            </div>
            <div v-if="!Object.keys(nodeOutputs).length" class="muted" style="font-size: 11px">没有节点输出。</div>
          </div>
        </section>
      </aside>
    </div>

    <section class="panel evidence-panel">
      <div class="panel-head">
        <div class="panel-title"><AppIcon name="image" :size="15" /> 截图证据</div>
        <span class="chip mono">{{ artifacts.length }}</span>
      </div>
      <div class="panel-body">
        <div v-if="artifacts.length" class="evidence-grid">
          <a
            v-for="event in artifacts"
            :key="event.seq"
            class="evidence-card"
            :href="(event.data as any)?.url"
            target="_blank"
            rel="noreferrer"
          >
            <img :src="(event.data as any)?.url" :alt="event.message" loading="lazy" />
            <div class="evidence-caption">
              <span>{{ nameOf(event.nodeId) }} · {{ event.message }}</span>
              <span class="mono">{{ timeOf(event.ts) }}</span>
            </div>
          </a>
        </div>
        <div v-else class="empty-state" style="padding: 28px">本次运行没有截图证据。</div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.run-title {
  font-size: clamp(24px, 2.2vw, 32px);
}

.run-meta {
  font-size: 10.5px;
  color: var(--faint);
  margin-top: 8px;
}

.icon-btn {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.02);
  color: var(--muted);
}

.icon-btn:hover {
  color: var(--text);
  border-color: #31455a;
}

.error-banner {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 13px 16px;
  border-radius: 10px;
  border: 1px solid rgba(248, 113, 113, 0.28);
  background: rgba(248, 113, 113, 0.06);
  color: #fca5a5;
  margin-bottom: 18px;
}

.error-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.error-msg {
  margin-top: 3px;
  font-size: 11.5px;
  color: #fecaca;
  font-family: var(--mono);
}

.detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 16px;
  margin-bottom: 16px;
}

.timeline-panel {
  min-height: 400px;
  display: flex;
  flex-direction: column;
}

.tab-switch {
  display: flex;
  gap: 2px;
  padding: 3px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-soft);
}

.tab-switch button {
  padding: 3px 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  font-size: 10.5px;
}

.tab-switch button.active {
  background: rgba(14, 165, 233, 0.12);
  color: var(--primary);
}

.scroll-body {
  flex: 1;
  overflow: auto;
  max-height: 520px;
  padding: 10px 16px 16px;
}

.timeline-row {
  display: grid;
  grid-template-columns: 30px 62px 18px minmax(90px, 140px) minmax(0, 1fr) 50px;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid rgba(214, 234, 245, 0.5);
  font-size: 10.5px;
}

.tl-seq,
.tl-time {
  color: var(--faint);
  font-size: 9px;
}

.tl-icon {
  display: grid;
  place-items: center;
  color: var(--muted);
}

.timeline-row.node\.started .tl-icon {
  color: var(--primary);
}

.timeline-row.run\.finished .tl-icon,
.timeline-row.node\.finished .tl-icon {
  color: var(--success);
}

.timeline-row.node\.failed .tl-icon {
  color: var(--danger);
}

.tl-node {
  font-weight: 550;
  color: var(--text-soft);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tl-msg {
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tl-dur {
  text-align: right;
  color: var(--faint);
  font-size: 8.5px;
}

.console {
  font-family: var(--mono);
  font-size: 10px;
  line-height: 1.8;
}

.console-line {
  display: grid;
  grid-template-columns: 66px 52px minmax(0, 1fr);
  gap: 8px;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-soft);
}

.console-time {
  color: var(--faint);
}

.console-level {
  color: var(--primary);
  font-size: 8.5px;
  text-transform: uppercase;
}

.console-line.node\.failed {
  color: #fca5a5;
}

.console-line.node\.failed .console-level {
  color: var(--danger);
}

.side-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.var-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.var-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(214, 234, 245, 0.5);
  font-size: 10px;
}

.var-key {
  color: var(--primary);
}

.var-value {
  color: var(--muted);
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.output-scroll {
  max-height: 240px;
  overflow: auto;
}

.node-output + .node-output {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(214, 234, 245, 0.6);
}

.output-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.output-node {
  font-size: 10.5px;
  font-weight: 600;
  color: var(--text-soft);
}

.output-head .mono {
  font-size: 8.5px;
}

.output-line {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 8px;
  font-size: 9px;
  padding: 1px 0;
}

.output-key {
  color: var(--faint);
  overflow: hidden;
  text-overflow: ellipsis;
}

.output-val {
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.evidence-panel {
  margin-bottom: 10px;
}

.evidence-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.evidence-card {
  display: block;
  border: 1px solid var(--border-soft);
  border-radius: 9px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.02);
  transition: border-color 0.15s ease, transform 0.15s ease;
}

.evidence-card:hover {
  border-color: rgba(14, 165, 233, 0.3);
  transform: translateY(-1px);
}

.evidence-card img {
  width: 100%;
  display: block;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  background: var(--panel-3);
}

.evidence-caption {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 7px 9px;
  font-size: 9.5px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
}

.evidence-caption .mono {
  color: var(--faint);
  flex: none;
}

@media (max-width: 1100px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }
}
</style>
