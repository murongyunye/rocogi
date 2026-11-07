<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import AppIcon from './AppIcon.vue'
import type { GraphNode, NodeContract, WorkflowGraph } from '../types'

const props = defineProps<{
  graph: WorkflowGraph
  contracts: NodeContract[]
  selectedId: string | null
  runStates: Record<string, string>
}>()

const emit = defineEmits<{
  select: [id: string | null]
  'node-moved': [id: string, x: number, y: number]
  connect: [from: string, fromPort: string, to: string]
  'delete-edge': [id: string]
}>()

const NODE_W = 232
const HEADER_H = 46
const OUT_START = 68

const canvasRef = ref<HTMLDivElement | null>(null)
const view = reactive({ x: 40, y: 40, scale: 0.86 })
const connecting = ref<{ from: string; fromPort: string; sx: number; sy: number; x: number; y: number } | null>(null)

const nodeMap = computed(() => new Map((props.graph.nodes || []).map((node) => [node.id, node])))
const contractMap = computed(() => new Map(props.contracts.map((contract) => [contract.type, contract])))

const edges = computed(() => {
  const result: { id: string; path: string; running: boolean }[] = []
  for (const edge of props.graph.edges || []) {
    const from = nodeMap.value.get(edge.from)
    const to = nodeMap.value.get(edge.to)
    if (!from || !to) continue
    const contract = contractMap.value.get(from.type)
    const outputIndex = Math.max(0, (contract?.outputs || []).findIndex((port) => port.id === edge.fromPort))
    const sx = from.x + NODE_W
    const sy = from.y + outputY(outputIndex)
    const tx = to.x
    const ty = to.y + HEADER_H
    const dx = Math.max(36, Math.abs(tx - sx) * 0.55)
    const path = `M ${sx} ${sy} C ${sx + dx} ${sy}, ${tx - dx} ${ty}, ${tx} ${ty}`
    result.push({ id: edge.id, path, running: props.runStates[from.id] === 'running' })
  }
  return result
})

const gridStyle = computed(() => ({
  backgroundSize: `${24 * view.scale}px ${24 * view.scale}px`,
  backgroundPosition: `${view.x}px ${view.y}px`,
}))

function outputY(index: number): number {
  return OUT_START + index * 20
}

function nodeHeight(node: GraphNode): number {
  const contract = contractMap.value.get(node.type)
  const outputs = contract?.outputs?.length || 1
  return Math.max(92, 78 + Math.max(0, outputs - 1) * 20)
}

function contractOf(node: GraphNode): NodeContract | undefined {
  return contractMap.value.get(node.type)
}

function iconFor(node: GraphNode): string {
  const category = contractOf(node)?.category || 'flow'
  const map: Record<string, string> = {
    run: 'target',
    flow: 'route',
    capture: 'image',
    vision: 'search',
    game: 'spark',
    map: 'map',
    battle: 'battle',
    input: 'cpu',
    net: 'external',
  }
  return map[category] || 'node'
}

function accentOf(node: GraphNode): string {
  return contractOf(node)?.accent || '#94a3b8'
}

function titleOf(node: GraphNode): string {
  return node.title || contractOf(node)?.title || node.type
}

function summaryLines(node: GraphNode): string[] {
  const contract = contractOf(node)
  if (!contract) return [node.type]
  const lines: string[] = []
  for (const field of contract.fields) {
    const value = node.config?.[field.key]
    if (value === undefined || value === null || value === '') continue
    if (field.type === 'boolean') {
      lines.push(`${field.label} ${value ? '开' : '关'}`)
    } else {
      lines.push(`${field.label} ${String(value).slice(0, 28)}`)
    }
    if (lines.length >= 2) break
  }
  return lines.length ? lines : [contract.description.slice(0, 30)]
}

function outputLabel(node: GraphNode, index: number): string {
  const contract = contractOf(node)
  return contract?.outputs?.[index]?.label || ''
}

// ---------------------------------------------------------------- transform
function toWorld(clientX: number, clientY: number) {
  const rect = canvasRef.value!.getBoundingClientRect()
  return {
    x: (clientX - rect.left - view.x) / view.scale,
    y: (clientY - rect.top - view.y) / view.scale,
  }
}

function zoomBy(factor: number, cx?: number, cy?: number) {
  const rect = canvasRef.value?.getBoundingClientRect()
  if (!rect) return
  const px = cx ?? rect.width / 2
  const py = cy ?? rect.height / 2
  const next = Math.min(1.8, Math.max(0.28, view.scale * factor))
  const wx = (px - view.x) / view.scale
  const wy = (py - view.y) / view.scale
  view.scale = next
  view.x = px - wx * next
  view.y = py - wy * next
}

function onWheel(event: WheelEvent) {
  event.preventDefault()
  const rect = canvasRef.value!.getBoundingClientRect()
  const factor = event.deltaY < 0 ? 1.12 : 0.89
  zoomBy(factor, event.clientX - rect.left, event.clientY - rect.top)
}

// ------------------------------------------------------------------- pan
let panState: { startX: number; startY: number; ox: number; oy: number } | null = null

function onCanvasPointerDown(event: PointerEvent) {
  if (event.button !== 0) return
  const target = event.target as HTMLElement
  if (target.closest('.node-card') || target.closest('.edge-hit')) return
  emit('select', null)
  panState = { startX: event.clientX, startY: event.clientY, ox: view.x, oy: view.y }
  window.addEventListener('pointermove', onPanMove)
  window.addEventListener('pointerup', onPanUp)
}

function onPanMove(event: PointerEvent) {
  if (!panState) return
  view.x = panState.ox + (event.clientX - panState.startX)
  view.y = panState.oy + (event.clientY - panState.startY)
}

function onPanUp() {
  panState = null
  window.removeEventListener('pointermove', onPanMove)
  window.removeEventListener('pointerup', onPanUp)
}

// ------------------------------------------------------------------- nodes
let dragState: { id: string; startX: number; startY: number; ox: number; oy: number } | null = null

function onNodePointerDown(event: PointerEvent, node: GraphNode) {
  if (event.button !== 0) return
  const target = event.target as HTMLElement
  if (target.closest('.port')) return
  emit('select', node.id)
  dragState = { id: node.id, startX: event.clientX, startY: event.clientY, ox: node.x, oy: node.y }
  window.addEventListener('pointermove', onNodeMove)
  window.addEventListener('pointerup', onNodeUp)
  event.stopPropagation()
}

function onNodeMove(event: PointerEvent) {
  if (!dragState) return
  const node = nodeMap.value.get(dragState.id)
  if (!node) return
  node.x = Math.round(dragState.ox + (event.clientX - dragState.startX) / view.scale)
  node.y = Math.round(dragState.oy + (event.clientY - dragState.startY) / view.scale)
}

function onNodeUp() {
  if (dragState) {
    const node = nodeMap.value.get(dragState.id)
    if (node) emit('node-moved', node.id, node.x, node.y)
  }
  dragState = null
  window.removeEventListener('pointermove', onNodeMove)
  window.removeEventListener('pointerup', onNodeUp)
}

// ------------------------------------------------------------------- connect
function startConnect(event: PointerEvent, node: GraphNode, portId: string) {
  event.stopPropagation()
  event.preventDefault()
  const contract = contractOf(node)
  const index = Math.max(0, (contract?.outputs || []).findIndex((port) => port.id === portId))
  const start = { x: node.x + NODE_W, y: node.y + outputY(index) }
  const world = toWorld(event.clientX, event.clientY)
  connecting.value = { from: node.id, fromPort: portId, sx: start.x, sy: start.y, x: world.x, y: world.y }
  window.addEventListener('pointermove', onConnectMove)
  window.addEventListener('pointerup', onConnectUp)
}

function onConnectMove(event: PointerEvent) {
  if (!connecting.value) return
  const world = toWorld(event.clientX, event.clientY)
  connecting.value.x = world.x
  connecting.value.y = world.y
}

function onConnectUp(event: PointerEvent) {
  if (connecting.value) {
    const element = document.elementFromPoint(event.clientX, event.clientY) as HTMLElement | null
    const input = element?.closest('[data-input-node]') as HTMLElement | null
    if (input?.dataset.inputNode) {
      emit('connect', connecting.value.from, connecting.value.fromPort, input.dataset.inputNode)
    }
  }
  connecting.value = null
  window.removeEventListener('pointermove', onConnectMove)
  window.removeEventListener('pointerup', onConnectUp)
}

const tempPath = computed(() => {
  if (!connecting.value) return ''
  const { sx, sy, x, y } = connecting.value
  const dx = Math.max(30, Math.abs(x - sx) * 0.5)
  return `M ${sx} ${sy} C ${sx + dx} ${sy}, ${x - dx} ${y}, ${x} ${y}`
})

function removeEdge(edgeId: string, event: MouseEvent) {
  event.stopPropagation()
  emit('delete-edge', edgeId)
}

// ------------------------------------------------------------------- fit
function fitView() {
  const nodes = props.graph.nodes || []
  const el = canvasRef.value
  if (!el || !nodes.length) {
    view.x = 40
    view.y = 40
    view.scale = 0.86
    return
  }
  const minX = Math.min(...nodes.map((node) => node.x))
  const minY = Math.min(...nodes.map((node) => node.y))
  const maxX = Math.max(...nodes.map((node) => node.x + NODE_W))
  const maxY = Math.max(...nodes.map((node) => node.y + 110))
  const pad = 40
  const scale = Math.min(
    1.1,
    (el.clientWidth - pad * 2) / Math.max(maxX - minX, 1),
    (el.clientHeight - pad * 2) / Math.max(maxY - minY, 1),
  )
  view.scale = Math.max(0.35, Math.min(scale, 1.1))
  view.x = pad + (el.clientWidth - pad * 2 - (maxX - minX) * view.scale) / 2 - minX * view.scale
  view.y = pad + (el.clientHeight - pad * 2 - (maxY - minY) * view.scale) / 2 - minY * view.scale
}

function viewportCenter() {
  const el = canvasRef.value
  if (!el) return { x: 200, y: 200 }
  return {
    x: (el.clientWidth / 2 - view.x) / view.scale - NODE_W / 2,
    y: (el.clientHeight / 2 - view.y) / view.scale - 50,
  }
}

function focusStart() {
  const el = canvasRef.value
  const nodes = props.graph.nodes || []
  if (!el || !nodes.length) return
  const start = nodes.find((node) => node.type === 'run.start') || nodes.reduce((a, b) => (a.x <= b.x ? a : b))
  const minY = Math.min(...nodes.map((node) => node.y))
  const maxY = Math.max(...nodes.map((node) => node.y + nodeHeight(node)))
  const scale = 0.78
  view.scale = scale
  view.x = 48 - start.x * scale
  view.y = Math.max(32, (el.clientHeight - (maxY - minY) * scale) / 2 - minY * scale)
}

onBeforeUnmount(() => {
  onPanUp()
  onNodeUp()
  if (connecting.value) onConnectUp(new PointerEvent('pointerup'))
})

defineExpose({ fitView, focusStart, zoomBy, viewportCenter, view })
</script>

<template>
  <div
    ref="canvasRef"
    class="canvas"
    :style="gridStyle"
    @pointerdown="onCanvasPointerDown"
    @wheel="onWheel"
  >
    <div class="canvas-layer" :style="{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})` }">
      <svg class="edges" width="1" height="1">
        <path
          v-for="edge in edges"
          :key="edge.id"
          :d="edge.path"
          class="edge-path"
          :class="{ running: edge.running }"
        />
        <path
          v-for="edge in edges"
          :key="`hit-${edge.id}`"
          :d="edge.path"
          class="edge-hit"
          @click="removeEdge(edge.id, $event)"
        >
          <title>点击删除这条连线</title>
        </path>
        <path v-if="tempPath" :d="tempPath" class="edge-temp" />
      </svg>

      <div
        v-for="node in graph.nodes"
        :key="node.id"
        class="node-card"
        :class="[
          `run-${runStates[node.id] || 'idle'}`,
          { selected: selectedId === node.id, disabled: node.disabled },
        ]"
        :style="{ left: `${node.x}px`, top: `${node.y}px`, width: `${NODE_W}px`, height: `${nodeHeight(node)}px` }"
        @pointerdown="onNodePointerDown($event, node)"
      >
        <div class="node-accent" :style="{ background: accentOf(node) }" />
        <div class="node-head">
          <div class="node-icon" :style="{ color: accentOf(node), background: `${accentOf(node)}14` }">
            <AppIcon :name="iconFor(node)" :size="15" />
          </div>
          <div class="node-title-wrap">
            <div class="node-title">{{ titleOf(node) }}</div>
            <div class="node-type mono">{{ node.type }}</div>
          </div>
          <span class="node-run-dot" />
        </div>
        <div class="node-body">
          <div v-for="(line, index) in summaryLines(node)" :key="index" class="node-summary">{{ line }}</div>
        </div>
        <div class="port in-port" data-input-node-target :data-input-node="node.id" :style="{ top: `${HEADER_H}px` }" />
        <div
          v-for="(port, index) in contractOf(node)?.outputs || []"
          :key="port.id"
          class="port out-port"
          :style="{ top: `${outputY(index)}px` }"
          @pointerdown="startConnect($event, node, port.id)"
        >
          <span class="port-label">{{ outputLabel(node, index) }}</span>
        </div>
      </div>
    </div>

    <div class="canvas-hint">
      <span class="mono">{{ Math.round(view.scale * 100) }}%</span>
      <span>拖动画布 · 滚轮缩放 · 从右侧端口拖线连接</span>
    </div>
  </div>
</template>

<style scoped>
.canvas {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background-color: #f5fbff;
  background-image: radial-gradient(rgba(122, 151, 176, 0.16) 1px, transparent 1px);
  cursor: grab;
}

.canvas:active {
  cursor: grabbing;
}

.canvas-layer {
  position: absolute;
  inset: 0 auto auto 0;
  transform-origin: 0 0;
  will-change: transform;
}

.edges {
  position: absolute;
  left: 0;
  top: 0;
  overflow: visible;
  pointer-events: none;
}

.edge-path {
  fill: none;
  stroke: rgba(127, 158, 185, 0.42);
  stroke-width: 1.6;
  stroke-linecap: round;
}

.edge-path.running {
  stroke: rgba(14, 165, 233, 0.75);
  stroke-width: 2.2;
  filter: drop-shadow(0 0 6px rgba(14, 165, 233, 0.45));
}

.edge-hit {
  fill: none;
  stroke: transparent;
  stroke-width: 16;
  cursor: pointer;
  pointer-events: stroke;
}

.edge-hit:hover {
  stroke: rgba(248, 113, 113, 0.35);
}

.edge-temp {
  fill: none;
  stroke: rgba(14, 165, 233, 0.8);
  stroke-width: 2;
  stroke-dasharray: 6 5;
}

.node-card {
  position: absolute;
  border-radius: 11px;
  border: 1px solid #283849;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.98));
  box-shadow: 0 10px 26px rgba(0, 0, 0, 0.35);
  cursor: default;
  user-select: none;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.node-card:hover {
  border-color: #375069;
}

.node-card.selected {
  border-color: rgba(14, 165, 233, 0.65);
  box-shadow: 0 0 0 1px rgba(14, 165, 233, 0.22), 0 14px 34px rgba(0, 0, 0, 0.45);
}

.node-card.run-running {
  border-color: rgba(14, 165, 233, 0.75);
  animation: node-glow 1.4s ease-in-out infinite;
}

.node-card.run-succeeded {
  border-color: rgba(52, 211, 153, 0.32);
}

.node-card.run-failed {
  border-color: rgba(248, 113, 113, 0.62);
}

.node-card.disabled {
  opacity: 0.5;
}

@keyframes node-glow {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(14, 165, 233, 0.16), 0 10px 26px rgba(0, 0, 0, 0.35);
  }
  50% {
    box-shadow: 0 0 0 5px rgba(14, 165, 233, 0.05), 0 10px 30px rgba(0, 0, 0, 0.4);
  }
}

.node-accent {
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 2px;
  border-radius: 2px;
  opacity: 0.8;
}

.node-head {
  display: flex;
  align-items: center;
  gap: 9px;
  height: 46px;
  padding: 0 12px 0 13px;
  border-bottom: 1px solid rgba(190, 220, 237, 0.55);
}

.node-icon {
  width: 27px;
  height: 27px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  flex: none;
  border: 1px solid rgba(255, 255, 255, 0.03);
}

.node-title-wrap {
  min-width: 0;
  flex: 1;
}

.node-title {
  font-size: 12.5px;
  font-weight: 620;
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-type {
  font-size: 9px;
  color: var(--faint);
  letter-spacing: 0.04em;
  margin-top: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-run-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: transparent;
  flex: none;
}

.run-running .node-run-dot {
  background: var(--primary);
  box-shadow: 0 0 8px rgba(14, 165, 233, 0.8);
}

.run-succeeded .node-run-dot {
  background: var(--success);
}

.run-failed .node-run-dot {
  background: var(--danger);
}

.node-body {
  padding: 8px 13px 6px;
}

.node-summary {
  font-size: 9.5px;
  line-height: 1.6;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-summary + .node-summary {
  color: var(--faint);
}

.port {
  position: absolute;
  width: 13px;
  height: 13px;
  border-radius: 50%;
  transform: translateY(-50%);
  border: 2px solid #5c7a94;
  background: #ffffff;
  z-index: 2;
}

.in-port {
  left: -7px;
  cursor: crosshair;
}

.out-port {
  right: -7px;
  cursor: crosshair;
  border-color: rgba(14, 165, 233, 0.6);
}

.out-port:hover,
.in-port:hover {
  border-color: var(--primary);
  box-shadow: 0 0 0 4px rgba(14, 165, 233, 0.12);
}

.port-label {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-family: var(--mono);
  font-size: 8.5px;
  color: var(--faint);
  white-space: nowrap;
  pointer-events: none;
}

.canvas-hint {
  position: absolute;
  left: 16px;
  bottom: 14px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 6px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(190, 220, 237, 0.7);
  font-size: 10px;
  color: var(--faint);
  pointer-events: none;
  backdrop-filter: blur(8px);
}

.canvas-hint .mono {
  color: var(--primary);
  font-size: 10px;
}
</style>
