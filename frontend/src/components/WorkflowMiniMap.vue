<script setup lang="ts">
import { computed } from 'vue'
import type { NodeContract, WorkflowGraph } from '../types'

const props = defineProps<{
  graph: WorkflowGraph
  contracts: NodeContract[]
  height?: number
}>()

const view = computed(() => {
  const width = 240
  const height = props.height || 84
  const nodes = props.graph?.nodes || []
  if (!nodes.length) return { width, height, nodes: [], edges: [] }
  const xs = nodes.map((node) => Number(node.x) || 0)
  const ys = nodes.map((node) => Number(node.y) || 0)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const pad = 10
  const scale = Math.min(
    (width - pad * 2) / Math.max(maxX - minX, 1),
    (height - pad * 2) / Math.max(maxY - minY, 1),
    1.1,
  )
  const px = (x: number) => pad + ((x - minX) / Math.max(maxX - minX, 1)) * (width - pad * 2)
  const py = (y: number) => pad + ((y - minY) / Math.max(maxY - minY, 1)) * (height - pad * 2)
  const byId = new Map(nodes.map((node) => [node.id, node]))
  const points = nodes.map((node) => ({
    id: node.id,
    x: px(Number(node.x) || 0),
    y: py(Number(node.y) || 0),
    color: colorOf(node.type),
  }))
  const pointMap = new Map(points.map((point) => [point.id, point]))
  const edges = (props.graph.edges || [])
    .map((edge) => {
      const a = pointMap.get(edge.from)
      const b = pointMap.get(edge.to)
      return a && b ? { id: edge.id, x1: a.x, y1: a.y, x2: b.x, y2: b.y } : null
    })
    .filter(Boolean)
  return { width, height, nodes: points, edges }
})

function colorOf(type: string) {
  const contract = props.contracts.find((item) => item.type === type)
  return contract?.accent || '#0ea5e9'
}
</script>

<template>
  <svg
    :viewBox="`0 0 ${view.width} ${view.height}`"
    preserveAspectRatio="xMidYMid meet"
    class="mini-map"
    aria-hidden="true"
  >
    <line
      v-for="edge in view.edges"
      :key="edge.id"
      :x1="edge.x1"
      :y1="edge.y1"
      :x2="edge.x2"
      :y2="edge.y2"
      stroke="rgba(141, 164, 188, 0.28)"
      stroke-width="1"
    />
    <circle
      v-for="node in view.nodes"
      :key="node.id"
      :cx="node.x"
      :cy="node.y"
      :r="3.2"
      :fill="node.color"
      fill-opacity="0.86"
      stroke="#f6fbff"
      stroke-width="1.4"
    />
  </svg>
</template>

<style scoped>
.mini-map {
  width: 100%;
  display: block;
}
</style>
