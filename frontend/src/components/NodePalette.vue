<script setup lang="ts">
import { computed, ref } from 'vue'
import AppIcon from './AppIcon.vue'
import type { NodeContract } from '../types'

const props = defineProps<{
  contracts: NodeContract[]
}>()

const emit = defineEmits<{
  add: [type: string]
}>()

const search = ref('')
const collapsed = ref<Record<string, boolean>>({})

const groups = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  const result: { category: string; label: string; accent: string; nodes: NodeContract[] }[] = []
  for (const contract of props.contracts) {
    if (
      keyword &&
      !contract.title.toLowerCase().includes(keyword) &&
      !contract.type.toLowerCase().includes(keyword) &&
      !contract.description.toLowerCase().includes(keyword) &&
      !contract.tags.join(' ').toLowerCase().includes(keyword)
    ) {
      continue
    }
    let group = result.find((item) => item.category === contract.category)
    if (!group) {
      group = {
        category: contract.category,
        label: contract.categoryLabel || contract.category,
        accent: contract.accent || '#94a3b8',
        nodes: [],
      }
      result.push(group)
    }
    group.nodes.push(contract)
  }
  return result
})

function toggle(category: string) {
  collapsed.value[category] = !collapsed.value[category]
}
</script>

<template>
  <aside class="palette">
    <div class="palette-head">
      <div class="panel-title"><AppIcon name="workflow" :size="15" /> 节点库</div>
      <span class="palette-count mono">{{ contracts.length }}</span>
    </div>
    <div class="palette-search">
      <AppIcon name="search" :size="14" />
      <input v-model="search" placeholder="搜索节点..." />
    </div>
    <div class="palette-scroll">
      <section v-for="group in groups" :key="group.category" class="palette-group">
        <button class="group-head" @click="toggle(group.category)">
          <span class="group-dot" :style="{ background: group.accent }" />
          <span class="group-name">{{ group.label }}</span>
          <span class="group-count mono">{{ group.nodes.length }}</span>
          <AppIcon
            name="chevron"
            :size="12"
            class="group-chevron"
            :style="{ transform: collapsed[group.category] ? 'rotate(-90deg)' : 'none' }"
          />
        </button>
        <div v-if="!collapsed[group.category]" class="group-list">
          <button
            v-for="contract in group.nodes"
            :key="contract.type"
            class="palette-node"
            :title="contract.description"
            @click="emit('add', contract.type)"
          >
            <span class="node-chip" :style="{ color: group.accent, background: `${group.accent}12` }">
              <span class="node-chip-dot" :style="{ background: group.accent }" />
            </span>
            <span class="node-info">
              <span class="node-name">{{ contract.title }}</span>
              <span class="node-desc">{{ contract.description }}</span>
            </span>
            <span class="node-add"><AppIcon name="plus" :size="13" /></span>
          </button>
        </div>
      </section>
      <div v-if="!groups.length" class="palette-empty">没有匹配的节点</div>
    </div>
    <div class="palette-foot">
      <div class="tip-line"><span class="tip-key mono" v-text="'{{ }}'"></span> 字段支持表达式</div>
      <div class="tip-line"><span class="tip-key mono">vars.x</span> 读取运行变量</div>
      <div class="tip-line"><span class="tip-key mono">nodes.id.field</span> 读取上游输出</div>
    </div>
  </aside>
</template>

<style scoped>
.palette {
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-right: 1px solid var(--border-soft);
  background: rgba(255, 255, 255, 0.92);
}

.palette-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 16px 10px;
}

.palette-count {
  font-size: 10px;
  color: var(--faint);
}

.palette-search {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 12px 10px;
  padding: 0 10px;
  height: 31px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.55);
  color: var(--faint);
}

.palette-search input {
  width: 100%;
  border: none;
  background: transparent;
  outline: none;
  font-size: 12px;
  color: var(--text);
}

.palette-search input::placeholder {
  color: var(--faint);
}

.palette-scroll {
  flex: 1;
  overflow: auto;
  padding: 0 10px 14px;
}

.palette-group + .palette-group {
  margin-top: 10px;
}

.group-head {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 6px 6px;
  border: none;
  background: transparent;
  color: var(--muted);
  text-align: left;
}

.group-head:hover {
  color: var(--text);
}

.group-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.group-name {
  font-size: 10.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 600;
}

.group-count {
  font-size: 9.5px;
  color: var(--faint);
}

.group-chevron {
  margin-left: auto;
  color: var(--faint);
  transition: transform 0.16s ease;
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.palette-node {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 8px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: transparent;
  text-align: left;
  color: var(--text-soft);
  transition: background 0.14s ease, border-color 0.14s ease;
}

.palette-node:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: var(--border-soft);
}

.node-chip {
  width: 24px;
  height: 24px;
  border-radius: 7px;
  display: grid;
  place-items: center;
  flex: none;
}

.node-chip-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.node-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.node-name {
  font-size: 11.5px;
  font-weight: 550;
}

.node-desc {
  font-size: 9.5px;
  color: var(--faint);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
}

.node-add {
  margin-left: auto;
  opacity: 0;
  color: var(--primary);
  transition: opacity 0.14s ease;
}

.palette-node:hover .node-add {
  opacity: 1;
}

.palette-empty {
  padding: 20px 10px;
  text-align: center;
  font-size: 11px;
  color: var(--faint);
}

.palette-foot {
  border-top: 1px solid var(--border-soft);
  padding: 10px 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tip-line {
  font-size: 9.5px;
  color: var(--faint);
  display: flex;
  align-items: center;
  gap: 7px;
}

.tip-key {
  color: var(--primary);
  background: rgba(14, 165, 233, 0.12);
  border: 1px solid rgba(14, 165, 233, 0.14);
  padding: 0 4px;
  border-radius: 3px;
  font-size: 9px;
}
</style>
