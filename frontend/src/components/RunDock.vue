<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import { formatDuration, formatTime } from '../lib/api'
import type { Run, RunEvent } from '../types'

const props = defineProps<{
  open: boolean
  run: Run | null
  events: RunEvent[]
  nodeNames: Record<string, string>
}>()

const emit = defineEmits<{
  close: []
  stop: []
}>()

const tab = ref<'timeline' | 'logs' | 'artifacts' | 'vars'>('timeline')
const listRef = ref<HTMLDivElement | null>(null)

const logs = computed(() =>
  props.events.filter((event) => ['log', 'node.failed', 'run.finished'].includes(event.type)),
)

const artifacts = computed(() => props.events.filter((event) => event.type === 'artifact'))

const timeline = computed(() =>
  props.events.filter((event) =>
    [
      'run.started',
      'node.started',
      'node.finished',
      'node.failed',
      'node.skipped',
      'run.finished',
    ].includes(event.type),
  ),
)

const liveVars = computed<Record<string, unknown>>(() => {
  const vars: Record<string, unknown> = { ...(props.run?.summary?.vars || {}) }
  for (const event of props.events) {
    if (event.type !== 'node.finished') continue
    const data = event.data as any
    if (data?.type !== 'flow.set_var') continue
    Object.assign(vars, data.outputs || {})
  }
  return vars
})

const statusText = computed(() => {
  switch (props.run?.status) {
    case 'running':
      return '运行中'
    case 'succeeded':
      return '已完成'
    case 'failed':
      return '失败'
    case 'stopped':
      return '已停止'
    default:
      return '未运行'
  }
})

const elapsed = computed(() => {
  if (props.run?.durationMs) return formatDuration(props.run.durationMs)
  if (props.run?.startedAt) {
    const ms = Date.now() - new Date(props.run.startedAt).getTime()
    return formatDuration(Math.max(0, ms))
  }
  return '—'
})

function timeOf(ts: string): string {
  const date = new Date(ts)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

function iconFor(event: RunEvent): string {
  if (event.type === 'node.failed') return 'warning'
  if (event.type === 'run.finished') return 'check'
  if (event.type === 'node.started') return 'play'
  if (event.type === 'artifact') return 'image'
  return 'dot'
}

function eventClass(event: RunEvent): string {
  if (event.type === 'node.failed' || event.type === 'run.finished' && (event.data as any)?.status === 'failed') return 'error'
  if (event.type === 'run.finished') return 'done'
  if (event.type === 'node.started') return 'start'
  return ''
}

function nameOf(nodeId?: string | null): string {
  if (!nodeId) return '运行'
  return props.nodeNames[nodeId] || nodeId
}

watch(
  () => props.events.length,
  async () => {
    if (tab.value !== 'timeline' && tab.value !== 'logs') return
    await nextTick()
    if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
  },
)

const tabs = computed(() => [
  { id: 'timeline' as const, label: '时间线', count: timeline.value.length },
  { id: 'logs' as const, label: '日志', count: logs.value.length },
  { id: 'artifacts' as const, label: '截图', count: artifacts.value.length },
  { id: 'vars' as const, label: '变量', count: Object.keys(liveVars.value).length },
])
</script>

<template>
  <div v-if="open" class="dock">
    <div class="dock-head">
      <div class="dock-title">
        <span class="status-dot" :class="run?.status || 'idle'" />
        <span class="dock-name">{{ run?.workflowName || '运行控制台' }}</span>
        <span class="chip" :class="run?.status === 'running' ? 'primary' : ''">{{ statusText }}</span>
        <span class="mono faint dock-id">{{ run?.id || '等待运行' }}</span>
      </div>
      <div class="dock-meta">
        <span class="mono">{{ elapsed }}</span>
        <span v-if="run" class="faint" style="font-size: 10px">{{ formatTime(run.startedAt) }}</span>
        <button v-if="run?.status === 'running'" class="btn btn-sm btn-danger" @click="emit('stop')">
          <AppIcon name="stop" :size="12" /> 停止
        </button>
        <button class="icon-btn" @click="emit('close')"><AppIcon name="chevron" :size="14" /></button>
      </div>
    </div>

    <div class="dock-tabs">
      <button
        v-for="item in tabs"
        :key="item.id"
        class="dock-tab"
        :class="{ active: tab === item.id }"
        @click="tab = item.id"
      >
        {{ item.label }}
        <span class="tab-count mono">{{ item.count }}</span>
      </button>
    </div>

    <div ref="listRef" class="dock-body">
      <div v-if="!run" class="dock-empty">运行一个工作流后，这里会显示实时节点时间线。</div>

      <div v-else-if="tab === 'timeline'" class="timeline">
        <div v-for="event in timeline" :key="event.seq" class="timeline-row" :class="eventClass(event)">
          <span class="tl-time mono">{{ timeOf(event.ts) }}</span>
          <span class="tl-icon"><AppIcon :name="iconFor(event)" :size="12" /></span>
          <span class="tl-node">{{ nameOf(event.nodeId) }}</span>
          <span class="tl-msg">{{ event.message }}</span>
          <span v-if="(event.data as any)?.durationMs" class="tl-duration mono">{{ (event.data as any).durationMs }}ms</span>
        </div>
        <div v-if="run.status === 'running'" class="live-row">
          <span class="live-dot" /> 等待下一个节点事件
        </div>
      </div>

      <div v-else-if="tab === 'logs'" class="console">
        <div v-for="event in logs" :key="event.seq" class="console-line" :class="eventClass(event)">
          <span class="mono console-time">{{ timeOf(event.ts) }}</span>
          <span class="mono console-level">{{ event.type === 'log' ? ((event.data as any)?.level || 'info') : event.type }}</span>
          <span>{{ event.message }}</span>
        </div>
        <div v-if="!logs.length" class="dock-empty">暂无日志。</div>
      </div>

      <div v-else-if="tab === 'artifacts'" class="artifacts">
        <a
          v-for="event in artifacts"
          :key="event.seq"
          class="artifact-card"
          :href="(event.data as any)?.url"
          target="_blank"
          rel="noreferrer"
        >
          <img :src="(event.data as any)?.url" :alt="event.message" loading="lazy" />
          <span class="artifact-caption">
            <span>{{ event.message }}</span>
            <span class="mono">{{ timeOf(event.ts) }}</span>
          </span>
        </a>
        <div v-if="!artifacts.length" class="dock-empty">本次运行还没有截图证据。</div>
      </div>

      <div v-else class="vars">
        <table class="vars-table">
          <thead>
            <tr><th>变量</th><th>值</th></tr>
          </thead>
          <tbody>
            <tr v-for="(value, key) in liveVars" :key="String(key)">
              <td class="mono var-key">{{ key }}</td>
              <td class="mono">{{ typeof value === 'object' ? JSON.stringify(value) : String(value) }}</td>
            </tr>
            <tr v-if="!Object.keys(liveVars).length">
              <td colspan="2" class="dock-empty" style="padding: 16px">暂无变量。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dock {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 260px;
  border-top: 1px solid var(--border-soft);
  background: rgba(255, 255, 255, 0.96);
  animation: dock-in 0.2s ease both;
}

@keyframes dock-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dock-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-soft);
}

.dock-title,
.dock-meta {
  display: flex;
  align-items: center;
  gap: 9px;
}

.dock-name {
  font-size: 12px;
  font-weight: 600;
}

.dock-id {
  font-size: 9px;
}

.dock-meta {
  color: var(--muted);
  font-size: 10.5px;
}

.dock-tabs {
  display: flex;
  gap: 2px;
  padding: 0 10px;
  border-bottom: 1px solid var(--border-soft);
}

.dock-tab {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 11px;
  border: none;
  background: transparent;
  color: var(--muted);
  font-size: 11px;
}

.dock-tab:hover {
  color: var(--text);
}

.dock-tab.active {
  color: var(--text);
}

.dock-tab.active::after {
  content: '';
  position: absolute;
  left: 9px;
  right: 9px;
  bottom: -1px;
  height: 1px;
  background: var(--primary);
}

.tab-count {
  font-size: 9px;
  color: var(--faint);
  background: rgba(255, 255, 255, 0.04);
  padding: 0 5px;
  border-radius: 999px;
}

.dock-body {
  flex: 1;
  overflow: auto;
  padding: 9px 14px 14px;
}

.timeline-row {
  display: grid;
  grid-template-columns: 62px 16px minmax(80px, 130px) minmax(0, 1fr) 54px;
  align-items: center;
  gap: 8px;
  padding: 5px 2px;
  border-bottom: 1px solid rgba(214, 234, 245, 0.45);
  font-size: 10.5px;
}

.tl-time {
  color: var(--faint);
  font-size: 9.5px;
}

.tl-icon {
  display: grid;
  place-items: center;
  color: var(--muted);
}

.timeline-row.start .tl-icon {
  color: var(--primary);
}

.timeline-row.done .tl-icon {
  color: var(--success);
}

.timeline-row.error .tl-icon {
  color: var(--danger);
}

.tl-node {
  color: var(--text-soft);
  font-weight: 550;
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

.tl-duration {
  color: var(--faint);
  font-size: 9px;
  text-align: right;
}

.live-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 4px;
  color: var(--faint);
  font-size: 10px;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--primary);
  animation: pulse 1.4s infinite;
}

.console {
  font-family: var(--mono);
  font-size: 10px;
  line-height: 1.8;
}

.console-line {
  display: grid;
  grid-template-columns: 70px 54px minmax(0, 1fr);
  gap: 8px;
  padding: 1px 0;
  color: var(--text-soft);
  white-space: pre-wrap;
  word-break: break-word;
}

.console-time {
  color: var(--faint);
}

.console-level {
  color: var(--primary);
  text-transform: uppercase;
  font-size: 9px;
}

.console-line.error {
  color: #fca5a5;
}

.console-line.error .console-level {
  color: var(--danger);
}

.artifacts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(172px, 1fr));
  gap: 9px;
}

.artifact-card {
  display: block;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.02);
  transition: border-color 0.15s ease, transform 0.15s ease;
}

.artifact-card:hover {
  border-color: rgba(14, 165, 233, 0.35);
  transform: translateY(-1px);
}

.artifact-card img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  background: var(--panel-3);
}

.artifact-caption {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  padding: 6px 8px;
  font-size: 9.5px;
  color: var(--muted);
}

.artifact-caption .mono {
  color: var(--faint);
  font-size: 8.5px;
}

.vars-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 10.5px;
}

.vars-table th {
  text-align: left;
  color: var(--faint);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 4px 8px;
  border-bottom: 1px solid var(--border-soft);
}

.vars-table td {
  padding: 5px 8px;
  border-bottom: 1px solid rgba(214, 234, 245, 0.5);
  color: var(--text-soft);
}

.var-key {
  color: var(--primary);
  width: 160px;
}

.dock-empty {
  color: var(--faint);
  font-size: 11px;
  padding: 18px 4px;
}

.icon-btn {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--faint);
}

.icon-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text);
}
</style>
