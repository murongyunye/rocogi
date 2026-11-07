<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { api, formatDuration, formatTime } from '../lib/api'
import { refreshMeta } from '../lib/store'
import { notify } from '../lib/toast'
import type { Run, Workflow } from '../types'

const router = useRouter()
const runs = ref<Run[]>([])
const workflows = ref<Workflow[]>([])
const loading = ref(true)
const statusFilter = ref('all')
const workflowFilter = ref('all')
let timer = 0

const filtered = computed(() =>
  runs.value.filter((run) => {
    if (statusFilter.value !== 'all' && run.status !== statusFilter.value) return false
    if (workflowFilter.value !== 'all' && run.workflowId !== workflowFilter.value) return false
    return true
  }),
)

const stats = computed(() => {
  const total = runs.value.length
  const succeeded = runs.value.filter((run) => run.status === 'succeeded').length
  const failed = runs.value.filter((run) => run.status === 'failed').length
  const avg = total ? runs.value.reduce((sum, run) => sum + (run.durationMs || 0), 0) / total : 0
  return [
    { label: 'Total', value: total, hint: '全部运行' },
    { label: 'Success', value: succeeded, hint: total ? `${Math.round((succeeded / total) * 100)}%` : '—' },
    { label: 'Failed', value: failed, hint: '需要关注' },
    { label: 'Avg', value: formatDuration(Math.round(avg)), hint: '平均耗时' },
  ]
})

async function load() {
  try {
    const [runList, workflowList] = await Promise.all([api<Run[]>('/api/runs?limit=80'), api<Workflow[]>('/api/workflows')])
    runs.value = runList
    workflows.value = workflowList
  } catch (error) {
    notify(`加载运行记录失败：${error}`, 'error')
  } finally {
    loading.value = false
  }
}

function isRunning(): boolean {
  return runs.value.some((run) => run.status === 'running')
}

function schedule() {
  window.clearTimeout(timer)
  timer = window.setTimeout(async () => {
    if (isRunning()) await load()
    schedule()
  }, 2500)
}

async function stopRun(run: Run, event: Event) {
  event.stopPropagation()
  try {
    await api(`/api/runs/${run.id}/stop`, { method: 'POST', body: '{}' })
    notify('已发送停止请求', 'info')
    await load()
  } catch (error) {
    notify(`停止失败：${error}`, 'error')
  }
}

function statusLabel(status: string): string {
  return { running: '运行中', succeeded: '已完成', failed: '失败', stopped: '已停止' }[status] || status
}

onMounted(async () => {
  await load()
  refreshMeta()
  schedule()
})

onBeforeUnmount(() => window.clearTimeout(timer))
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <div class="eyebrow">Execution History</div>
        <h1>执行记录</h1>
        <p class="page-sub">每次运行都会留下节点时间线、日志、变量与截图证据。点击记录查看完整现场。</p>
      </div>
      <div class="page-actions">
        <button class="btn" @click="load"><AppIcon name="refresh" :size="14" /> 刷新</button>
      </div>
    </header>

    <div class="stat-grid" style="margin-bottom: 24px">
      <div v-for="stat in stats" :key="stat.label" class="stat-cell">
        <div class="stat-label">{{ stat.label }}</div>
        <div class="stat-value">{{ stat.value }}<small>{{ stat.hint }}</small></div>
      </div>
    </div>

    <div class="filter-row">
      <div class="filter-group">
        <span class="filter-label">状态</span>
        <button
          v-for="status in ['all', 'running', 'succeeded', 'failed', 'stopped']"
          :key="status"
          class="chip tag-pill"
          :class="{ primary: statusFilter === status }"
          @click="statusFilter = status"
        >
          {{ status === 'all' ? '全部' : statusLabel(status) }}
        </button>
      </div>
      <div class="filter-group">
        <span class="filter-label">工作流</span>
        <select v-model="workflowFilter" class="select filter-select">
          <option value="all">全部工作流</option>
          <option v-for="workflow in workflows" :key="workflow.id" :value="workflow.id">{{ workflow.name }}</option>
        </select>
      </div>
      <div class="result-count">{{ filtered.length }} 条记录</div>
    </div>

    <div v-if="loading" class="panel empty-state">正在读取运行记录...</div>

    <div v-else-if="filtered.length" class="panel table-panel">
      <table class="table">
        <thead>
          <tr>
            <th style="width: 48px">状态</th>
            <th>工作流</th>
            <th style="width: 150px">开始时间</th>
            <th style="width: 100px">耗时</th>
            <th style="width: 96px">触发</th>
            <th style="width: 120px">运行 ID</th>
            <th style="width: 74px"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="run in filtered" :key="run.id" class="run-row" @click="router.push(`/runs/${run.id}`)">
            <td>
              <span class="status-dot" :class="run.status" />
            </td>
            <td>
              <div class="run-name">{{ run.workflowName }}</div>
              <div class="run-sub">{{ statusLabel(run.status) }}<span v-if="run.error"> · {{ run.error }}</span></div>
            </td>
            <td class="mono time-cell">{{ formatTime(run.startedAt) }}</td>
            <td class="mono">{{ formatDuration(run.durationMs) }}</td>
            <td><span class="chip">{{ run.trigger }}</span></td>
            <td class="mono run-id">{{ run.id }}</td>
            <td class="row-actions">
              <button v-if="run.status === 'running'" class="btn btn-sm btn-danger" @click="stopRun(run, $event)">
                停止
              </button>
              <button v-else class="btn btn-sm" @click.stop="router.push(`/runs/${run.id}`)">详情</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="panel empty-state">
      <div class="empty-icon"><AppIcon name="runs" :size="22" /></div>
      <h3>还没有运行记录</h3>
      <p class="muted" style="font-size: 12px">打开工作流并点击运行，第一条记录会出现在这里。</p>
      <button class="btn btn-primary" style="margin-top: 6px" @click="router.push('/workflows')">去工作流</button>
    </div>
  </div>
</template>

<style scoped>
.filter-row {
  display: flex;
  align-items: center;
  gap: 22px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-label {
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--faint);
  margin-right: 2px;
}

.tag-pill {
  cursor: pointer;
}

.filter-select {
  width: 190px;
  height: 30px;
  padding: 4px 28px 4px 10px;
  font-size: 11.5px;
}

.result-count {
  margin-left: auto;
  font-family: var(--mono);
  font-size: 10.5px;
  color: var(--faint);
}

.table-panel {
  overflow: hidden;
}

.run-row {
  cursor: pointer;
}

.run-name {
  font-size: 12.5px;
  font-weight: 550;
}

.run-sub {
  font-size: 9.5px;
  color: var(--faint);
  margin-top: 2px;
  max-width: 320px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.time-cell {
  color: var(--muted);
  font-size: 10.5px;
}

.run-id {
  color: var(--faint);
  font-size: 9.5px;
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.row-actions {
  text-align: right;
}
</style>
