<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../lib/api'
import { notify } from '../lib/toast'

interface ElementInfo {
  name: string
  count: number
  color: string
}

interface Meta {
  total: number
  skillTotal: number
  evolutionTotal: number
  elements: ElementInfo[]
  stages: string[]
  categories: { name: string; count: number; color: string }[]
  maxTotal: number
  minTotal: number
  avgTotal: number
  source: string
}

interface StatCell {
  key: string
  label: string
  value: number
  color: string
}

interface Ability {
  name: string
  description: string
}

interface Pet {
  id: number
  spiritNo: string
  name: string
  element: string
  elementColor: string
  stage: string
  ability: Ability
  total: number
  stats: StatCell[]
  statPreview?: Record<string, number>
  // 形态与配色是两条轴：form 是模型形态，colorType 是九类配色之一。
  variant?: {
    colorType: string
    colorLabel: string
    colorEffect: string
    formLabel: string
    formRaw: string
    season: number | null
    isShiny: boolean
    isPolluted: boolean
  }
}

interface Skill {
  id: number
  name: string
  element: string
  elementColor: string
  category: string
  categoryColor: string
  power: number
  energy: number
  description: string
  learnable: number
}

interface Evolution {
  from: string
  to: string
  level: number | null
  condition: string
  chainText: string
}

interface Detail {
  pokemon: Pet
  skills: Skill[]
  evolution: Evolution[]
  related: Pet[]
}

const meta = ref<Meta | null>(null)
const tab = ref<'pets' | 'skills'>('pets')
const query = ref('')
const element = ref('')
const stage = ref('')
const sort = ref('id')
const order = ref<'asc' | 'desc'>('asc')
const category = ref('')

const pets = ref<Pet[]>([])
const petTotal = ref(0)
const skills = ref<Skill[]>([])
const skillTotal = ref(0)
const loading = ref(false)
const moreLoading = ref(false)
const pageError = ref('')

const detail = ref<Detail | null>(null)
const detailLoading = ref(false)
const searchInput = ref<HTMLInputElement | null>(null)
let detailSeq = 0

const sortOptions = [
  { value: 'id', label: '图鉴编号' },
  { value: 'total', label: '种族值' },
  { value: 'hp', label: '生命' },
  { value: 'speed', label: '速度' },
  { value: 'atk', label: '物攻' },
  { value: 'spatk', label: '魔攻' },
  { value: 'def', label: '物防' },
  { value: 'spdef', label: '魔防' },
]

const activeFilters = computed(() => Boolean(query.value || element.value || stage.value || category.value))
const hasMorePets = computed(() => pets.value.length < petTotal.value)
const hasMoreSkills = computed(() => skills.value.length < skillTotal.value)

function elementStyle(name: string) {
  const info = meta.value?.elements.find((item) => item.name === name)
  const color = info?.color || '#A0A8B0'
  return { color, background: `${color}16`, borderColor: `${color}38` }
}

function petQuery(offset: number) {
  const params = new URLSearchParams()
  params.set('limit', '24')
  params.set('offset', String(offset))
  params.set('sort', sort.value)
  params.set('order', order.value)
  if (query.value.trim()) params.set('q', query.value.trim())
  if (element.value) params.set('element', element.value)
  if (stage.value) params.set('stage', stage.value)
  return params.toString()
}

function skillQuery(offset: number) {
  const params = new URLSearchParams()
  params.set('limit', '40')
  params.set('offset', String(offset))
  if (query.value.trim()) params.set('q', query.value.trim())
  if (element.value) params.set('element', element.value)
  if (category.value) params.set('category', category.value)
  return params.toString()
}

let petSeq = 0
let skillSeq = 0
let debounceTimer: ReturnType<typeof setTimeout> | null = null

async function loadPets(reset = true) {
  const seq = ++petSeq
  if (reset) {
    loading.value = true
    pageError.value = ''
  } else {
    moreLoading.value = true
  }
  try {
    const offset = reset ? 0 : pets.value.length
    const data = await api<{ total: number; items: Pet[]; limit: number; offset: number }>(
      `/api/dex/pokemon?${petQuery(offset)}`,
    )
    if (seq !== petSeq) return
    petTotal.value = data.total
    pets.value = reset ? data.items : [...pets.value, ...data.items]
  } catch (error) {
    if (seq === petSeq) pageError.value = `读取图鉴失败：${error}`
  } finally {
    if (seq === petSeq) {
      loading.value = false
      moreLoading.value = false
    }
  }
}

async function loadSkills(reset = true) {
  const seq = ++skillSeq
  if (reset) {
    loading.value = true
    pageError.value = ''
  } else {
    moreLoading.value = true
  }
  try {
    const offset = reset ? 0 : skills.value.length
    const data = await api<{ total: number; items: Skill[]; limit: number; offset: number }>(
      `/api/dex/skills?${skillQuery(offset)}`,
    )
    if (seq !== skillSeq) return
    skillTotal.value = data.total
    skills.value = reset ? data.items : [...skills.value, ...data.items]
  } catch (error) {
    if (seq === skillSeq) pageError.value = `读取技能库失败：${error}`
  } finally {
    if (seq === skillSeq) {
      loading.value = false
      moreLoading.value = false
    }
  }
}

function refreshCurrent() {
  if (tab.value === 'pets') loadPets(true)
  else loadSkills(true)
}

function scheduleRefresh() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(refreshCurrent, 260)
}

function toggleElement(name: string) {
  element.value = element.value === name ? '' : name
}

function toggleStage(name: string) {
  stage.value = stage.value === name ? '' : name
}

function clearFilters() {
  query.value = ''
  element.value = ''
  stage.value = ''
  category.value = ''
}

function switchTab(next: 'pets' | 'skills') {
  if (next === tab.value) return
  query.value = ''
  if (next === 'skills') stage.value = ''
  else category.value = ''
  tab.value = next
}

function loadMore() {
  if (tab.value === 'pets') loadPets(false)
  else loadSkills(false)
}

async function openPet(pet: Pet) {
  const seq = ++detailSeq
  detailLoading.value = true
  detail.value = null
  try {
    const data = await api<Detail>(`/api/dex/pokemon/${encodeURIComponent(pet.name)}`)
    if (seq === detailSeq) detail.value = data
  } catch (error: any) {
    if (seq === detailSeq) notify(`读取 ${pet.name} 详情失败：${error?.payload?.detail || error}`, 'error')
  } finally {
    if (seq === detailSeq) detailLoading.value = false
  }
}

function closeDetail() {
  detailSeq++
  detail.value = null
  detailLoading.value = false
}

function statBarWidth(value: number, max = 200) {
  return `${Math.min(100, Math.round((value / max) * 100))}%`
}

function evolutionText(row: Evolution) {
  return row.chainText || `${row.from} → ${row.to}`
}

function onKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement | null
  if (event.key === 'Escape' && detail.value) closeDetail()
  if (event.key === '/' && target?.tagName !== 'INPUT' && target?.tagName !== 'TEXTAREA') {
    event.preventDefault()
    searchInput.value?.focus()
  }
}

watch([query, element, stage, sort, order, category], scheduleRefresh)
watch(tab, () => {
  if (tab.value === 'pets' && !pets.value.length) loadPets(true)
  if (tab.value === 'skills' && !skills.value.length) loadSkills(true)
})

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  try {
    meta.value = await api<Meta>('/api/dex/meta')
  } catch (error) {
    notify(`读取图鉴元数据失败：${error}`, 'error')
  }
  loadPets(true)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  if (debounceTimer) clearTimeout(debounceTimer)
})
</script>

<template>
  <div class="page dex-page">
    <header class="page-head">
      <div>
        <div class="eyebrow">ROCO ARCHIVE · {{ meta?.total || 0 }} ENTRIES</div>
        <h1>精灵图鉴</h1>
        <p class="page-sub">
          按名称、属性和形态秒查精灵，点开即可看到种族值、特性、技能表与进化链；技能库同样支持属性与类别筛选。
        </p>
      </div>
      <div class="page-actions">
        <span v-if="meta" class="chip">{{ meta.total }} 精灵</span>
        <span v-if="meta" class="chip">{{ meta.skillTotal }} 技能</span>
        <span v-if="meta" class="chip">{{ meta.evolutionTotal }} 进化链</span>
        <a class="chip primary" href="https://github.com/eachyczhang/-RocoTools" target="_blank" rel="noreferrer">
          <AppIcon name="external" :size="12" /> RocoTools 字段参考
        </a>
      </div>
    </header>

    <section class="dex-toolbar panel">
      <div class="toolbar-top">
        <label class="dex-search">
          <AppIcon name="search" :size="15" />
          <input
            ref="searchInput"
            v-model="query"
            type="search"
            :placeholder="tab === 'pets' ? '搜索精灵名或特性，例如 迪莫 / 氧循环' : '搜索技能名或描述，例如 地震 / 回复'"
            aria-label="搜索图鉴"
          />
          <kbd class="mono">/</kbd>
          <button v-if="query" class="search-clear" aria-label="清空搜索" @click="query = ''">
            <AppIcon name="close" :size="12" />
          </button>
        </label>

        <div class="tab-switch">
          <button :class="{ active: tab === 'pets' }" @click="switchTab('pets')">
            精灵 <span class="mono">{{ meta?.total || 0 }}</span>
          </button>
          <button :class="{ active: tab === 'skills' }" @click="switchTab('skills')">
            技能 <span class="mono">{{ meta?.skillTotal || 0 }}</span>
          </button>
        </div>

        <div v-if="tab === 'pets'" class="sort-box">
          <select v-model="sort" aria-label="排序字段">
            <option v-for="item in sortOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
          <button class="order-btn mono" :title="order === 'asc' ? '升序' : '降序'" @click="order = order === 'asc' ? 'desc' : 'asc'">
            {{ order === 'asc' ? '↑' : '↓' }}
          </button>
        </div>
      </div>

      <div class="filter-row">
        <span class="filter-label">属性</span>
        <div class="element-chips">
          <button class="element-chip" :class="{ active: !element }" @click="element = ''">全部</button>
          <button
            v-for="item in meta?.elements || []"
            :key="item.name"
            class="element-chip"
            :class="{ active: element === item.name }"
            :style="{
              '--elem': item.color,
              color: element === item.name ? item.color : undefined,
              borderColor: element === item.name ? `${item.color}55` : undefined,
              background: element === item.name ? `${item.color}14` : undefined,
            }"
            @click="toggleElement(item.name)"
          >
            <i :style="{ background: item.color }" />
            {{ item.name }}
            <span class="mono">{{ item.count }}</span>
          </button>
        </div>
      </div>

      <div v-if="tab === 'pets'" class="filter-row">
        <span class="filter-label">形态</span>
        <div class="stage-chips">
          <button class="stage-chip" :class="{ active: !stage }" @click="stage = ''">全部</button>
          <button
            v-for="item in meta?.stages || []"
            :key="item"
            class="stage-chip"
            :class="{ active: stage === item }"
            @click="toggleStage(item)"
          >
            {{ item }}
          </button>
        </div>
        <span v-if="activeFilters" class="filter-clear" @click="clearFilters">清除筛选</span>
      </div>

      <div v-else class="filter-row">
        <span class="filter-label">类别</span>
        <div class="stage-chips">
          <button class="stage-chip" :class="{ active: !category }" @click="category = ''">全部</button>
          <button
            v-for="item in meta?.categories || []"
            :key="item.name"
            class="stage-chip"
            :class="{ active: category === item.name }"
            :style="category === item.name ? { color: item.color, borderColor: `${item.color}55`, background: `${item.color}12` } : {}"
            @click="category = category === item.name ? '' : item.name"
          >
            {{ item.name }}
            <span class="mono">{{ item.count }}</span>
          </button>
        </div>
        <span v-if="activeFilters" class="filter-clear" @click="clearFilters">清除筛选</span>
      </div>
    </section>

    <div class="result-line">
      <span v-if="tab === 'pets'">
        共 <b class="mono">{{ petTotal }}</b> 只精灵
        <template v-if="element"> · {{ element }}系</template>
        <template v-if="stage"> · {{ stage }}</template>
      </span>
      <span v-else>
        共 <b class="mono">{{ skillTotal }}</b> 个技能
        <template v-if="element"> · {{ element }}系</template>
        <template v-if="category"> · {{ category }}</template>
      </span>
      <span class="result-source mono">{{ meta?.source }}</span>
    </div>

    <div v-if="pageError" class="dex-error">{{ pageError }}</div>

    <div v-if="tab === 'pets'" class="dex-grid">
      <button
        v-for="pet in pets"
        :key="pet.id"
        class="pet-card"
        :style="{ '--elem': pet.elementColor }"
        @click="openPet(pet)"
      >
        <div class="pet-card-top">
          <span class="pet-no mono">{{ pet.spiritNo }}</span>
          <span class="pet-badges">
            <span v-if="pet.stage" class="pet-stage">{{ pet.stage }}</span>
            <span class="pet-total mono">{{ pet.total }}</span>
          </span>
        </div>
        <div class="pet-orb">
          <span>{{ pet.element }}</span>
        </div>
        <div class="pet-name-row">
          <strong :title="pet.name">{{ pet.name }}</strong>
        </div>
        <div class="pet-ability" :title="pet.ability.description">
          <b v-if="pet.ability.name">{{ pet.ability.name }}</b>
          <span v-else>暂无特性</span>
        </div>
        <div class="pet-bars">
          <i
            v-for="stat in pet.stats"
            :key="stat.key"
            :title="`${stat.label} ${stat.value}`"
            :style="{ width: statBarWidth(stat.value), background: stat.color }"
          />
        </div>
      </button>
      <div v-if="!loading && !pets.length" class="empty-state dex-empty">
        <AppIcon name="search" :size="26" />
        <div>没有匹配的精灵</div>
        <button class="btn btn-sm" @click="clearFilters">清除筛选</button>
      </div>
    </div>

    <div v-else class="skill-list">
      <article v-for="skill in skills" :key="skill.id" class="skill-row panel">
        <div class="skill-main">
          <div class="skill-title">
            <strong>{{ skill.name }}</strong>
            <span class="skill-tag" :style="elementStyle(skill.element)">{{ skill.element }}</span>
            <span class="skill-tag" :style="{ color: skill.categoryColor, background: `${skill.categoryColor}12`, borderColor: `${skill.categoryColor}33` }">
              {{ skill.category }}
            </span>
          </div>
          <p>{{ skill.description || '暂无技能描述' }}</p>
        </div>
        <div class="skill-metrics">
          <div>
            <span class="mono">{{ skill.power || '—' }}</span>
            <small>威力</small>
          </div>
          <div>
            <span class="mono">{{ skill.energy }}</span>
            <small>能量</small>
          </div>
          <div>
            <span class="mono">{{ skill.learnable }}</span>
            <small>可学</small>
          </div>
        </div>
      </article>
      <div v-if="!loading && !skills.length" class="empty-state dex-empty">
        <AppIcon name="search" :size="26" />
        <div>没有匹配的技能</div>
        <button class="btn btn-sm" @click="clearFilters">清除筛选</button>
      </div>
    </div>

    <div v-if="(tab === 'pets' ? hasMorePets : hasMoreSkills)" class="load-more">
      <button class="btn" :disabled="moreLoading" @click="loadMore">
        {{ moreLoading ? '加载中...' : `加载更多（${tab === 'pets' ? pets.length : skills.length} / ${tab === 'pets' ? petTotal : skillTotal}）` }}
      </button>
    </div>

    <div v-if="tab === 'pets' && meta" class="dex-footer-note">
      <AppIcon name="spark" :size="14" />
      <span>
        种族值区间 {{ meta.minTotal }}–{{ meta.maxTotal }}，平均 {{ meta.avgTotal }}；数据来自本地 NRC_AI 图鉴库，
        字段结构参考 RocoTools（属性、形态、特性、六维、技能与进化链）。
      </span>
    </div>
  </div>

  <Teleport to="body">
    <Transition name="fade">
      <div v-if="detail || detailLoading" class="dex-drawer-mask" @click.self="closeDetail">
        <aside class="dex-drawer" :style="{ '--elem': detail?.pokemon.elementColor || '#38bdf8' }">
          <header class="drawer-head">
            <div class="drawer-head-top">
              <span class="mono drawer-no">{{ detail?.pokemon.spiritNo || '...' }}</span>
              <div class="drawer-head-actions">
                <RouterLink
                  v-if="detail"
                  class="btn btn-sm"
                  :to="{ path: '/pet', query: { name: detail.pokemon.name } }"
                >
                  <AppIcon name="spark" :size="12" /> 设为桌宠
                </RouterLink>
                <button class="btn btn-icon btn-sm" aria-label="关闭详情" @click="closeDetail">
                  <AppIcon name="close" :size="14" />
                </button>
              </div>
            </div>
            <div v-if="detail" class="drawer-title-row">
              <div class="drawer-orb">{{ detail.pokemon.element }}</div>
              <div>
                <h2>{{ detail.pokemon.name }}</h2>
                <div class="drawer-sub">
                  <span class="skill-tag" :style="elementStyle(detail.pokemon.element)">{{ detail.pokemon.element }}系</span>
                  <span v-if="detail.pokemon.stage" class="chip">{{ detail.pokemon.stage }}</span>
                  <span class="chip mono">种族值 {{ detail.pokemon.total }}</span>
                  <span
                    v-if="detail.pokemon.variant && detail.pokemon.variant.colorType !== 'normal'"
                    class="chip variant-chip"
                    :class="{ shiny: detail.pokemon.variant.isShiny, polluted: detail.pokemon.variant.isPolluted }"
                    :title="detail.pokemon.variant.colorEffect"
                  >{{ detail.pokemon.variant.colorLabel }}</span>
                  <span v-if="detail.pokemon.variant?.formLabel" class="chip">{{ detail.pokemon.variant.formLabel }}</span>
                  <span v-if="detail.pokemon.variant?.season" class="chip mono">S{{ detail.pokemon.variant.season }} 赛季</span>
                </div>
              </div>
            </div>
            <div v-else class="drawer-title-row skeleton-row">
              <div class="drawer-orb">?</div>
              <div>
                <h2>读取中...</h2>
              </div>
            </div>
          </header>

          <div v-if="detail" class="drawer-body">
            <section class="drawer-section">
              <div class="drawer-section-title">特性</div>
              <div class="ability-card">
                <b>{{ detail.pokemon.ability.name || '暂无特性' }}</b>
                <p>{{ detail.pokemon.ability.description || '这只精灵还没有特性描述。' }}</p>
              </div>
            </section>

            <section class="drawer-section">
              <div class="drawer-section-title">种族值</div>
              <div class="stat-list">
                <div v-for="stat in detail.pokemon.stats" :key="stat.key" class="stat-row">
                  <span class="stat-label">{{ stat.label }}</span>
                  <div class="stat-track">
                    <i :style="{ width: statBarWidth(stat.value), background: stat.color }" />
                  </div>
                  <span class="stat-value mono">{{ stat.value }}</span>
                </div>
              </div>
            </section>

            <section class="drawer-section">
              <div class="drawer-section-title">
                技能 <span class="mono">{{ detail.skills.length }}</span>
              </div>
              <div class="drawer-skills">
                <div v-for="skill in detail.skills" :key="skill.id" class="drawer-skill">
                  <div class="drawer-skill-head">
                    <strong>{{ skill.name }}</strong>
                    <span class="skill-tag" :style="elementStyle(skill.element)">{{ skill.element }}</span>
                    <span class="skill-tag" :style="{ color: skill.categoryColor, background: `${skill.categoryColor}12`, borderColor: `${skill.categoryColor}33` }">
                      {{ skill.category }}
                    </span>
                    <span class="mono drawer-skill-metric">威力 {{ skill.power || '—' }} · 能量 {{ skill.energy }}</span>
                  </div>
                  <p>{{ skill.description || '暂无描述' }}</p>
                </div>
              </div>
            </section>

            <section class="drawer-section">
              <div class="drawer-section-title">进化链</div>
              <div v-if="detail.evolution.length" class="evolution-list">
                <div v-for="(row, index) in detail.evolution" :key="index" class="evolution-row">
                  <span>{{ evolutionText(row) }}</span>
                  <span v-if="row.level" class="mono">Lv.{{ row.level }}</span>
                  <span v-if="row.condition" class="muted">{{ row.condition }}</span>
                </div>
              </div>
              <p v-else class="drawer-empty">暂无进化链数据，可能为单形态或特殊形态。</p>
            </section>

            <section v-if="detail.related.length" class="drawer-section">
              <div class="drawer-section-title">同系精灵</div>
              <div class="related-list">
                <button
                  v-for="item in detail.related"
                  :key="item.id"
                  class="related-item"
                  :style="{ '--elem': item.elementColor }"
                  @click="openPet(item)"
                >
                  <i />
                  {{ item.name }}
                  <span class="mono">{{ item.total }}</span>
                </button>
              </div>
            </section>
          </div>
          <div v-else class="drawer-loading">
            <span class="status-dot running" />
            正在读取图鉴详情...
          </div>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.dex-page {
  padding-bottom: 60px;
}

.dex-toolbar {
  position: sticky;
  top: 12px;
  z-index: 12;
  padding: 13px 14px;
  margin-bottom: 12px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(16px);
}

.toolbar-top {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.dex-search {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 280px;
  height: 38px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: #fff;
  box-shadow: inset 0 1px 2px rgba(42, 108, 140, 0.04);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.dex-search:focus-within {
  border-color: rgba(14, 165, 233, 0.45);
  box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1);
}

.dex-search svg {
  color: var(--primary);
  flex: none;
}

.dex-search input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-size: 12.5px;
  color: var(--text);
}

.dex-search input::placeholder {
  color: var(--faint);
}

.dex-search kbd {
  flex: none;
  padding: 1px 6px;
  border: 1px solid var(--border-soft);
  border-radius: 5px;
  background: var(--panel-2);
  color: var(--faint);
  font-size: 9px;
}

.search-clear {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 50%;
  background: var(--panel-3);
  color: var(--muted);
}

.search-clear:hover {
  background: #dcf0fa;
  color: var(--text);
}

.tab-switch {
  display: flex;
  padding: 3px;
  border: 1px solid var(--border-soft);
  border-radius: 10px;
  background: var(--panel-2);
}

.tab-switch button {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}

.tab-switch button.active {
  background: #fff;
  color: var(--text);
  box-shadow: 0 2px 8px rgba(42, 108, 140, 0.08);
}

.tab-switch .mono {
  font-size: 9px;
  color: var(--faint);
}

.sort-box {
  display: flex;
  align-items: center;
  gap: 5px;
}

.sort-box select {
  height: 32px;
  padding: 0 8px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #fff;
  color: var(--text-soft);
  font-size: 11.5px;
  outline: none;
}

.order-btn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #fff;
  color: var(--primary);
  font-size: 14px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 9px;
  min-width: 0;
}

.filter-label {
  flex: none;
  width: 28px;
  font-size: 10px;
  color: var(--faint);
  letter-spacing: 0.08em;
}

.element-chips,
.stage-chips {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
}

.element-chip,
.stage-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 25px;
  padding: 0 8px;
  border: 1px solid var(--border-soft);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  color: var(--muted);
  font-size: 10.5px;
  white-space: nowrap;
  transition: color 0.14s ease, border-color 0.14s ease, background 0.14s ease;
}

.element-chip i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.element-chip .mono {
  font-size: 8.5px;
  color: var(--faint);
}

.element-chip:hover,
.stage-chip:hover {
  border-color: #a8d4e8;
  color: var(--text);
}

.element-chip.active,
.stage-chip.active {
  border-color: rgba(14, 165, 233, 0.32);
  background: rgba(14, 165, 233, 0.08);
  color: var(--primary);
}

.element-chip.active .mono,
.stage-chip.active .mono {
  color: inherit;
  opacity: 0.7;
}

.filter-clear {
  margin-left: auto;
  font-size: 10px;
  color: var(--primary);
  cursor: pointer;
  white-space: nowrap;
}

.filter-clear:hover {
  text-decoration: underline;
}

.result-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 14px 2px 10px;
  font-size: 11px;
  color: var(--muted);
}

.result-line b {
  color: var(--text);
  font-weight: 600;
}

.result-source {
  font-size: 9px;
  color: var(--faint);
}

.dex-error {
  padding: 12px 14px;
  border: 1px solid rgba(225, 29, 72, 0.24);
  border-radius: 10px;
  background: rgba(255, 241, 245, 0.8);
  color: #be123c;
  font-size: 11.5px;
}

.dex-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 11px;
}

.pet-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 13px 13px;
  text-align: left;
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(250, 253, 255, 0.9)),
    radial-gradient(circle at 80% -10%, color-mix(in srgb, var(--elem) 18%, transparent), transparent 55%);
  box-shadow: 0 6px 18px rgba(42, 108, 140, 0.05);
  overflow: hidden;
  transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
}

.pet-card::before {
  content: '';
  position: absolute;
  inset: 0 auto auto 0;
  width: 100%;
  height: 3px;
  background: var(--elem);
  opacity: 0.55;
}

.pet-card:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--elem) 38%, transparent);
  box-shadow: 0 14px 28px rgba(42, 108, 140, 0.1);
}

.pet-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.pet-badges {
  display: flex;
  align-items: center;
  gap: 3px;
  flex: none;
}

.pet-no {
  font-size: 9px;
  color: var(--faint);
  letter-spacing: 0.06em;
}

.pet-stage {
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--panel-2);
  border: 1px solid var(--border-soft);
  color: var(--muted);
  font-size: 8.5px;
}

.pet-orb {
  align-self: center;
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  margin: 2px 0;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--elem) 35%, transparent);
  background:
    radial-gradient(circle at 32% 26%, rgba(255, 255, 255, 0.95), transparent 42%),
    color-mix(in srgb, var(--elem) 18%, white);
  color: var(--elem);
  font-size: 19px;
  font-weight: 700;
  letter-spacing: -0.02em;
  box-shadow: inset 0 -6px 14px color-mix(in srgb, var(--elem) 16%, transparent);
}

.pet-name-row {
  display: flex;
  align-items: baseline;
  min-width: 0;
}

.pet-name-row strong {
  font-size: 13px;
  letter-spacing: -0.01em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pet-total {
  padding: 1px 6px;
  border: 1px solid rgba(216, 149, 34, 0.28);
  border-radius: 999px;
  background: rgba(255, 198, 95, 0.18);
  color: #8a5a00;
  font-size: 10px;
}

.pet-ability {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-height: 28px;
  font-size: 9.5px;
  line-height: 1.45;
  color: var(--muted);
}

.pet-ability b {
  color: var(--text-soft);
  font-weight: 600;
  font-size: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pet-bars {
  display: flex;
  gap: 2px;
  height: 4px;
  align-items: flex-end;
}

.pet-bars i {
  height: 100%;
  border-radius: 2px;
  opacity: 0.85;
  transition: width 0.2s ease;
}

.dex-empty {
  grid-column: 1 / -1;
}

.skill-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.skill-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 15px;
  border-radius: 12px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.skill-row:hover {
  border-color: #a8d4e8;
  box-shadow: 0 8px 20px rgba(42, 108, 140, 0.07);
}

.skill-main {
  flex: 1;
  min-width: 0;
}

.skill-title {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.skill-title strong {
  font-size: 13px;
}

.skill-tag {
  display: inline-flex;
  align-items: center;
  height: 19px;
  padding: 0 7px;
  border: 1px solid;
  border-radius: 999px;
  font-size: 9px;
  white-space: nowrap;
}

.skill-main p {
  margin-top: 4px;
  font-size: 10.5px;
  line-height: 1.55;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}

.skill-metrics {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: none;
}

.skill-metrics > div {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
}

.skill-metrics span {
  font-size: 14px;
  color: var(--text-soft);
}

.skill-metrics small {
  font-size: 8px;
  color: var(--faint);
  letter-spacing: 0.08em;
}

.load-more {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.dex-footer-note {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 22px;
  padding: 10px 13px;
  border-radius: 9px;
  border: 1px solid var(--paper-muted);
  background: linear-gradient(180deg, var(--paper-soft), var(--paper));
  font-size: 10.5px;
  line-height: 1.6;
  color: var(--muted);
}

.dex-footer-note svg {
  color: var(--gold-strong);
  flex: none;
}

/* ---------------------------------------------------------------- drawer */
.dex-drawer-mask {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  justify-content: flex-end;
  background: rgba(16, 43, 58, 0.28);
  backdrop-filter: blur(3px);
}

.dex-drawer {
  width: min(520px, 94vw);
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fbfdff;
  border-left: 1px solid var(--border);
  box-shadow: -24px 0 60px rgba(20, 60, 84, 0.16);
  overflow: hidden;
}

.drawer-head {
  padding: 16px 20px 18px;
  border-bottom: 1px solid var(--border-soft);
  background:
    radial-gradient(circle at 88% -20%, color-mix(in srgb, var(--elem) 26%, transparent), transparent 60%),
    linear-gradient(180deg, #ffffff, #f5fbff);
}

.drawer-head-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.drawer-no {
  font-size: 10px;
  color: var(--faint);
  letter-spacing: 0.1em;
}

.drawer-head-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.drawer-head-actions .btn {
  color: var(--primary);
}

.drawer-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.drawer-orb {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--elem) 36%, transparent);
  background:
    radial-gradient(circle at 30% 26%, rgba(255, 255, 255, 0.98), transparent 44%),
    color-mix(in srgb, var(--elem) 20%, white);
  color: var(--elem);
  font-size: 22px;
  font-weight: 700;
  flex: none;
  box-shadow: inset 0 -8px 18px color-mix(in srgb, var(--elem) 14%, transparent);
}

.drawer-title-row h2 {
  font-size: 22px;
  letter-spacing: -0.03em;
  line-height: 1.2;
}

.drawer-sub {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 6px;
  flex-wrap: wrap;
}

/* 配色标签：异色偏品红、污染偏紫，和属性/阶段标签区分开。 */
.drawer-sub .variant-chip {
  border-color: #7dd3fc55;
  color: #7dd3fc;
}

.drawer-sub .variant-chip.shiny {
  border-color: #f0abfc55;
  color: #f0abfc;
}

.drawer-sub .variant-chip.polluted {
  border-color: #a78bfa55;
  color: #a78bfa;
}

.drawer-body {
  flex: 1;
  overflow: auto;
  padding: 4px 20px 28px;
}

.drawer-section {
  padding: 16px 0;
  border-bottom: 1px solid var(--border-soft);
}

.drawer-section:last-child {
  border-bottom: none;
}

.drawer-section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--faint);
  margin-bottom: 10px;
}

.drawer-section-title .mono {
  color: var(--primary);
  font-size: 9px;
}

.ability-card {
  padding: 12px 13px;
  border: 1px solid var(--paper-muted);
  border-radius: 11px;
  background: linear-gradient(180deg, var(--paper-soft), #fff);
}

.ability-card b {
  font-size: 12.5px;
}

.ability-card p {
  margin-top: 4px;
  font-size: 10.5px;
  line-height: 1.65;
  color: var(--muted);
}

.stat-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.stat-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stat-label {
  width: 30px;
  flex: none;
  font-size: 10px;
  color: var(--muted);
}

.stat-track {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: #e6f2fa;
  overflow: hidden;
}

.stat-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.stat-value {
  width: 30px;
  flex: none;
  text-align: right;
  font-size: 11px;
  color: var(--text-soft);
}

.drawer-skills {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 320px;
  overflow: auto;
  padding-right: 2px;
}

.drawer-skill {
  padding: 9px 11px;
  border: 1px solid var(--border-soft);
  border-radius: 9px;
  background: #fff;
}

.drawer-skill-head {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.drawer-skill-head strong {
  font-size: 11.5px;
}

.drawer-skill-metric {
  margin-left: auto;
  font-size: 9px;
  color: var(--faint);
}

.drawer-skill p {
  margin-top: 3px;
  font-size: 9.5px;
  line-height: 1.55;
  color: var(--muted);
}

.evolution-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.evolution-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 11px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: #fff;
  font-size: 11px;
}

.evolution-row .mono {
  margin-left: auto;
  font-size: 9.5px;
  color: var(--primary);
}

.evolution-row .muted {
  font-size: 9.5px;
}

.drawer-empty {
  font-size: 10.5px;
  color: var(--faint);
}

.related-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.related-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  border: 1px solid var(--border-soft);
  border-radius: 999px;
  background: #fff;
  color: var(--text-soft);
  font-size: 10.5px;
}

.related-item i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--elem);
}

.related-item .mono {
  font-size: 9px;
  color: var(--faint);
}

.related-item:hover {
  border-color: color-mix(in srgb, var(--elem) 40%, transparent);
  background: color-mix(in srgb, var(--elem) 6%, white);
}

.drawer-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 48px 20px;
  font-size: 11px;
  color: var(--muted);
}

.skeleton-row h2 {
  color: var(--faint);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 780px) {
  .dex-toolbar {
    position: static;
  }

  .dex-grid {
    grid-template-columns: repeat(auto-fill, minmax(148px, 1fr));
  }

  .skill-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .skill-metrics {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
