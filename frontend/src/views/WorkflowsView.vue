<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import WorkflowMiniMap from '../components/WorkflowMiniMap.vue'
import { api, formatDuration, formatTime } from '../lib/api'
import { appStore, refreshMeta } from '../lib/store'
import { notify } from '../lib/toast'
import type { NodeContract, Run, Workflow } from '../types'

const router = useRouter()
const workflows = ref<Workflow[]>([])
const contracts = ref<NodeContract[]>([])
const loading = ref(true)
const search = ref('')
const activeTag = ref('全部')
const creating = ref(false)
const newName = ref('')
const newDescription = ref('')
const busyId = ref('')

const allTags = computed(() => {
  const tags = new Set<string>()
  workflows.value.forEach((workflow) => workflow.tags?.forEach((tag) => tags.add(tag)))
  return ['全部', ...Array.from(tags).slice(0, 8)]
})

const filtered = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  return workflows.value.filter((workflow) => {
    const tagMatch = activeTag.value === '全部' || workflow.tags.includes(activeTag.value)
    const textMatch =
      !keyword ||
      workflow.name.toLowerCase().includes(keyword) ||
      workflow.description.toLowerCase().includes(keyword) ||
      workflow.tags.some((tag) => tag.toLowerCase().includes(keyword))
    return tagMatch && textMatch
  })
})

const stats = computed(() => [
  { label: 'Workflows', value: workflows.value.length, hint: '本地工作流' },
  { label: 'Runs', value: appStore.meta?.runCount ?? 0, hint: '历史运行' },
  { label: 'POI', value: appStore.meta?.map?.pointCount ?? 0, hint: '地图点位' },
  { label: 'Templates', value: appStore.meta?.resources ?? 0, hint: '视觉资源' },
])

async function load() {
  loading.value = true
  try {
    const [items, catalog] = await Promise.all([api<Workflow[]>('/api/workflows'), api<{ nodes: NodeContract[] }>('/api/nodes')])
    workflows.value = items
    contracts.value = catalog.nodes
  } catch (error) {
    notify(`加载工作流失败：${error}`, 'error')
  } finally {
    loading.value = false
  }
}

function tagClass(tag: string): string {
  if (['抓宠', '循环', '战斗'].includes(tag)) return 'amber'
  if (['地图', '路线', 'SIFT'].includes(tag)) return 'primary'
  if (['对战', 'MCTS'].includes(tag)) return 'pink'
  return ''
}

function nodeCount(workflow: Workflow): number {
  return workflow.graph?.nodes?.length || 0
}

function edgeCount(workflow: Workflow): number {
  return workflow.graph?.edges?.length || 0
}

function runStatusClass(run?: Run | null): string {
  return run?.status || 'idle'
}

function openWorkflow(workflow: Workflow) {
  router.push(`/workflows/${workflow.id}`)
}

async function createWorkflow() {
  const name = newName.value.trim()
  if (!name) {
    notify('请填写工作流名称', 'error')
    return
  }
  const graph = {
    nodes: [{ id: 'start', type: 'run.start', x: 120, y: 200, config: { label: '开始' } }],
    edges: [],
    subgraphs: {},
    variables: {},
  }
  try {
    const created = await api<Workflow>('/api/workflows', {
      method: 'POST',
      body: JSON.stringify({ name, description: newDescription.value.trim(), graph, tags: [] }),
    })
    creating.value = false
    newName.value = ''
    newDescription.value = ''
    notify('工作流已创建', 'success')
    await load()
    refreshMeta()
    router.push(`/workflows/${created.id}`)
  } catch (error) {
    notify(`创建失败：${error}`, 'error')
  }
}

async function runWorkflow(workflow: Workflow) {
  busyId.value = workflow.id
  try {
    const run = await api<Run>(`/api/workflows/${workflow.id}/run`, { method: 'POST', body: '{}' })
    notify(`已启动「${workflow.name}」`, 'success')
    await load()
    refreshMeta()
    router.push(`/runs/${run.id}`)
  } catch (error: any) {
    notify(`启动失败：${error?.payload?.message || error}`, 'error')
  } finally {
    busyId.value = ''
  }
}

async function duplicateWorkflow(workflow: Workflow, event: Event) {
  event.stopPropagation()
  event.preventDefault()
  try {
    await api(`/api/workflows/${workflow.id}/duplicate`, { method: 'POST', body: '{}' })
    notify('已创建副本', 'success')
    await load()
    refreshMeta()
  } catch (error) {
    notify(`复制失败：${error}`, 'error')
  }
}

async function removeWorkflow(workflow: Workflow, event: Event) {
  event.stopPropagation()
  event.preventDefault()
  if (!window.confirm(`确定删除「${workflow.name}」？该操作不可撤销。`)) return
  try {
    await api(`/api/workflows/${workflow.id}`, { method: 'DELETE' })
    notify('工作流已删除', 'success')
    await load()
    refreshMeta()
  } catch (error) {
    notify(`删除失败：${error}`, 'error')
  }
}

function importJson(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = async () => {
    try {
      const payload = JSON.parse(String(reader.result))
      const graph = payload.graph || payload
      if (!graph.nodes) throw new Error('缺少 graph.nodes')
      const created = await api<Workflow>('/api/workflows', {
        method: 'POST',
        body: JSON.stringify({
          name: payload.name || file.name.replace('.json', ''),
          description: payload.description || '导入的工作流',
          graph,
          tags: payload.tags || ['导入'],
        }),
      })
      notify('工作流已导入', 'success')
      await load()
      refreshMeta()
      router.push(`/workflows/${created.id}`)
    } catch (error) {
      notify(`导入失败：${error}`, 'error')
    } finally {
      input.value = ''
    }
  }
  reader.readAsText(file, 'utf-8')
}

onMounted(async () => {
  await load()
  refreshMeta()
})
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <div class="eyebrow">Independent Tasks</div>
        <h1>独立任务</h1>
        <p class="page-sub">
          把截图、识别、输入、地图定位与对战决策连成可调试的独立工作流。也可以从一条龙页面生成任务计划，再进入编辑器细化。
        </p>
      </div>
      <div class="page-actions">
        <label class="btn">
          <AppIcon name="upload" :size="15" />
          导入
          <input type="file" accept="application/json" hidden @change="importJson" />
        </label>
        <button class="btn btn-primary" @click="creating = true">
          <AppIcon name="plus" :size="15" />
          新建工作流
        </button>
      </div>
    </header>

    <div class="stat-grid" style="margin-bottom: 26px">
      <div v-for="stat in stats" :key="stat.label" class="stat-cell">
        <div class="stat-label">{{ stat.label }}</div>
        <div class="stat-value">{{ stat.value }}<small>{{ stat.hint }}</small></div>
      </div>
    </div>

    <div class="filter-bar">
      <div class="search-wrap">
        <AppIcon name="search" :size="15" />
        <input v-model="search" class="search-input" placeholder="搜索工作流、标签或描述..." />
      </div>
      <div class="tag-row">
        <button
          v-for="tag in allTags"
          :key="tag"
          class="chip tag-pill"
          :class="{ primary: activeTag === tag }"
          @click="activeTag = tag"
        >
          {{ tag }}
        </button>
      </div>
      <div class="result-count">{{ filtered.length }} 个工作流</div>
    </div>

    <div v-if="loading" class="wf-grid fade-list">
      <div v-for="index in 3" :key="index" class="wf-card skeleton" />
    </div>

    <div v-else-if="filtered.length" class="wf-grid fade-list">
      <article
        v-for="(workflow, index) in filtered"
        :key="workflow.id"
        class="wf-card"
        @click="openWorkflow(workflow)"
      >
        <div class="wf-card-top">
          <div class="wf-title-row">
            <span class="wf-index mono">{{ String(index + 1).padStart(2, '0') }}</span>
            <div class="wf-tags">
              <span v-for="tag in workflow.tags.slice(0, 2)" :key="tag" class="chip" :class="tagClass(tag)">{{
                tag }}</span>
            </div>
          </div>
          <div class="wf-utils">
            <button class="icon-btn" title="复制" @click="duplicateWorkflow(workflow, $event)">
              <AppIcon name="copy" :size="14" />
            </button>
            <button class="icon-btn danger" title="删除" @click="removeWorkflow(workflow, $event)">
              <AppIcon name="trash" :size="14" />
            </button>
          </div>
        </div>

        <h3 class="wf-name">{{ workflow.name }}</h3>
        <p class="wf-desc">{{ workflow.description }}</p>

        <div class="wf-preview">
          <WorkflowMiniMap :graph="workflow.graph" :contracts="contracts" :height="78" />
          <div class="wf-preview-meta">
            <span>{{ nodeCount(workflow) }} 节点</span>
            <span>{{ edgeCount(workflow) }} 连线</span>
          </div>
        </div>

        <div class="wf-foot">
          <div class="wf-last">
            <span class="status-dot" :class="runStatusClass(workflow.lastRun)" />
            <span v-if="workflow.lastRun">
              最近 {{ workflow.lastRun.status === 'succeeded' ? '成功' : workflow.lastRun.status === 'running' ? '运行中' : workflow.lastRun.status === 'failed' ? '失败' : '已停止' }}
              · {{ formatDuration(workflow.lastRun.durationMs) }}
            </span>
            <span v-else class="faint">尚未运行</span>
          </div>
          <div class="wf-actions">
            <button
              class="btn btn-sm"
              :disabled="busyId === workflow.id"
              @click.stop="runWorkflow(workflow)"
            >
              <AppIcon :name="busyId === workflow.id ? 'refresh' : 'play'" :size="13" />
              {{ busyId === workflow.id ? '启动中' : '运行' }}
            </button>
            <button class="btn btn-sm btn-primary" @click.stop="openWorkflow(workflow)">
              <AppIcon name="panel" :size="13" />
              编辑
            </button>
          </div>
        </div>
      </article>
    </div>

    <div v-else class="panel empty-state">
      <div class="empty-icon"><AppIcon name="workflow" :size="22" /></div>
      <h3>没有匹配的工作流</h3>
      <p class="muted" style="font-size: 12px">调整筛选条件，或从空白工作流开始搭建。</p>
      <button class="btn btn-primary" style="margin-top: 8px" @click="creating = true">
        <AppIcon name="plus" :size="14" />
        新建工作流
      </button>
    </div>

    <div class="wf-tip">
      <AppIcon name="spark" :size="14" />
      <span>提示：内置示例使用模拟游戏窗口，可以在设置中切换为 Windows 窗口目标，绑定后再运行。</span>
      <span class="mono faint">{{ formatTime(new Date().toISOString()) }}</span>
    </div>

    <div v-if="creating" class="dialog-backdrop" @click.self="creating = false">
      <div class="dialog panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="workflow" :size="16" /> 新建工作流</div>
          <button class="icon-btn" @click="creating = false"><AppIcon name="close" :size="15" /></button>
        </div>
        <div class="panel-body">
          <div class="field">
            <div class="field-label">名称</div>
            <input v-model="newName" class="input" placeholder="例如：每日宝箱巡线" autofocus @keyup.enter="createWorkflow" />
          </div>
          <div class="field">
            <div class="field-label">描述</div>
            <textarea v-model="newDescription" class="textarea" rows="3" placeholder="这条工作流负责什么？" />
          </div>
          <div class="dialog-foot">
            <button class="btn" @click="creating = false">取消</button>
            <button class="btn btn-primary" @click="createWorkflow">创建并打开</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

.search-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  width: min(360px, 100%);
  height: 34px;
  padding: 0 11px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.55);
  color: var(--faint);
}

.search-input {
  width: 100%;
  border: none;
  background: transparent;
  outline: none;
  font-size: 12.5px;
  color: var(--text);
}

.search-input::placeholder {
  color: var(--faint);
}

.tag-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tag-pill {
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}

.tag-pill:hover {
  color: var(--text);
  border-color: var(--border);
}

.result-count {
  margin-left: auto;
  font-family: var(--mono);
  font-size: 10.5px;
  color: var(--faint);
}

.wf-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: 16px;
}

.wf-card {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 280px;
  padding: 18px 18px 16px;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.92));
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
}

.wf-card:hover {
  transform: translateY(-2px);
  border-color: #2c4056;
  box-shadow: 0 18px 44px rgba(0, 0, 0, 0.28);
}

.wf-card::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 2px;
  background: linear-gradient(180deg, var(--primary), transparent 55%);
  opacity: 0.45;
}

.wf-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 24px;
}

.wf-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.wf-index {
  font-size: 10px;
  color: var(--faint);
  letter-spacing: 0.08em;
}

.wf-tags {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.wf-utils {
  display: flex;
  gap: 3px;
  opacity: 0;
  transition: opacity 0.16s ease;
}

.wf-card:hover .wf-utils {
  opacity: 1;
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
  border-color: var(--border-soft);
}

.icon-btn.danger:hover {
  color: var(--danger);
  border-color: rgba(248, 113, 113, 0.25);
}

.wf-name {
  margin-top: 13px;
  font-size: 17px;
  font-weight: 620;
  letter-spacing: -0.02em;
  line-height: 1.3;
}

.wf-desc {
  margin-top: 7px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 38px;
}

.wf-preview {
  margin: 14px -4px 0;
  padding: 4px 8px 0;
  border-radius: 9px;
  background: radial-gradient(circle at 50% 40%, rgba(14, 165, 233, 0.05), transparent 70%);
  border: 1px solid rgba(190, 220, 237, 0.5);
}

.wf-preview-meta {
  display: flex;
  justify-content: space-between;
  padding: 2px 6px 7px;
  font-family: var(--mono);
  font-size: 9.5px;
  color: var(--faint);
}

.wf-foot {
  margin-top: auto;
  padding-top: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.wf-last {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 10.5px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wf-actions {
  display: flex;
  gap: 6px;
  flex: none;
}

.skeleton {
  min-height: 280px;
  background: linear-gradient(100deg, #ffffff 30%, #dcefff 50%, #ffffff 70%);
  background-size: 300% 100%;
  animation: shimmer 1.4s infinite linear;
  cursor: default;
}

.skeleton:hover {
  transform: none;
  border-color: var(--border-soft);
  box-shadow: none;
}

@keyframes shimmer {
  from {
    background-position: 100% 0;
  }
  to {
    background-position: -100% 0;
  }
}

.wf-tip {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 24px;
  padding: 11px 14px;
  border-radius: 9px;
  border: 1px solid rgba(14, 165, 233, 0.12);
  background: rgba(14, 165, 233, 0.035);
  color: var(--muted);
  font-size: 11.5px;
}

.wf-tip svg {
  color: var(--primary);
}

.wf-tip .mono {
  margin-left: auto;
  font-size: 10px;
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  place-items: center;
  background: rgba(3, 6, 10, 0.62);
  backdrop-filter: blur(6px);
  animation: fade 0.18s ease both;
}

.dialog {
  width: min(460px, calc(100vw - 40px));
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.6);
  animation: rise 0.22s ease both;
}

.dialog-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

@keyframes fade {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
</style>
