<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../lib/api'
import { notify } from '../lib/toast'

interface Component {
  id: string
  name: string
  detail: string
  code: string
  engineId: string
  features: string[]
  reuse: number
  status: 'ready' | 'partial' | 'missing'
  statusNote: string
}

interface Engine {
  id: string
  name: string
  icon: string
  accent: string
  layer: string
  summary: string
  source: string
  components: Component[]
}

interface Feature {
  id: string
  name: string
  route: string
  icon: string
  accent: string
  summary: string
  components: string[]
  componentCount: number
  engineCount: number
  engines: string[]
}

interface Stats {
  engineCount: number
  componentCount: number
  featureCount: number
  bindingCount: number
  reusableComponents: number
  singleUseComponents: number
  readyComponents: number
  partialComponents: number
  gapCount: number
  maxReuse: number
  avgComponentsPerFeature: number
  avgEnginesPerFeature: number
  coverage: number
}

interface EngineGroup {
  id: string
  name: string
  exe: string
  engines: string[]
  summary: string
  actions: string[]
  componentCount: number
  readyCount: number
  components: string[]
}

interface Gap {
  id: string
  engine: string
  name: string
  status: 'missing' | 'partial'
  note: string
}

interface Registry {
  version: string
  principle: {
    title: string
    rules: string[]
    reference: { name: string; url: string; pattern: string }
  }
  stats: Stats
  engines: Engine[]
  features: Feature[]
  groups: EngineGroup[]
  gaps: Gap[]
  matrix: Record<string, Record<string, string[]>>
}

const registry = ref<Registry | null>(null)
const selected = ref('')

const engineMap = computed(() => {
  const map = new Map<string, Engine>()
  registry.value?.engines.forEach((engine) => map.set(engine.id, engine))
  return map
})

const featureMap = computed(() => {
  const map = new Map<string, Feature>()
  registry.value?.features.forEach((feature) => map.set(feature.id, feature))
  return map
})

const selectedFeature = computed(() => (selected.value ? featureMap.value.get(selected.value) : undefined))

const stats = computed(() => registry.value?.stats)

function isFeatureOn(id: string) {
  return !selected.value || selected.value === id
}

function isComponentOn(component: Component) {
  return !selected.value || component.features.includes(selected.value)
}

function toggleFeature(id: string) {
  selected.value = selected.value === id ? '' : id
}

function featureName(id: string) {
  return featureMap.value.get(id)?.name || id
}

function featureRoute(id: string) {
  return featureMap.value.get(id)?.route || '/launcher'
}

function cellCount(featureId: string, engineId: string) {
  return registry.value?.matrix?.[featureId]?.[engineId]?.length || 0
}

function cellTitle(featureId: string, engineId: string) {
  const ids = registry.value?.matrix?.[featureId]?.[engineId] || []
  const names = ids.map((id) => {
    const engine = engineMap.value.get(engineId)
    return engine?.components.find((component) => component.id === id)?.name || id
  })
  return names.length ? names.join('、') : '该功能不使用此引擎组元'
}

function engineName(id: string) {
  return engineMap.value.get(id)?.name || id
}

function statusLabel(status: string) {
  return status === 'ready' ? '已完善' : status === 'missing' ? '未实现' : '待完善'
}

function groupIcon(id: string) {
  return {
    sense: 'image',
    input: 'cpu',
    sift: 'target',
    battle: 'battle',
    flow: 'activity',
    core: 'node',
  }[id] || 'node'
}

async function load() {
  try {
    registry.value = await api<Registry>('/api/components')
  } catch (error) {
    notify(`读取组件图谱失败：${error}`, 'error')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <div class="eyebrow">Component Graph</div>
        <h1>组件图谱</h1>
        <p class="page-sub">
          功能不是引擎的复制品，而是组元的组合。每个功能只装配自己需要的那部分组元，同一个组元则同时服务多个功能。
        </p>
      </div>
      <div class="page-actions">
        <a
          v-if="registry"
          class="chip primary"
          :href="registry.principle.reference.url"
          target="_blank"
          rel="noreferrer"
        >
          <AppIcon name="external" :size="12" />
          参考 {{ registry.principle.reference.name }}
        </a>
        <button class="btn" @click="load"><AppIcon name="refresh" :size="14" /> 刷新</button>
      </div>
    </header>

    <section v-if="registry" class="principle panel">
      <div class="principle-copy">
        <div class="principle-kicker">Architecture Principle</div>
        <h2>{{ registry.principle.title }}</h2>
        <ol class="rule-list">
          <li v-for="(rule, index) in registry.principle.rules" :key="rule">
            <span class="rule-index mono">0{{ index + 1 }}</span>
            <span>{{ rule }}</span>
          </li>
        </ol>
      </div>
      <div class="principle-flow">
        <div class="flow-node engine-node">
          <span class="flow-label">ENGINE</span>
          <strong>{{ registry.stats.engineCount }} 个引擎</strong>
          <small>截图 · 视觉 · 输入 · SIFT · 对战 · 调度</small>
        </div>
        <div class="flow-arrow">
          <span class="flow-dot" />
          <span class="flow-line" />
          <span class="flow-caption mono">subset</span>
        </div>
        <div class="flow-node feature-node">
          <span class="flow-label">FEATURE</span>
          <strong>{{ registry.stats.featureCount }} 个功能</strong>
          <small>每个功能只取所需组元</small>
        </div>
        <p class="flow-note">{{ registry.principle.reference.pattern }}</p>
      </div>
    </section>

    <div v-if="stats" class="stat-grid coverage-stats">
      <div class="stat-cell">
        <div class="stat-label">引擎组元</div>
        <div class="stat-value">{{ stats.componentCount }}<small>components</small></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">主要功能</div>
        <div class="stat-value">{{ stats.featureCount }}<small>features</small></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">组元装配</div>
        <div class="stat-value">{{ stats.bindingCount }}<small>bindings</small></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">被复用组元</div>
        <div class="stat-value">{{ stats.reusableComponents }}<small>/ {{ stats.componentCount }}</small></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">最高复用</div>
        <div class="stat-value">{{ stats.maxReuse }}<small>个功能</small></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">已完善组元</div>
        <div class="stat-value">{{ stats.readyComponents }}<small>/ {{ stats.componentCount }}</small></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">待完善组元</div>
        <div class="stat-value">{{ stats.partialComponents }}<small>/ {{ stats.componentCount }}</small></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">能力缺口</div>
        <div class="stat-value">{{ stats.gapCount }}<small>gaps</small></div>
      </div>
    </div>

    <div class="section-title" style="margin-top: 26px">
      <h2>引擎可执行包</h2>
      <span class="hint">组件按功能组合为 headless 引擎；Windows 下由 scripts/build-engines.ps1 生成 .exe</span>
    </div>
    <div v-if="registry" class="group-grid">
      <article v-for="group in registry.groups" :key="group.id" class="group-card" :class="{ core: group.id === 'core' }">
        <div class="group-head">
          <span class="group-icon"><AppIcon :name="groupIcon(group.id)" :size="16" /></span>
          <div>
            <h3>{{ group.name }}</h3>
            <div class="group-exe mono">{{ group.exe }}.exe</div>
          </div>
          <span class="chip mono">{{ group.readyCount }}/{{ group.componentCount }}</span>
        </div>
        <p>{{ group.summary }}</p>
        <div class="group-actions">
          <span v-for="action in group.actions" :key="action" class="action-chip mono">
            {{ group.id === 'core' ? 'group.action' : action }}
          </span>
        </div>
      </article>
    </div>
    <div v-if="registry" class="build-note">
      <AppIcon name="cpu" :size="13" />
      <span>
        统一入口：<span class="mono">{{ 'RocogiEngine.exe --action sense.capture' }}</span> 或
        <span class="mono">{{ '--action battle.analyze' }}</span>；JSON 走 stdout。Linux 产物同名无扩展名，已在本机完成构建与冒烟测试。
      </span>
    </div>

    <div class="section-title" style="margin-top: 26px">
      <h2>复用矩阵</h2>
      <span class="hint">行是功能，列是引擎；数字表示该功能装配了该引擎的几个组元</span>
    </div>
    <div v-if="registry" class="matrix-wrap panel">
      <table class="matrix">
        <thead>
          <tr>
            <th class="corner">功能 / 引擎</th>
            <th v-for="engine in registry.engines" :key="engine.id">
              <span class="matrix-engine" :style="{ color: engine.accent }">
                <AppIcon :name="engine.icon" :size="14" />
                {{ engine.name }}
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="feature in registry.features" :key="feature.id" :class="{ dim: selected && selected !== feature.id }">
            <th class="matrix-feature">
              <button class="feature-button" :class="{ active: selected === feature.id }" @click="toggleFeature(feature.id)">
                <AppIcon :name="feature.icon" :size="14" />
                {{ feature.name }}
                <span class="feature-total mono">{{ feature.componentCount }}</span>
              </button>
            </th>
            <td
              v-for="engine in registry.engines"
              :key="engine.id"
              :class="{ lit: cellCount(feature.id, engine.id) > 0, focus: selected === feature.id }"
              :title="cellTitle(feature.id, engine.id)"
              @click="toggleFeature(feature.id)"
            >
              <template v-if="cellCount(feature.id, engine.id)">
                <span class="cell-count mono">{{ cellCount(feature.id, engine.id) }}</span>
                <span class="cell-bars">
                  <i
                    v-for="index in cellCount(feature.id, engine.id)"
                    :key="index"
                    :style="{ background: engine.accent }"
                  />
                </span>
              </template>
              <span v-else class="cell-empty">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="section-title" style="margin-top: 26px">
      <div class="title-with-filter">
        <h2>功能装配</h2>
        <button v-if="selected" class="chip danger" @click="selected = ''">
          <AppIcon name="close" :size="11" /> 清除筛选
        </button>
      </div>
      <span class="hint">点击任意功能，查看它实际装配的组元；再次点击取消</span>
    </div>
    <div v-if="registry" class="feature-grid">
      <article
        v-for="feature in registry.features"
        :key="feature.id"
        class="feature-card"
        :class="{ selected: selected === feature.id, dim: selected && selected !== feature.id }"
        :style="{ '--accent': feature.accent }"
        @click="toggleFeature(feature.id)"
      >
        <div class="feature-head">
          <span class="feature-icon" :style="{ color: feature.accent, background: `${feature.accent}14` }">
            <AppIcon :name="feature.icon" :size="16" />
          </span>
          <div>
            <h3>{{ feature.name }}</h3>
            <div class="feature-metrics mono">
              {{ feature.componentCount }} 组元 · {{ feature.engineCount }} 引擎
            </div>
          </div>
          <span v-if="selected === feature.id" class="chip primary">筛选中</span>
        </div>
        <p class="feature-summary">{{ feature.summary }}</p>
        <div class="feature-engines">
          <span
            v-for="engineId in feature.engines"
            :key="engineId"
            class="engine-pill"
            :style="{ color: engineMap.get(engineId)?.accent, borderColor: `${engineMap.get(engineId)?.accent}33` }"
          >
            {{ engineMap.get(engineId)?.name }}
            <b class="mono">{{ cellCount(feature.id, engineId) }}</b>
          </span>
        </div>
        <RouterLink class="feature-link" :to="feature.route" @click.stop>
          打开功能 <AppIcon name="external" :size="12" />
        </RouterLink>
      </article>
    </div>

    <div class="section-title" style="margin-top: 26px">
      <h2>引擎组元</h2>
      <span class="hint">每个组元列出复用它的功能；数字越大，说明越是跨功能的公共能力</span>
    </div>
    <div v-if="registry" class="engine-stack">
      <section
        v-for="engine in registry.engines"
        :key="engine.id"
        class="engine-block panel"
        :style="{ '--accent': engine.accent }"
      >
        <header class="engine-head">
          <span class="engine-icon" :style="{ color: engine.accent, background: `${engine.accent}14` }">
            <AppIcon :name="engine.icon" :size="17" />
          </span>
          <div class="engine-meta">
            <div class="engine-name-row">
              <h3>{{ engine.name }}</h3>
              <span class="chip">{{ engine.layer }}</span>
              <span class="chip mono">{{ engine.components.length }} 组元</span>
            </div>
            <p>{{ engine.summary }}</p>
            <div class="engine-source mono">{{ engine.source }}</div>
          </div>
          <div class="engine-reuse">
            <span class="mono">{{ engine.components.reduce((sum, item) => sum + item.reuse, 0) }}</span>
            <small>组装配</small>
          </div>
        </header>
        <div class="component-list">
          <div
            v-for="component in engine.components"
            :key="component.id"
            class="component-row"
            :class="{ dim: !isComponentOn(component), on: selectedFeature && isComponentOn(component) }"
          >
            <div class="component-main">
              <div class="component-title">
                <strong>{{ component.name }}</strong>
                <span
                  class="status-badge"
                  :class="component.status"
                  :title="component.statusNote || statusLabel(component.status)"
                >
                  {{ statusLabel(component.status) }}
                </span>
                <span class="reuse-badge" :class="{ hot: component.reuse >= 5 }" :title="`被 ${component.reuse} 个功能复用`">
                  ×{{ component.reuse }}
                </span>
              </div>
              <p>{{ component.detail }}</p>
              <div class="component-code mono">{{ component.code }}</div>
            </div>
            <div class="component-features">
              <button
                v-for="featureId in component.features"
                :key="featureId"
                class="feature-chip"
                :class="{ active: selected === featureId }"
                :title="featureMap.get(featureId)?.summary"
                @click="toggleFeature(featureId)"
              >
                {{ featureName(featureId) }}
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>

    <div class="section-title" style="margin-top: 26px">
      <h2>未完善组件</h2>
      <span class="hint">这些能力还没有完整落地，或只在特定环境可用</span>
    </div>
    <div v-if="registry?.gaps?.length" class="gap-grid">
      <article v-for="gap in registry.gaps" :key="gap.id" class="gap-card">
        <div class="gap-head">
          <span class="status-badge" :class="gap.status">{{ statusLabel(gap.status) }}</span>
          <strong>{{ gap.name }}</strong>
          <span class="mono gap-id">{{ gap.id }}</span>
        </div>
        <p>{{ gap.note }}</p>
        <span class="gap-engine">{{ engineName(gap.engine) }}</span>
      </article>
    </div>

    <div v-if="registry" class="graph-note">
      <AppIcon name="spark" :size="14" />
      <span>
        组件注册表由 <span class="mono">backend/app/components.py</span> 单一维护，功能只声明组元 ID；
        新增功能只需追加一份子集，新增引擎能力则自动被所有声明它的功能复用。
      </span>
    </div>
  </div>
</template>

<style scoped>
.principle {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
  gap: 26px;
  padding: 24px 26px;
  margin-bottom: 18px;
  overflow: hidden;
  position: relative;
}

.principle::before {
  content: '';
  position: absolute;
  inset: -40% 55% auto auto;
  width: 340px;
  height: 340px;
  background: radial-gradient(circle, rgba(56, 189, 248, 0.18), transparent 65%);
  pointer-events: none;
}

.principle-kicker {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--faint);
  margin-bottom: 8px;
}

.principle h2 {
  font-size: 20px;
  letter-spacing: -0.03em;
}

.rule-list {
  list-style: none;
  margin: 14px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.rule-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.55;
}

.rule-index {
  font-size: 10px;
  color: var(--primary);
  background: var(--primary-dim);
  border: 1px solid rgba(14, 165, 233, 0.2);
  border-radius: 6px;
  padding: 2px 6px;
  flex: none;
}

.principle-flow {
  position: relative;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 10px;
  padding: 16px;
  border: 1px dashed rgba(14, 165, 233, 0.22);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(240, 250, 255, 0.7), rgba(255, 255, 255, 0.5));
}

.flow-node {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border-radius: 11px;
  background: #fff;
  border: 1px solid var(--border-soft);
  box-shadow: 0 8px 20px rgba(42, 108, 140, 0.06);
}

.feature-node {
  border-color: rgba(236, 72, 153, 0.24);
  box-shadow: 0 8px 20px rgba(236, 72, 153, 0.08);
}

.flow-label {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 0.16em;
  color: var(--faint);
}

.flow-node strong {
  font-size: 14px;
}

.flow-node small {
  font-size: 9.5px;
  line-height: 1.5;
  color: var(--muted);
}

.flow-arrow {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  min-width: 46px;
}

.flow-line {
  width: 38px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(14, 165, 233, 0.6), transparent);
}

.flow-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--primary);
  box-shadow: 0 0 8px rgba(14, 165, 233, 0.6);
}

.flow-caption {
  font-size: 8px;
  color: var(--faint);
  letter-spacing: 0.12em;
}

.flow-note {
  grid-column: 1 / -1;
  margin-top: 4px;
  font-size: 9.5px;
  line-height: 1.6;
  color: var(--faint);
}

.coverage-stats {
  margin-top: 4px;
}

.group-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 11px;
}

.group-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 15px;
  border: 1px solid var(--border-soft);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 6px 18px rgba(42, 108, 140, 0.05);
}

.group-card.core {
  border-color: rgba(124, 58, 237, 0.24);
  background: linear-gradient(180deg, rgba(250, 247, 255, 0.95), rgba(255, 255, 255, 0.9));
}

.group-head {
  display: flex;
  align-items: center;
  gap: 9px;
}

.group-icon {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  color: var(--primary);
  background: var(--primary-dim);
  flex: none;
}

.group-card.core .group-icon {
  color: var(--violet);
  background: rgba(139, 92, 246, 0.1);
}

.group-head h3 {
  font-size: 12.5px;
}

.group-exe {
  margin-top: 1px;
  font-size: 8.5px;
  color: var(--faint);
}

.group-head .chip {
  margin-left: auto;
}

.group-card p {
  font-size: 9.5px;
  line-height: 1.55;
  color: var(--muted);
  min-height: 30px;
}

.group-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.action-chip {
  padding: 2px 6px;
  border-radius: 5px;
  border: 1px solid var(--border-soft);
  background: rgba(246, 252, 255, 0.9);
  font-size: 8px;
  color: var(--text-soft);
}

.build-note {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  margin-top: 10px;
  padding: 9px 11px;
  border-radius: 8px;
  border: 1px dashed var(--border);
  background: rgba(246, 252, 255, 0.7);
  font-size: 9.5px;
  line-height: 1.6;
  color: var(--muted);
}

.build-note svg {
  color: var(--primary);
  flex: none;
  margin-top: 1px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  height: 17px;
  padding: 0 6px;
  border-radius: 999px;
  border: 1px solid var(--border-soft);
  background: #fff;
  font-size: 8px;
  white-space: nowrap;
}

.status-badge.ready {
  color: #047857;
  border-color: rgba(5, 150, 105, 0.24);
  background: rgba(5, 150, 105, 0.08);
}

.status-badge.partial {
  color: #b45309;
  border-color: rgba(217, 119, 6, 0.24);
  background: rgba(251, 191, 36, 0.12);
}

.status-badge.missing {
  color: #be123c;
  border-color: rgba(225, 29, 72, 0.24);
  background: rgba(225, 29, 72, 0.08);
}

.gap-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
  gap: 10px;
}

.gap-card {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 13px 14px;
  border: 1px solid rgba(225, 29, 72, 0.16);
  border-radius: 11px;
  background: linear-gradient(180deg, rgba(255, 250, 251, 0.9), rgba(255, 255, 255, 0.8));
}

.gap-head {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
}

.gap-head strong {
  font-size: 11.5px;
}

.gap-id {
  margin-left: auto;
  font-size: 8px;
  color: var(--faint);
}

.gap-card p {
  font-size: 9.5px;
  line-height: 1.6;
  color: var(--muted);
}

.gap-engine {
  align-self: flex-start;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--panel-2);
  border: 1px solid var(--border-soft);
  font-size: 8px;
  color: var(--faint);
}

.matrix-wrap {
  overflow: auto;
  padding: 6px 6px 10px;
}

.matrix {
  width: 100%;
  min-width: 760px;
  border-collapse: separate;
  border-spacing: 0;
}

.matrix th,
.matrix td {
  padding: 9px 10px;
  border-bottom: 1px solid rgba(214, 234, 245, 0.6);
  text-align: center;
}

.matrix thead th {
  position: sticky;
  top: 0;
  background: rgba(250, 253, 255, 0.96);
  backdrop-filter: blur(10px);
  font-size: 10px;
  font-weight: 600;
  color: var(--muted);
  letter-spacing: 0.04em;
  border-bottom: 1px solid var(--border-soft);
  z-index: 2;
}

.matrix thead th.corner {
  text-align: left;
  color: var(--faint);
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.matrix-engine {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}

.matrix-feature {
  text-align: left;
  position: sticky;
  left: 0;
  background: rgba(252, 254, 255, 0.98);
  z-index: 1;
  min-width: 150px;
}

.feature-button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 8px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--text-soft);
  font-size: 12px;
  font-weight: 550;
}

.feature-button:hover,
.feature-button.active {
  background: rgba(14, 165, 233, 0.08);
  border-color: rgba(14, 165, 233, 0.18);
  color: var(--text);
}

.feature-total {
  margin-left: auto;
  font-size: 9.5px;
  color: var(--faint);
}

.matrix tbody tr.dim {
  opacity: 0.35;
}

.matrix tbody td {
  cursor: pointer;
  transition: background 0.15s ease;
}

.matrix tbody td.lit .cell-count {
  font-size: 13px;
  color: var(--text);
}

.matrix tbody td.focus {
  background: rgba(240, 250, 255, 0.8);
}

.cell-count {
  display: block;
  font-size: 11px;
  color: var(--faint);
  line-height: 1.2;
}

.cell-bars {
  display: flex;
  gap: 2px;
  justify-content: center;
  margin-top: 5px;
}

.cell-bars i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  opacity: 0.9;
}

.cell-empty {
  color: #c3d7e3;
  font-size: 11px;
}

.title-with-filter {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-with-filter .chip {
  cursor: pointer;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(272px, 1fr));
  gap: 13px;
}

.feature-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 9px;
  padding: 16px;
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 8px 22px rgba(42, 108, 140, 0.05);
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease, opacity 0.16s ease;
}

.feature-card:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--accent) 38%, transparent);
  box-shadow: 0 14px 30px rgba(42, 108, 140, 0.1);
}

.feature-card.selected {
  border-color: color-mix(in srgb, var(--accent) 55%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--accent) 20%, transparent),
    0 14px 30px rgba(42, 108, 140, 0.12);
  background: #fff;
}

.feature-card.dim {
  opacity: 0.45;
}

.feature-card::after {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 3px;
  border-radius: 14px 0 0 14px;
  background: var(--accent);
  opacity: 0.55;
}

.feature-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.feature-icon {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  flex: none;
}

.feature-head h3 {
  font-size: 14px;
  line-height: 1.3;
}

.feature-metrics {
  font-size: 9px;
  color: var(--faint);
  margin-top: 2px;
  letter-spacing: 0.04em;
}

.feature-head .chip {
  margin-left: auto;
}

.feature-summary {
  font-size: 10.5px;
  line-height: 1.6;
  color: var(--muted);
  min-height: 50px;
}

.feature-engines {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.engine-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  border: 1px solid;
  border-radius: 999px;
  font-size: 9.5px;
  background: #fff;
}

.engine-pill b {
  font-size: 9px;
  opacity: 0.8;
}

.feature-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: auto;
  font-size: 10.5px;
  color: var(--primary);
  padding-top: 4px;
}

.feature-link:hover {
  text-decoration: underline;
}

.engine-stack {
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.engine-block {
  overflow: hidden;
  border-left: 3px solid color-mix(in srgb, var(--accent) 55%, transparent);
}

.engine-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 15px 18px;
  border-bottom: 1px solid var(--border-soft);
  background: linear-gradient(90deg, color-mix(in srgb, var(--accent) 5%, transparent), transparent 65%);
}

.engine-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  flex: none;
}

.engine-meta {
  min-width: 0;
  flex: 1;
}

.engine-name-row {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
}

.engine-name-row h3 {
  font-size: 14px;
}

.engine-meta p {
  margin-top: 4px;
  font-size: 10.5px;
  color: var(--muted);
  line-height: 1.55;
}

.engine-source {
  margin-top: 4px;
  font-size: 9px;
  color: var(--faint);
}

.engine-reuse {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
}

.engine-reuse span {
  font-size: 20px;
  letter-spacing: -0.04em;
  color: var(--accent);
}

.engine-reuse small {
  font-size: 8.5px;
  color: var(--faint);
  letter-spacing: 0.08em;
}

.component-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: 0;
}

.component-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 13px 18px;
  border-bottom: 1px solid rgba(214, 234, 245, 0.55);
  border-right: 1px solid rgba(214, 234, 245, 0.4);
  transition: opacity 0.16s ease, background 0.16s ease;
}

.component-row:nth-child(2n) {
  border-right: none;
}

.component-row.dim {
  opacity: 0.32;
}

.component-row.on {
  background: color-mix(in srgb, var(--accent) 4%, transparent);
}

.component-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.component-title strong {
  font-size: 12px;
  font-weight: 600;
}

.reuse-badge {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 6px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: #fff;
  font-family: var(--mono);
  font-size: 9px;
  color: var(--muted);
}

.reuse-badge.hot {
  color: var(--primary);
  border-color: rgba(14, 165, 233, 0.3);
  background: rgba(14, 165, 233, 0.08);
}

.component-row p {
  font-size: 10px;
  line-height: 1.55;
  color: var(--muted);
}

.component-code {
  font-size: 8.5px;
  color: var(--faint);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.component-features {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: auto;
}

.feature-chip {
  display: inline-flex;
  align-items: center;
  height: 19px;
  padding: 0 7px;
  border-radius: 999px;
  border: 1px solid var(--border-soft);
  background: rgba(246, 252, 255, 0.9);
  color: var(--muted);
  font-size: 9px;
  transition: color 0.14s ease, border-color 0.14s ease, background 0.14s ease;
}

.feature-chip:hover,
.feature-chip.active {
  color: var(--primary);
  border-color: rgba(14, 165, 233, 0.32);
  background: rgba(14, 165, 233, 0.08);
}

.graph-note {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 18px;
  padding: 10px 13px;
  border-radius: 9px;
  border: 1px solid rgba(14, 165, 233, 0.16);
  background: rgba(14, 165, 233, 0.05);
  font-size: 10.5px;
  line-height: 1.6;
  color: var(--muted);
}

.graph-note svg {
  color: var(--primary);
  flex: none;
}

.graph-note .mono {
  color: var(--text-soft);
}

@media (max-width: 1080px) {
  .principle {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .component-list {
    grid-template-columns: 1fr;
  }

  .component-row {
    border-right: none;
  }
}
</style>
