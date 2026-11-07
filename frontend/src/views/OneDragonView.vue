<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { api, formatDuration, formatTime } from '../lib/api'
import { refreshMeta } from '../lib/store'
import { notify } from '../lib/toast'
import type { OneDragonPlan, OneDragonTask, Run, RunEvent } from '../types'

const router = useRouter()
const tasks = ref<OneDragonTask[]>([])
const plan = ref<OneDragonPlan>({ loops: 3, tasks: [] })
const selectedIndex = ref(0)
const run = ref<Run | null>(null)
const events = ref<RunEvent[]>([])
const loading = ref(true)
const busy = ref(false)
let pollTimer = 0

const selected = computed(() => plan.value.tasks[selectedIndex.value] || null)
const selectedTask = computed(() => tasks.value.find((task) => task.id === selected.value?.id) || null)
const enabledCount = computed(() => plan.value.tasks.filter((task) => task.enabled).length)
const workflowId = ref('wf_onedragon')

const progress = computed(() => {
  if (!run.value) return 0
  if (run.value.status === 'succeeded') return 100
  if (run.value.status === 'failed' || run.value.status === 'stopped') return 100
  const finished = events.value.filter((event) => event.type === 'node.finished').length
  const targetNodes = plan.value.tasks.filter((task) => task.enabled).length * plan.value.loops + 6
  return Math.min(96, Math.round((finished / Math.max(targetNodes, 1)) * 100))
})

const runLogs = computed(() =>
  events.value.filter((event) => ['log', 'node.finished', 'node.failed', 'run.finished'].includes(event.type)).slice(-12),
)

function statusLabel(status?: string): string {
  return { running: '执行中', succeeded: '已完成', failed: '失败', stopped: '已停止' }[status || ''] || '未执行'
}

const taskSummaries: Record<string, (config: Record<string, any>) => string> = {
  auto_ball: (config) => `按键 ${String(config.key || 'x').toUpperCase()} · 阈值 ${config.threshold ?? 0.45}`,
  smart_battle: (config) =>
    `普通 ${config.normalStrategy || 'gather'} / 污染 ${config.pollutedStrategy || 'escape'}`,
  party_confirm: (config) => `按键 ${String(config.key || 'f').toUpperCase()} · 阈值 ${config.threshold ?? 0.45}`,
  map_route: (config) => `${config.labels || '宝箱'} · ${config.limit || 8} 个点`,
  battle_ai: (config) => `MCTS ${config.simulations || 30} 次模拟`,
}

function summaryOf(item: { id: string; config: Record<string, any> }): string {
  return taskSummaries[item.id]?.(item.config) || ''
}

async function load() {
  try {
    const data = await api<{ plan: OneDragonPlan; tasks: OneDragonTask[]; workflowId: string }>('/api/onedragon/plan')
    plan.value = JSON.parse(JSON.stringify(data.plan))
    tasks.value = data.tasks
    workflowId.value = data.workflowId
    if (!plan.value.tasks.length) plan.value.tasks = []
    await loadLatestRun()
  } catch (error) {
    notify(`加载一条龙计划失败：${error}`, 'error')
  } finally {
    loading.value = false
  }
}

async function loadLatestRun() {
  try {
    const runs = await api<Run[]>(`/api/runs?workflowId=${workflowId.value}&limit=1`)
    if (runs.length) {
      run.value = runs[0]
      events.value = await api<RunEvent[]>(`/api/runs/${runs[0].id}/events`)
      if (runs[0].status === 'running') startPolling(runs[0].id)
    }
  } catch {
    /* ignore */
  }
}

function move(index: number, direction: number) {
  const target = index + direction
  if (target < 0 || target >= plan.value.tasks.length) return
  const list = plan.value.tasks
  ;[list[index], list[target]] = [list[target], list[index]]
  selectedIndex.value = target
}

async function savePlan(silent = false): Promise<boolean> {
  try {
    const data = await api<{ plan: OneDragonPlan }>('/api/onedragon/plan', {
      method: 'PUT',
      body: JSON.stringify({ plan: plan.value }),
    })
    plan.value = JSON.parse(JSON.stringify(data.plan))
    if (!silent) notify('任务计划已保存', 'success')
    refreshMeta()
    return true
  } catch (error) {
    notify(`保存计划失败：${error}`, 'error')
    return false
  }
}

async function start() {
  busy.value = true
  try {
    await savePlan(true)
    const result = await api<{ runId: string }>('/api/onedragon/run', {
      method: 'POST',
      body: JSON.stringify({ plan: plan.value }),
    })
    notify('一条龙已启动', 'success')
    const detail = await api<Run>(`/api/runs/${result.runId}`)
    run.value = detail
    events.value = []
    startPolling(result.runId)
    refreshMeta()
  } catch (error: any) {
    notify(`启动失败：${error?.payload?.message || error}`, 'error')
  } finally {
    busy.value = false
  }
}

function startPolling(runId: string) {
  window.clearInterval(pollTimer)
  pollTimer = window.setInterval(async () => {
    if (!run.value || run.value.status !== 'running') {
      window.clearInterval(pollTimer)
      return
    }
    try {
      run.value = await api<Run>(`/api/runs/${runId}`)
      events.value = await api<RunEvent[]>(`/api/runs/${runId}/events`)
      if (run.value.status !== 'running') {
        window.clearInterval(pollTimer)
        refreshMeta()
      }
    } catch {
      /* ignore */
    }
  }, 1200)
}

async function stop() {
  if (!run.value) return
  try {
    await api(`/api/runs/${run.value.id}/stop`, { method: 'POST', body: '{}' })
    notify('已发送停止请求', 'info')
  } catch (error) {
    notify(`停止失败：${error}`, 'error')
  }
}

onMounted(load)
onBeforeUnmount(() => window.clearInterval(pollTimer))
</script>

<template>
  <div class="page onedragon-page">
    <header class="page-head">
      <div>
        <div class="eyebrow">One Dragon</div>
        <div class="title-row">
          <h1>一条龙</h1>
          <span class="chip">{{ enabledCount }} / {{ plan.tasks.length }} 任务</span>
          <span class="status-dot" :class="run?.status || 'idle'" />
          <span class="chip" :class="run?.status === 'running' ? 'primary' : run?.status === 'failed' ? 'danger' : ''">
            {{ run ? '最近一次 ' + statusLabel(run.status) : '未执行' }}
          </span>
        </div>
        <p class="page-sub">
          按 BetterGI 的任务计划结构组织：左侧排序与开关，右侧配置与执行。计划会同步生成一个可编辑的独立工作流。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn" @click="savePlan()"><AppIcon name="save" :size="14" /> 保存计划</button>
        <button class="btn" @click="router.push(`/workflows/${workflowId}`)">
          <AppIcon name="workflow" :size="14" /> 查看工作流
        </button>
        <button v-if="run?.status !== 'running'" class="btn btn-primary" :disabled="busy" @click="start">
          <AppIcon name="play" :size="14" /> 开始一条龙
        </button>
        <button v-else class="btn btn-danger" @click="stop"><AppIcon name="stop" :size="14" /> 停止</button>
      </div>
    </header>

    <div class="onedragon-layout">
      <section class="panel task-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="activity" :size="15" /> 任务列表</div>
          <span class="chip mono">{{ plan.tasks.length }}</span>
        </div>
        <div class="panel-body task-list">
          <div
            v-for="(item, index) in plan.tasks"
            :key="item.id"
            class="task-row"
            :class="{ selected: index === selectedIndex, disabled: !item.enabled }"
            @click="selectedIndex = index"
          >
            <div class="task-order mono">{{ String(index + 1).padStart(2, '0') }}</div>
            <div class="task-switch" :class="{ on: item.enabled }" @click.stop="item.enabled = !item.enabled" />
            <div class="task-main">
              <div class="task-name">{{ tasks.find((task) => task.id === item.id)?.name || item.id }}</div>
              <div class="task-summary">{{ summaryOf(item) }}</div>
            </div>
            <div class="task-move" @click.stop>
              <button class="mini-btn" title="上移任务" aria-label="上移任务" :disabled="index === 0" @click="move(index, -1)"><AppIcon name="chevron" :size="11" class="up" /></button>
              <button class="mini-btn" title="下移任务" aria-label="下移任务" :disabled="index === plan.tasks.length - 1" @click="move(index, 1)"><AppIcon name="chevron" :size="11" /></button>
            </div>
          </div>
          <div v-if="loading" class="muted" style="font-size: 11px; padding: 12px">正在加载任务计划...</div>

          <div class="loop-row">
            <div>
              <div class="field-label">循环轮数</div>
              <div class="field-help">完成全部任务后回到开头继续</div>
            </div>
            <input v-model.number="plan.loops" type="number" min="1" max="20" class="input loop-input" />
          </div>

          <button class="btn btn-primary start-button" :disabled="busy || run?.status === 'running'" @click="start">
            <AppIcon name="play" :size="14" /> {{ run?.status === 'running' ? '执行中...' : '开始一条龙' }}
          </button>
          <div class="start-note">任务顺序与开关会写入生成的 workflow；也可以切换到编辑器继续细化。</div>
        </div>
      </section>

      <section class="right-col">
        <section class="panel config-panel">
          <div class="panel-head">
            <div class="panel-title"><AppIcon name="settings" :size="15" /> 任务配置</div>
            <span class="chip mono">{{ selectedTask?.id || '—' }}</span>
          </div>
          <div v-if="selected && selectedTask" class="panel-body">
            <div class="selected-head">
              <div class="selected-icon"><AppIcon name="node" :size="17" /></div>
              <div>
                <div class="selected-name">{{ selectedTask.name }}</div>
                <div class="selected-desc">{{ selectedTask.description }}</div>
              </div>
              <span class="chip" :class="selected.enabled ? 'primary' : ''">{{ selected.enabled ? '已启用' : '已跳过' }}</span>
            </div>

            <div v-if="selected.id === 'auto_ball'" class="config-grid">
              <div class="field">
                <div class="field-label">触发按键</div>
                <input v-model="selected.config.key" class="input" maxlength="8" />
              </div>
              <div class="field">
                <div class="field-label">识别阈值</div>
                <input v-model.number="selected.config.threshold" type="number" min="0.2" max="1" step="0.01" class="input" />
              </div>
            </div>

            <div v-else-if="selected.id === 'smart_battle'" class="config-grid">
              <div class="field">
                <div class="field-label">普通战斗</div>
                <select v-model="selected.config.normalStrategy" class="select">
                  <option value="gather">只聚能（X）</option>
                  <option value="skill1_gather">技能1 后聚能</option>
                  <option value="escape">逃跑</option>
                  <option value="none">不操作</option>
                </select>
              </div>
              <div class="field">
                <div class="field-label">污染战斗</div>
                <select v-model="selected.config.pollutedStrategy" class="select">
                  <option value="escape">逃跑</option>
                  <option value="gather">只聚能（X）</option>
                  <option value="skill1_gather">技能1 后聚能</option>
                  <option value="none">不操作</option>
                </select>
              </div>
            </div>

            <div v-else-if="selected.id === 'party_confirm'" class="config-grid">
              <div class="field">
                <div class="field-label">确认按键</div>
                <input v-model="selected.config.key" class="input" maxlength="8" />
              </div>
              <div class="field">
                <div class="field-label">识别阈值</div>
                <input v-model.number="selected.config.threshold" type="number" min="0.2" max="1" step="0.01" class="input" />
              </div>
            </div>

            <div v-else-if="selected.id === 'map_route'" class="config-grid">
              <div class="field">
                <div class="field-label">资源名称</div>
                <input v-model="selected.config.labels" class="input" placeholder="宝箱" />
              </div>
              <div class="field">
                <div class="field-label">最多点位</div>
                <input v-model.number="selected.config.limit" type="number" min="1" max="50" class="input" />
              </div>
            </div>

            <div v-else-if="selected.id === 'battle_ai'" class="config-grid">
              <div class="field">
                <div class="field-label">MCTS 模拟次数</div>
                <input v-model.number="selected.config.simulations" type="number" min="10" max="200" step="10" class="input" />
              </div>
            </div>

            <div class="config-hint">
              任务会按左侧顺序进入生成的 workflow。关闭的任务不会出现在执行图中。
            </div>
          </div>
          <div v-else class="empty-state">选择一个任务查看配置</div>
        </section>

        <section class="panel run-panel">
          <div class="panel-head">
            <div class="panel-title"><AppIcon name="runs" :size="15" /> 执行进度</div>
            <span class="chip mono">{{ run ? formatDuration(run.durationMs) : '—' }}</span>
          </div>
          <div class="panel-body">
            <div class="progress-head">
              <span>{{ run?.status === 'running' ? '正在执行' : run ? '最近执行' : '等待启动' }}</span>
              <span class="mono">{{ progress }}%</span>
            </div>
            <div class="progress-track"><span class="progress-fill" :style="{ width: `${progress}%` }" /></div>
            <div v-if="run" class="run-meta mono">{{ run.id }} · {{ formatTime(run.startedAt) }}</div>
            <div class="run-log">
              <div v-for="(event, index) in runLogs" :key="index" class="run-log-row">
                <span class="mono log-time">{{ new Date(event.ts).toLocaleTimeString('zh-CN', { hour12: false }) }}</span>
                <span class="log-msg">{{ event.message }}</span>
              </div>
              <div v-if="!runLogs.length" class="muted" style="font-size: 11px; padding: 10px 0">
                启动一条龙后，这里会显示节点执行与日志。
              </div>
            </div>
            <button v-if="run" class="btn" style="margin-top: 12px" @click="router.push(`/runs/${run.id}`)">
              <AppIcon name="external" :size="13" /> 查看完整运行记录
            </button>
          </div>
        </section>
      </section>
    </div>
  </div>
</template>

<style scoped>
.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.onedragon-layout {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 16px;
}

.right-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.task-panel .panel-body {
  padding: 10px 12px 14px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.task-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 8px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.018);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.task-row:hover {
  border-color: #31455a;
}

.task-row.selected {
  border-color: rgba(14, 165, 233, 0.34);
  background: rgba(14, 165, 233, 0.05);
}

.task-row.disabled {
  opacity: 0.58;
}

.task-order {
  font-size: 9px;
  color: var(--faint);
  width: 18px;
}

.task-switch {
  position: relative;
  width: 28px;
  height: 16px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: #0a1018;
  flex: none;
}

.task-switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--faint);
  transition: transform 0.16s ease, background 0.16s ease;
}

.task-switch.on {
  background: rgba(14, 165, 233, 0.14);
  border-color: rgba(14, 165, 233, 0.4);
}

.task-switch.on::after {
  transform: translateX(12px);
  background: var(--primary);
}

.task-main {
  min-width: 0;
  flex: 1;
}

.task-name {
  font-size: 11.5px;
  font-weight: 550;
}

.task-summary {
  margin-top: 1px;
  font-size: 9px;
  color: var(--faint);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-move {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.mini-btn {
  width: 17px;
  height: 14px;
  display: grid;
  place-items: center;
  border: 1px solid transparent;
  background: transparent;
  color: var(--faint);
  border-radius: 3px;
}

.mini-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text);
}

.mini-btn:disabled {
  opacity: 0.25;
}

.mini-btn .up {
  transform: rotate(180deg);
}

.loop-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--border-soft);
}

.loop-input {
  width: 64px;
  text-align: center;
}

.start-button {
  width: 100%;
  margin-top: 12px;
}

.start-note {
  margin-top: 8px;
  font-size: 9px;
  line-height: 1.55;
  color: var(--faint);
  text-align: center;
}

.selected-head {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-soft);
}

.selected-icon {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  flex: none;
  color: var(--primary);
  background: rgba(14, 165, 233, 0.12);
  border: 1px solid rgba(14, 165, 233, 0.16);
}

.selected-name {
  font-size: 14px;
  font-weight: 620;
}

.selected-desc {
  margin-top: 3px;
  font-size: 10.5px;
  line-height: 1.6;
  color: var(--muted);
  max-width: 580px;
}

.selected-head .chip {
  margin-left: auto;
  flex: none;
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 14px;
}

.config-grid .field + .field {
  margin-top: 0;
}

.config-hint {
  margin-top: 16px;
  padding: 9px 11px;
  border-radius: 8px;
  border: 1px solid rgba(14, 165, 233, 0.1);
  background: rgba(14, 165, 233, 0.035);
  font-size: 10px;
  line-height: 1.55;
  color: var(--muted);
}

.progress-head {
  display: flex;
  justify-content: space-between;
  font-size: 10.5px;
  color: var(--muted);
}

.progress-track {
  margin-top: 7px;
  height: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.progress-fill {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, rgba(14, 165, 233, 0.4), var(--primary));
  border-radius: 999px;
  transition: width 0.4s ease;
}

.run-meta {
  margin-top: 7px;
  font-size: 9px;
  color: var(--faint);
}

.run-log {
  margin-top: 10px;
  max-height: 190px;
  overflow: auto;
  border-top: 1px solid var(--border-soft);
}

.run-log-row {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr);
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px solid rgba(214, 234, 245, 0.45);
  font-size: 10px;
  color: var(--text-soft);
}

.log-time {
  color: var(--faint);
  font-size: 9px;
}

.log-msg {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1080px) {
  .onedragon-layout {
    grid-template-columns: 1fr;
  }
}
</style>
