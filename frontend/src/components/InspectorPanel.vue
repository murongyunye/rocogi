<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import type { GraphNode, NodeContract, Resource, Workflow } from '../types'

const props = defineProps<{
  workflow: Workflow | null
  node: GraphNode | null
  contract: NodeContract | null
  resources: Resource[]
  issues: { level: string; message: string; node_id?: string }[]
  lastOutputs: Record<string, unknown> | null
  target: Record<string, unknown> | null
}>()

const emit = defineEmits<{
  'update-config': [key: string, value: unknown]
  'update-description': [value: string]
  delete: []
  duplicate: []
  close: []
}>()

const templateOptions = computed(() =>
  props.resources
    .filter((resource) => resource.kind === 'template')
    .map((resource) => ({ value: resource.name, label: resource.name })),
)

const nodeIssues = computed(() =>
  props.issues.filter((issue) => props.node && issue.node_id === props.node.id),
)

function valueFor(key: string): unknown {
  if (!props.node) return undefined
  const field = props.contract?.fields.find((item) => item.key === key)
  const value = props.node.config?.[key]
  return value === undefined ? field?.default : value
}

function setValue(key: string, value: unknown) {
  emit('update-config', key, value)
}

function onTextInput(key: string, event: Event) {
  setValue(key, (event.target as HTMLInputElement).value)
}

function onNumberInput(key: string, event: Event) {
  const value = (event.target as HTMLInputElement).value
  setValue(key, value === '' ? '' : Number(value))
}

function onToggle(key: string) {
  setValue(key, !valueFor(key))
}

function optionsFor(field: NodeContract['fields'][number]) {
  if (field.type === 'resource') return templateOptions.value
  return field.options || []
}

function formatOutput(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'object') return JSON.stringify(value).slice(0, 100)
  return String(value)
}
</script>

<template>
  <aside class="inspector">
    <div v-if="node && contract" class="inspector-inner">
      <div class="inspector-head">
        <div class="ins-icon" :style="{ color: contract.accent, background: `${contract.accent}14` }">
          <AppIcon name="node" :size="16" />
        </div>
        <div class="ins-title-wrap">
          <div class="ins-title">{{ node.title || contract.title }}</div>
          <div class="ins-type mono">{{ node.type }}</div>
        </div>
        <button class="icon-btn" title="取消选择" @click="emit('close')">
          <AppIcon name="close" :size="14" />
        </button>
      </div>

      <div class="ins-desc">{{ contract.description }}</div>

      <div v-if="nodeIssues.length" class="issue-stack">
        <div v-for="(issue, index) in nodeIssues" :key="index" class="issue-row" :class="issue.level">
          <AppIcon :name="issue.level === 'error' ? 'warning' : 'dot'" :size="12" />
          {{ issue.message }}
        </div>
      </div>

      <div class="ins-section">
        <div class="ins-section-title">配置</div>
        <div v-for="field in contract.fields" :key="field.key" class="field">
          <template v-if="field.type === 'boolean'">
            <div class="toggle-row" style="padding: 2px 0">
              <div>
                <div class="field-label">{{ field.label }}</div>
                <div v-if="field.help" class="field-help">{{ field.help }}</div>
              </div>
              <div class="toggle" :class="{ on: Boolean(valueFor(field.key)) }" @click="onToggle(field.key)" />
            </div>
          </template>
          <template v-else>
            <div class="field-label">
              <span>{{ field.label }}<span v-if="field.required" class="req">*</span></span>
            </div>

            <select
              v-if="field.type === 'select' || field.type === 'resource' || field.type === 'target'"
              class="select"
              :value="String(valueFor(field.key) ?? '')"
              @change="onTextInput(field.key, $event)"
            >
              <option value="" disabled>请选择</option>
              <option
                v-for="option in optionsFor(field)"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>

            <input
              v-else-if="field.type === 'number'"
              class="input"
              type="number"
              :min="field.minimum"
              :max="field.maximum"
              :step="field.step"
              :value="valueFor(field.key)"
              @input="onNumberInput(field.key, $event)"
            />

            <textarea
              v-else-if="field.type === 'textarea'"
              class="textarea"
              :rows="field.rows || 3"
              :value="String(valueFor(field.key) ?? '')"
              :placeholder="field.placeholder"
              @input="onTextInput(field.key, $event)"
            />

            <input
              v-else
              class="input"
              :class="{ mono: field.type === 'expression' }"
              :value="String(valueFor(field.key) ?? '')"
              :placeholder="field.placeholder"
              @input="onTextInput(field.key, $event)"
            />

            <div v-if="field.help" class="field-help">{{ field.help }}</div>
          </template>
        </div>

        <div v-if="!contract.fields.length" class="no-fields">该节点没有可配置字段</div>
      </div>

      <div class="ins-section">
        <div class="ins-section-title">节点信息</div>
        <div class="meta-grid">
          <span class="meta-key">ID</span><span class="meta-val mono">{{ node.id }}</span>
          <span class="meta-key">位置</span><span class="meta-val mono">{{ node.x }}, {{ node.y }}</span>
          <span class="meta-key">输出</span><span class="meta-val mono">{{ contract.outputs.map((o) => o.label).join(' / ') || '—' }}</span>
        </div>
      </div>

      <div v-if="lastOutputs" class="ins-section">
        <div class="ins-section-title">最近一次输出</div>
        <div class="output-list">
          <div v-for="(value, key) in lastOutputs" :key="String(key)" class="output-row">
            <span class="output-key mono">{{ key }}</span>
            <span class="output-value mono">{{ formatOutput(value) }}</span>
          </div>
        </div>
      </div>

      <div class="ins-actions">
        <button class="btn btn-sm" @click="emit('duplicate')">
          <AppIcon name="copy" :size="13" /> 复制
        </button>
        <button class="btn btn-sm btn-danger" @click="emit('delete')">
          <AppIcon name="trash" :size="13" /> 删除节点
        </button>
      </div>
    </div>

    <div v-else class="inspector-overview">
      <div class="ins-section">
        <div class="ins-section-title">工作流概览</div>
        <div v-if="workflow" class="overview-name">{{ workflow.name }}</div>
        <textarea
          v-if="workflow"
          class="textarea overview-edit"
          rows="3"
          :value="workflow.description"
          placeholder="补充这条工作流的用途与注意事项..."
          @input="emit('update-description', ($event.target as HTMLTextAreaElement).value)"
        />
        <div class="meta-grid" style="margin-top: 14px">
          <span class="meta-key">节点</span><span class="meta-val mono">{{ workflow?.graph?.nodes?.length || 0 }}</span>
          <span class="meta-key">连线</span><span class="meta-val mono">{{ workflow?.graph?.edges?.length || 0 }}</span>
          <span class="meta-key">修订</span><span class="meta-val mono">r{{ workflow?.revision || 1 }}</span>
          <span class="meta-key">目标槽位</span><span class="meta-val mono">{{ workflow?.targetSlot || 'nrc-game' }}</span>
        </div>
      </div>

      <div class="ins-section">
        <div class="ins-section-title">本机目标</div>
        <div class="target-card">
          <div class="target-head">
            <span class="status-dot" :class="target?.kind === 'windows' ? 'succeeded' : 'running'" />
            <span>{{ target?.kind === 'windows' ? 'Windows 窗口' : '模拟目标' }}</span>
            <span class="chip primary" style="margin-left: auto">已绑定</span>
          </div>
          <div class="target-detail mono">
            {{ target?.title || '洛克王国：世界（模拟窗口）' }}
            <span v-if="target?.width"> · {{ target.width }}×{{ target.height }}</span>
          </div>
        </div>
      </div>

      <div class="ins-section">
        <div class="ins-section-title">校验</div>
        <div v-if="!issues.length" class="ok-row"><AppIcon name="check" :size="13" /> 工作流结构有效</div>
        <div v-for="(issue, index) in issues" :key="index" class="issue-row" :class="issue.level">
          <AppIcon :name="issue.level === 'error' ? 'warning' : 'dot'" :size="12" />
          {{ issue.message }}
        </div>
      </div>

      <div class="ins-section">
        <div class="ins-section-title">使用提示</div>
        <div class="hint-card">
          <p>· 从左侧节点库点击添加节点，拖动节点调整布局。</p>
          <p>· 从节点右侧端口拖线到另一个节点的左侧端口。</p>
          <p>· 字段可填写表达式，例如 <span class="mono">nodes.classify.isBattle</span>。</p>
          <p>· 运行前会自动保存；截图与日志会写入运行记录。</p>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.inspector {
  min-height: 0;
  overflow: auto;
  border-left: 1px solid var(--border-soft);
  background: rgba(255, 255, 255, 0.94);
}

.inspector-inner,
.inspector-overview {
  padding: 15px 16px 18px;
}

.inspector-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ins-icon {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: grid;
  place-items: center;
}

.ins-title-wrap {
  min-width: 0;
  flex: 1;
}

.ins-title {
  font-size: 13.5px;
  font-weight: 620;
  letter-spacing: -0.01em;
}

.ins-type {
  font-size: 9.5px;
  color: var(--faint);
  margin-top: 1px;
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

.ins-desc {
  margin-top: 10px;
  font-size: 10.5px;
  line-height: 1.6;
  color: var(--muted);
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-soft);
}

.ins-section {
  padding-top: 15px;
}

.ins-section-title {
  font-size: 10px;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: var(--faint);
  margin-bottom: 10px;
}

.field + .field {
  margin-top: 13px;
}

.req {
  color: var(--danger);
  margin-left: 3px;
}

.no-fields {
  font-size: 11px;
  color: var(--faint);
  padding: 6px 0;
}

.meta-grid {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 7px 10px;
  font-size: 10.5px;
}

.meta-key {
  color: var(--faint);
}

.meta-val {
  color: var(--text-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.output-list {
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  overflow: hidden;
}

.output-row {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 8px;
  padding: 7px 9px;
  font-size: 9.5px;
  border-bottom: 1px solid rgba(214, 234, 245, 0.6);
}

.output-row:last-child {
  border-bottom: none;
}

.output-key {
  color: var(--primary);
  overflow: hidden;
  text-overflow: ellipsis;
}

.output-value {
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ins-actions {
  display: flex;
  gap: 7px;
  margin-top: 18px;
  padding-top: 15px;
  border-top: 1px solid var(--border-soft);
}

.issue-stack {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.issue-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 10px;
  line-height: 1.5;
  color: var(--muted);
  background: rgba(255, 255, 255, 0.025);
}

.issue-row.error {
  color: #fca5a5;
  background: rgba(248, 113, 113, 0.07);
}

.issue-row.warning {
  color: var(--amber);
  background: rgba(251, 191, 36, 0.06);
}

.ok-row {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  color: var(--success);
}

.overview-name {
  font-size: 15px;
  font-weight: 620;
  letter-spacing: -0.02em;
}

.overview-desc {
  margin-top: 6px;
  font-size: 11px;
  line-height: 1.6;
  color: var(--muted);
}

.overview-edit {
  margin-top: 9px;
  font-size: 11px;
  min-height: 58px;
}

.target-card {
  border: 1px solid var(--border-soft);
  border-radius: 9px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.02);
}

.target-head {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11.5px;
}

.target-detail {
  margin-top: 6px;
  font-size: 9.5px;
  color: var(--faint);
  line-height: 1.5;
}

.hint-card {
  font-size: 10.5px;
  line-height: 1.7;
  color: var(--faint);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hint-card .mono {
  color: var(--primary);
}
</style>
