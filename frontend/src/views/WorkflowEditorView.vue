<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import InspectorPanel from '../components/InspectorPanel.vue'
import NodePalette from '../components/NodePalette.vue'
import RunDock from '../components/RunDock.vue'
import WorkflowCanvas from '../components/WorkflowCanvas.vue'
import { api, wsUrl } from '../lib/api'
import { appStore, refreshMeta } from '../lib/store'
import { notify } from '../lib/toast'
import type { GraphNode, NodeContract, Resource, Run, RunEvent, Workflow, WorkflowGraph } from '../types'

const route = useRoute()
const router = useRouter()
const workflow = ref<Workflow | null>(null)
const contracts = ref<NodeContract[]>([])
const resources = ref<Resource[]>([])
const graph = ref<WorkflowGraph>({ nodes: [], edges: [], subgraphs: {}, variables: {} })
const selectedId = ref<string | null>(null)
const issues = ref<{ level: string; message: string; node_id?: string }[]>([])
const dirty = ref(false)
const saving = ref(false)
const loading = ref(true)
const run = ref<Run | null>(null)
const events = ref<RunEvent[]>([])
const dockOpen = ref(false)
const canvasRef = ref<InstanceType<typeof WorkflowCanvas> | null>(null)
const nameInput = ref('')
let socket: WebSocket | null = null
let validateTimer = 0
let pollTimer = 0

const contractMap = computed(() => new Map(contracts.value.map((contract) => [contract.type, contract])))
const selectedNode = computed(() => graph.value.nodes.find((node) => node.id === selectedId.value) || null)
const selectedContract = computed(() =>
  selectedNode.value ? contractMap.value.get(selectedNode.value.type) || null : null,
)
const errorCount = computed(() => issues.value.filter((issue) => issue.level === 'error').length)
const warningCount = computed(() => issues.value.filter((issue) => issue.level === 'warning').length)

const runStates = computed<Record<string, string>>(() => {
  const states: Record<string, string> = {}
  for (const event of events.value) {
    if (!event.nodeId) continue
    if (event.type === 'node.started') states[event.nodeId] = 'running'
    else if (event.type === 'node.finished') states[event.nodeId] = 'succeeded'
    else if (event.type === 'node.failed') states[event.nodeId] = 'failed'
    else if (event.type === 'node.skipped') states[event.nodeId] = 'skipped'
  }
  if (run.value?.status === 'running') {
    const started = [...events.value].reverse().find((event) => event.type === 'node.started')
    if (started?.nodeId && !events.value.some((event) => event.type === 'node.finished' && event.seq > started.seq)) {
      states[started.nodeId] = 'running'
    }
  }
  return states
})

const nodeNames = computed<Record<string, string>>(() => {
  const names: Record<string, string> = {}
  for (const node of graph.value.nodes) {
    const contract = contractMap.value.get(node.type)
    names[node.id] = node.title || contract?.title || node.type
  }
  return names
})

const lastOutputs = computed<Record<string, unknown> | null>(() => {
  if (!selectedId.value) return null
  for (const event of [...events.value].reverse()) {
    if (event.type === 'node.finished' && event.nodeId === selectedId.value) {
      return (event.data as any)?.outputs || null
    }
  }
  const summary = run.value?.summary?.nodeOutputs as Record<string, Record<string, unknown>> | undefined
  return summary?.[selectedId.value] || null
})

const targetInfo = computed(() => (appStore.meta?.target as Record<string, unknown>) || null)

async function load() {
  loading.value = true
  const id = String(route.params.id)
  try {
    const [detail, catalog, resourceList] = await Promise.all([
      api<Workflow>(`/api/workflows/${id}`),
      api<{ nodes: NodeContract[] }>('/api/nodes'),
      api<Resource[]>('/api/resources'),
    ])
    workflow.value = detail
    nameInput.value = detail.name
    graph.value = JSON.parse(JSON.stringify(detail.graph))
    contracts.value = catalog.nodes
    resources.value = resourceList
    issues.value = detail.issues || []
    dirty.value = false
    loading.value = false
    await nextTick()
    canvasRef.value?.focusStart()
  } catch (error) {
    notify(`加载工作流失败：${error}`, 'error')
  } finally {
    loading.value = false
  }
}

function markDirty() {
  dirty.value = true
  scheduleValidate()
}

function scheduleValidate() {
  window.clearTimeout(validateTimer)
  validateTimer = window.setTimeout(async () => {
    try {
      const result = await api<{ ok: boolean; issues: typeof issues.value }>('/api/validate', {
        method: 'POST',
        body: JSON.stringify({ graph: graph.value }),
      })
      issues.value = result.issues
    } catch {
      /* validation is advisory */
    }
  }, 450)
}

function newId(prefix: string): string {
  let index = 1
  let candidate = `${prefix}_${index}`
  const existing = new Set(graph.value.nodes.map((node) => node.id))
  while (existing.has(candidate)) {
    index += 1
    candidate = `${prefix}_${index}`
  }
  return candidate
}

function addNode(type: string) {
  const contract = contractMap.value.get(type)
  if (!contract) return
  const center = canvasRef.value?.viewportCenter() || { x: 300, y: 200 }
  const node: GraphNode = {
    id: newId(type.split('.').pop() || 'node'),
    type,
    x: Math.round(center.x + Math.random() * 24),
    y: Math.round(center.y + Math.random() * 18),
    config: {},
  }
  graph.value.nodes.push(node)
  selectedId.value = node.id
  markDirty()
}

function connect(from: string, fromPort: string, to: string) {
  if (from === to) {
    notify('不能连接到自身', 'error')
    return
  }
  const duplicate = graph.value.edges.some(
    (edge) => edge.from === from && edge.fromPort === fromPort && edge.to === to,
  )
  if (duplicate) return
  graph.value.edges.push({
    id: `e_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 5)}`,
    from,
    fromPort,
    to,
    toPort: 'in',
  })
  markDirty()
}

function deleteEdge(edgeId: string) {
  graph.value.edges = graph.value.edges.filter((edge) => edge.id !== edgeId)
  markDirty()
}

function onNodeMoved() {
  markDirty()
}

function onDescriptionUpdate(value: string) {
  if (!workflow.value) return
  workflow.value.description = value
  markDirty()
}

function updateConfig(key: string, value: unknown) {
  if (!selectedNode.value) return
  selectedNode.value.config = { ...selectedNode.value.config, [key]: value }
  markDirty()
}

function deleteNode() {
  if (!selectedNode.value) return
  const contract = contractMap.value.get(selectedNode.value.type)
  if (!window.confirm(`删除节点「${selectedNode.value.title || contract?.title || selectedNode.value.type}」？`)) return
  graph.value.edges = graph.value.edges.filter(
    (edge) => edge.from !== selectedNode.value!.id && edge.to !== selectedNode.value!.id,
  )
  graph.value.nodes = graph.value.nodes.filter((node) => node.id !== selectedNode.value!.id)
  selectedId.value = null
  markDirty()
}

function duplicateNode() {
  if (!selectedNode.value) return
  const source = selectedNode.value
  const copy: GraphNode = {
    ...JSON.parse(JSON.stringify(source)),
    id: newId(source.type.split('.').pop() || 'node'),
    x: source.x + 40,
    y: source.y + 40,
  }
  graph.value.nodes.push(copy)
  selectedId.value = copy.id
  markDirty()
}

async function save(silent = false): Promise<boolean> {
  if (!workflow.value) return false
  saving.value = true
  try {
    const name = nameInput.value.trim() || workflow.value.name
    const updated = await api<Workflow>(`/api/workflows/${workflow.value.id}`, {
      method: 'PUT',
      body: JSON.stringify({
        name,
        description: workflow.value.description,
        graph: graph.value,
        tags: workflow.value.tags,
        targetSlot: workflow.value.targetSlot,
      }),
    })
    workflow.value = updated
    dirty.value = false
    await api('/api/validate', { method: 'POST', body: JSON.stringify({ graph: graph.value }) }).then((result: any) => {
      issues.value = result.issues
    })
    if (!silent) notify('工作流已保存', 'success')
    refreshMeta()
    return true
  } catch (error: any) {
    const detail = error?.payload?.detail
    if (detail?.issues) issues.value = detail.issues
    notify(`保存失败：${detail?.message || error}`, 'error')
    return false
  } finally {
    saving.value = false
  }
}

async function startRun() {
  if (!workflow.value) return
  if (dirty.value) {
    const ok = await save(true)
    if (!ok) return
  }
  try {
    const created = await api<Run>(`/api/workflows/${workflow.value.id}/run`, {
      method: 'POST',
      body: JSON.stringify({ trigger: 'editor' }),
    })
    run.value = created
    events.value = []
    dockOpen.value = true
    refreshMeta()
    subscribe(created.id)
    startPolling(created.id)
  } catch (error: any) {
    const detail = error?.payload?.detail
    if (detail?.issues) issues.value = detail.issues
    notify(`启动失败：${detail?.message || error}`, 'error')
  }
}

function subscribe(runId: string) {
  if (socket) {
    socket.onclose = null
    socket.close()
  }
  socket = new WebSocket(wsUrl(`/api/ws/runs/${runId}`))
  socket.onmessage = (message) => {
    try {
      const event = JSON.parse(message.data) as RunEvent
      if (events.value.some((item) => item.seq === event.seq)) return
      events.value.push(event)
      if (event.type === 'run.finished') {
        const status = (event.data as any)?.status || 'succeeded'
        if (run.value) run.value = { ...run.value, status }
        refreshRun(runId)
      }
    } catch {
      /* ignore malformed event */
    }
  }
  socket.onerror = () => {
    /* polling fallback below */
  }
  socket.onclose = () => {
    if (run.value?.status === 'running') refreshRun(runId)
  }
}

async function refreshRun(runId: string) {
  try {
    const detail = await api<Run>(`/api/runs/${runId}`)
    run.value = detail
    if (detail.status !== 'running' && !events.value.some((event) => event.type === 'run.finished')) {
      const backlog = await api<RunEvent[]>(`/api/runs/${runId}/events`)
      events.value = backlog
    }
    if (detail.status !== 'running') {
      window.clearInterval(pollTimer)
    }
    refreshMeta()
  } catch {
    /* ignore */
  }
}

function startPolling(runId: string) {
  window.clearInterval(pollTimer)
  pollTimer = window.setInterval(() => {
    if (!run.value || run.value.status !== 'running') {
      window.clearInterval(pollTimer)
      return
    }
    refreshRun(runId)
  }, 1200)
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

function goBack() {
  if (dirty.value && !window.confirm('有未保存的修改，仍要离开吗？')) return
  router.push('/workflows')
}

function onKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
    event.preventDefault()
    save()
  }
  if (event.key === 'Delete' || event.key === 'Backspace') {
    if (selectedId.value) {
      event.preventDefault()
      deleteNode()
    }
  }
  if (event.key === 'Escape') selectedId.value = null
  if (event.key === 'f' && !event.metaKey && !event.ctrlKey) canvasRef.value?.fitView()
}

watch(
  () => route.params.id,
  () => load(),
)

onMounted(async () => {
  await load()
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  window.clearTimeout(validateTimer)
  window.clearInterval(pollTimer)
  if (socket) {
    socket.onclose = null
    socket.close()
  }
})
</script>

<template>
  <div class="editor">
    <header class="editor-top">
      <div class="top-left">
        <button class="icon-btn" title="返回工作流" @click="goBack">
          <AppIcon name="arrowLeft" :size="16" />
        </button>
        <div class="crumb">
          <RouterLink to="/workflows" class="crumb-link">工作流</RouterLink>
          <span class="crumb-sep">/</span>
          <input v-model="nameInput" class="name-input" :placeholder="workflow?.name" @input="markDirty" />
        </div>
        <span v-if="dirty" class="dirty-dot" title="有未保存的修改" />
      </div>

      <div class="top-center">
        <span v-if="errorCount" class="chip danger"><AppIcon name="warning" :size="12" /> {{ errorCount }} 个错误</span>
        <span v-else-if="warningCount" class="chip amber"><AppIcon name="dot" :size="12" /> {{ warningCount }} 个提示</span>
        <span v-else class="chip success"><AppIcon name="check" :size="12" /> 结构有效</span>
        <span class="chip mono">{{ graph.nodes.length }} nodes · {{ graph.edges.length }} edges</span>
      </div>

      <div class="top-actions">
        <button class="btn btn-sm" :disabled="saving" @click="save()">
          <AppIcon name="save" :size="13" /> {{ saving ? '保存中' : '保存' }}
        </button>
        <button v-if="run?.status !== 'running'" class="btn btn-sm btn-primary" @click="startRun">
          <AppIcon name="play" :size="13" /> 运行
        </button>
        <button v-else class="btn btn-sm btn-danger" @click="stopRun">
          <AppIcon name="stop" :size="13" /> 停止
        </button>
        <button class="btn btn-sm btn-icon" title="显示/隐藏运行控制台" @click="dockOpen = !dockOpen">
          <AppIcon name="panel" :size="14" />
        </button>
      </div>
    </header>

    <div class="editor-main">
      <NodePalette :contracts="contracts" @add="addNode" />
      <div class="canvas-wrap">
        <div v-if="loading" class="canvas-loading">正在加载画布...</div>
        <WorkflowCanvas
          v-else
          ref="canvasRef"
          :graph="graph"
          :contracts="contracts"
          :selected-id="selectedId"
          :run-states="runStates"
          @select="selectedId = $event"
          @node-moved="onNodeMoved"
          @connect="connect"
          @delete-edge="deleteEdge"
        />
        <div class="canvas-tools">
          <button class="tool-btn" title="缩小" @click="canvasRef?.zoomBy(0.88)">
            <AppIcon name="zoomOut" :size="14" />
          </button>
          <button class="tool-btn" title="放大" @click="canvasRef?.zoomBy(1.12)">
            <AppIcon name="zoomIn" :size="14" />
          </button>
          <button class="tool-btn" title="适配画布（F）" @click="canvasRef?.fitView()">
            <AppIcon name="fit" :size="14" />
          </button>
        </div>
        <div v-if="run?.status === 'running'" class="live-ribbon">
          <span class="status-dot running" />
          {{ run.workflowName }} 正在运行 · 节点 {{ events.filter((e) => e.type === 'node.finished').length }} 完成
        </div>
      </div>
      <InspectorPanel
        :workflow="workflow"
        :node="selectedNode"
        :contract="selectedContract"
        :resources="resources"
        :issues="issues"
        :last-outputs="lastOutputs"
        :target="targetInfo"
        @update-config="updateConfig"
        @update-description="onDescriptionUpdate"
        @delete="deleteNode"
        @duplicate="duplicateNode"
        @close="selectedId = null"
      />
    </div>

    <RunDock
      :open="dockOpen"
      :run="run"
      :events="events"
      :node-names="nodeNames"
      @close="dockOpen = false"
      @stop="stopRun"
    />
  </div>
</template>

<style scoped>
.editor {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5fbff;
  overflow: hidden;
}

.editor-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  height: 56px;
  padding: 0 14px;
  border-bottom: 1px solid var(--border-soft);
  background: rgba(255, 255, 255, 0.96);
  flex: none;
}

.top-left,
.top-actions,
.top-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.crumb {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.crumb-link {
  font-size: 11px;
  color: var(--faint);
  white-space: nowrap;
  flex: none;
}

.crumb-link:hover {
  color: var(--primary);
}

.crumb-sep {
  color: var(--faint);
  font-size: 11px;
}

.name-input {
  width: clamp(120px, 22vw, 320px);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 3px 6px;
  font-size: 13.5px;
  font-weight: 620;
  letter-spacing: -0.01em;
  color: var(--text);
  outline: none;
  text-overflow: ellipsis;
}

.name-input:hover,
.name-input:focus {
  border-color: var(--border);
  background: rgba(255, 255, 255, 0.025);
}

.dirty-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--amber);
  box-shadow: 0 0 8px rgba(251, 191, 36, 0.5);
}

.top-center {
  gap: 6px;
  min-width: 0;
  overflow: hidden;
}

.top-actions {
  flex: none;
}

.editor-main {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 236px minmax(0, 1fr) 306px;
}

.canvas-wrap {
  position: relative;
  min-width: 0;
  min-height: 0;
  background: #f5fbff;
}

.canvas-loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--faint);
  font-size: 12px;
}

.canvas-tools {
  position: absolute;
  right: 14px;
  top: 14px;
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(190, 220, 237, 0.72);
  backdrop-filter: blur(8px);
}

.tool-btn {
  width: 27px;
  height: 27px;
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

.live-ribbon {
  position: absolute;
  top: 15px;
  left: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 11px;
  border-radius: 8px;
  border: 1px solid rgba(14, 165, 233, 0.2);
  background: rgba(235, 250, 255, 0.88);
  font-size: 10.5px;
  color: var(--primary);
  backdrop-filter: blur(8px);
}

.icon-btn {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 7px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--muted);
}

.icon-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text);
}

@media (max-width: 1280px) {
  .editor-main {
    grid-template-columns: 210px minmax(0, 1fr) 280px;
  }
}

@media (max-width: 1120px) {
  .top-center {
    display: none;
  }
}

@media (max-width: 1020px) {
  .editor-main {
    grid-template-columns: 200px minmax(0, 1fr);
  }
  .inspector {
    display: none;
  }
}

@media (max-width: 760px) {
  .crumb-link,
  .crumb-sep {
    display: none;
  }
  .name-input {
    width: 132px;
  }
  .editor-main {
    grid-template-columns: 176px minmax(0, 1fr);
  }
}
</style>
