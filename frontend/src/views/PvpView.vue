<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../lib/api'
import { notify } from '../lib/toast'

interface OpponentMember {
  name: string
  type?: string
  hp?: number
  skills?: string[]
}

interface Opponent {
  id: string
  name: string
  description: string
  members: OpponentMember[]
}

interface ObservedPet {
  name: string
  element: string
  elementColor: string
  stage: string
  total: number
  speed: number
  bulk?: number
}

interface PvpMeta {
  dex: {
    total: number
    elements: { name: string; count: number; color: string }[]
  }
  opponents: Opponent[]
  observations: {
    topTotal: ObservedPet[]
    topSpeed: ObservedPet[]
    topBulk: ObservedPet[]
  }
  disclaimer: string
}

interface PvpMember {
  name: string
  spiritNo: string
  element: string
  elementColor: string
  stage: string
  role: string
  total: number
  speed: number
  bulk: number
  stats: Record<string, number>
  skills: { name: string; element: string; category: string; power: number; energy: number }[]
}

interface Analysis {
  ok: boolean
  members: PvpMember[]
  metrics: {
    count: number
    avgTotal: number
    avgSpeed: number
    maxSpeed: number
    avgBulk: number
    elements: string[]
    duplicateElements: number
    physical: number
    special: number
    fast: number
    skillCategories: Record<string, number>
    coverage: number
    score: number
  }
  roles: Record<string, number>
  notes: string[]
}

interface BattleLog {
  kind: string
  text?: string
  turn?: number
  a?: string
  b?: string
  hpA?: number
  hpB?: number
  deltaA?: number
  deltaB?: number
}

interface Matchup {
  ok: boolean
  error?: string
  winner?: string
  turns?: number
  durationMs?: number
  logs?: BattleLog[]
  player?: Analysis
  enemy?: { ok: boolean; id: string; members: { name: string; type: string; element?: string; elementColor?: string; hp: number; skills: string[] }[] }
}

const meta = ref<PvpMeta | null>(null)
const team = ref<string[]>([])
const opponent = ref('')
const simulations = ref(40)
const maxTurns = ref(30)

const search = ref('')
const searchResults = ref<{ name: string; element: string; elementColor: string; stage: string; total: number }[]>([])
const searching = ref(false)
const searchTimer = ref<ReturnType<typeof setTimeout> | null>(null)

const analysis = ref<Analysis | null>(null)
const analyzing = ref(false)
const result = ref<Matchup | null>(null)
const running = ref(false)

// ---- community PvP dataset (datasets/pvp/pvp_data.db via /api/pvp/dataset*)
interface DatasetCounts {
  pet?: number
  skill?: number
  trait?: number
  pet_skill?: number
  usage?: number
  [key: string]: number | undefined
}

interface DatasetSummary {
  available: boolean
  counts: DatasetCounts
  sources: Record<string, { repo: string; commit: string }>
  typeSource: string
  typeConflicts: { atk: string; def: string; bwiki: number; rokepvp: number }[]
  usageNote: string
  skillsByCategory: Record<string, number>
}

interface DatasetUsageRow {
  label: string
  percent: number
  ratio: number
  rank: number
}

interface DatasetSkill {
  name: string
  element: string
  category: string
  power: number | null
  energy: number | null
  combo: number | null
  unlock?: string
  description?: string
}

interface DatasetProfile {
  available: boolean
  found: boolean
  name?: string
  pet?: {
    id: string
    no: string
    name: string
    baseName: string
    form: string
    types: string[]
    stats: Record<string, number>
    total: number
    stageTag: string
    boss: boolean
    trait: string
    usagePercent: number
    usageRatio: number
  }
  trait?: { name: string; category: string; effect: string } | null
  defense?: { weak: { type: string; multiplier: number }[]; resist: { type: string; multiplier: number }[]; immune: string[] }
  offense?: { strong: { type: string; multiplier: number }[]; resisted: { type: string; multiplier: number }[] }
  recommended?: { skills: DatasetSkill[]; natures: string[]; individualValues: string[] }
  usage?: Record<string, DatasetUsageRow[]>
  learnset?: DatasetSkill[]
  variant?: {
    colorType: string
    colorLabel: string
    colorBase: string
    colorEffect: string
    season: number | null
    isShiny: boolean
    isPolluted: boolean
    formLabel: string
    formRaw: string
  }
  siblings?: { name: string; form: string; colorType: string; colorLabel: string; types: string[] }[]
}

const dataset = ref<DatasetSummary | null>(null)
const profile = ref<DatasetProfile | null>(null)
const profileName = ref('')
const profileLoading = ref(false)

const datasetCounts = computed<DatasetCounts>(() => dataset.value?.counts || {})
const usageLabel = computed(() => (datasetCounts.value.usage || 0).toLocaleString('zh-CN'))
const statLabels: Record<string, string> = { hp: '生命', atk: '物攻', mag: '魔攻', def: '物防', res: '魔防', spd: '速度' }
const statRows = computed(() => {
  const stats = profile.value?.pet?.stats
  if (!stats) return []
  return Object.keys(statLabels).map((key) => ({ key, label: statLabels[key], value: Number(stats[key] || 0) }))
})
const maxStat = computed(() => Math.max(1, ...statRows.value.map((row) => row.value)))
const topLearnset = computed(() => (profile.value?.learnset || []).filter((item) => item.power).slice(0, 8))
const usageSkills = computed(() => (profile.value?.usage?.skill || []).slice(0, 6))
const usageNatures = computed(() => (profile.value?.usage?.nature || []).slice(0, 4))
// Upstream stores individual values as stat codes (hp/pa/ma/pd/md/sp).
const ivLabels = computed(() => {
  const map: Record<string, string> = { hp: '生命', pa: '物攻', ma: '魔攻', pd: '物防', md: '魔防', sp: '速度' }
  return (profile.value?.recommended.individualValues || []).map((code) => map[code] || code)
})
const traitKind = computed(() => {
  const map: Record<string, string> = {
    ignored: '未结构化',
    passive: '被动',
    generic_stack: '可叠加',
    special_condition: '特殊条件',
  }
  const category = profile.value?.trait?.category || ''
  return map[category] || category
})

async function loadProfile(name: string) {
  if (!name) return
  profileLoading.value = true
  profileName.value = name
  try {
    profile.value = await api<DatasetProfile>(`/api/pvp/dataset/pets/${encodeURIComponent(name)}`)
  } catch (error) {
    notify(`读取 PvP 数据集失败：${error}`, 'error')
  } finally {
    profileLoading.value = false
  }
}

async function loadDataset() {
  try {
    dataset.value = await api<DatasetSummary>('/api/pvp/dataset')
  } catch {
    dataset.value = null
  }
}

let analyzeSeq = 0
let analyzeTimer: ReturnType<typeof setTimeout> | null = null

const teamFull = computed(() => team.value.length >= 6)

// The backend resolves loose names (千棘盔 -> 千棘盔（本来的样子）) but keeps
// the team order, so slots read the analysis by index, not by name.
function memberAt(index: number): PvpMember | null {
  return analysis.value?.members?.[index - 1] || null
}
const teamReady = computed(() => team.value.length > 0 && !analyzing.value)
const winnerLabel = computed(() => {
  if (!result.value?.winner) return ''
  if (result.value.winner === 'a') return '我方胜利'
  if (result.value.winner === 'b') return '对方胜利'
  return '平局'
})
const winnerTone = computed(() => {
  if (!result.value?.winner) return ''
  if (result.value.winner === 'a') return 'success'
  if (result.value.winner === 'b') return 'danger'
  return 'amber'
})

function addPet(name: string) {
  if (!name) return
  if (team.value.includes(name)) {
    notify(`${name} 已经在阵容里`, 'info')
    return
  }
  if (team.value.length >= 6) {
    notify('阵容最多 6 只精灵', 'info')
    return
  }
  team.value = [...team.value, name]
  result.value = null
  search.value = ''
  searchResults.value = []
}

function removePet(name: string) {
  team.value = team.value.filter((item) => item !== name)
  result.value = null
}

function fillFromOpponent(item: Opponent) {
  team.value = item.members.map((member) => member.name).filter(Boolean).slice(0, 6)
  result.value = null
}

async function searchPets() {
  const query = search.value.trim()
  if (!query) {
    searchResults.value = []
    return
  }
  searching.value = true
  try {
    const data = await api<{ items: any[] }>(`/api/dex/pokemon?q=${encodeURIComponent(query)}&limit=14`)
    searchResults.value = data.items.map((item) => ({
      name: item.name,
      element: item.element,
      elementColor: item.elementColor,
      stage: item.stage,
      total: item.total,
    }))
  } catch (error) {
    notify(`搜索精灵失败：${error}`, 'error')
  } finally {
    searching.value = false
  }
}

function scheduleSearch() {
  if (searchTimer.value) clearTimeout(searchTimer.value)
  searchTimer.value = setTimeout(searchPets, 280)
}

async function analyze() {
  if (!team.value.length) {
    analysis.value = null
    return
  }
  const seq = ++analyzeSeq
  analyzing.value = true
  try {
    const data = await api<Analysis>('/api/pvp/analyze', {
      method: 'POST',
      body: JSON.stringify({ team: team.value }),
    })
    if (seq === analyzeSeq) analysis.value = data
  } catch (error: any) {
    if (seq === analyzeSeq) notify(`阵容分析失败：${error?.payload?.detail || error}`, 'error')
  } finally {
    if (seq === analyzeSeq) analyzing.value = false
  }
}

function scheduleAnalyze() {
  if (analyzeTimer) clearTimeout(analyzeTimer)
  analyzeTimer = setTimeout(analyze, 420)
}

async function runMatchup() {
  if (!team.value.length) {
    notify('请先选择阵容', 'info')
    return
  }
  running.value = true
  result.value = null
  try {
    result.value = await api<Matchup>('/api/pvp/matchup', {
      method: 'POST',
      body: JSON.stringify({
        team: team.value,
        opponent: opponent.value,
        simulations: simulations.value,
        maxTurns: maxTurns.value,
      }),
    })
    if (result.value.ok) notify(`推演完成 · ${winnerLabel.value}`, 'success')
    else notify(result.value.error || '推演失败', 'error')
  } catch (error: any) {
    notify(`推演失败：${error?.payload?.detail || error}`, 'error')
  } finally {
    running.value = false
  }
}

function roleTone(role: string) {
  return {
    速攻: '#e11d48',
    物攻: '#ea580c',
    魔攻: '#7c3aed',
    耐久: '#0b7fab',
    均衡: '#059669',
  }[role] || '#0b7fab'
}

function coverageWidth(count: number, categories: Record<string, number>) {
  const max = Math.max(...Object.values(categories), 1)
  return `${Math.max(8, Math.round((count / max) * 100))}%`
}

function logText(log: BattleLog) {
  if (log.text) return log.text
  return `第 ${log.turn} 回合 · 我方 ${log.a} / 对方 ${log.b} · HP ${log.hpA ?? '—'} : ${log.hpB ?? '—'}`
}

function loadTeamFromMeta(data: PvpMeta) {
  const starter = data.opponents.find((item) => item.id === 'toxic') || data.opponents[0]
  const rival = data.opponents.find((item) => item.id === 'wing') || data.opponents.find((item) => item !== starter)
  if (starter) team.value = starter.members.map((member) => member.name).filter(Boolean).slice(0, 6)
  if (rival) opponent.value = rival.id
}

onMounted(async () => {
  loadDataset()
  try {
    meta.value = await api<PvpMeta>('/api/pvp/meta')
    loadTeamFromMeta(meta.value)
    if (team.value.length) analyze()
    if (team.value.length) loadProfile(team.value[0])
  } catch (error) {
    notify(`读取 PvP 数据失败：${error}`, 'error')
  }
})

watch(search, scheduleSearch)
watch(team, scheduleAnalyze)

onBeforeUnmount(() => {
  if (searchTimer.value) clearTimeout(searchTimer.value)
  if (analyzeTimer) clearTimeout(analyzeTimer)
})
</script>

<template>
  <div class="page pvp-page">
    <header class="page-head">
      <div>
        <div class="eyebrow">PvP Balance Lab</div>
        <h1>PvP 平衡实验室</h1>
        <p class="page-sub">
          用本地图鉴组出 6 人阵容，查看速度线、耐久、物魔分布与技能覆盖，再交给 MCTS 与预设队伍跑一局 6v6 推演。
        </p>
      </div>
      <div class="page-actions">
        <span v-if="meta" class="chip">{{ meta.dex.total }} 精灵</span>
        <span class="chip amber">研究用 · 非官方强度榜</span>
        <a class="chip primary" href="https://github.com/Pacific-shark/roco-balance-lab" target="_blank" rel="noreferrer">
          <AppIcon name="external" :size="12" /> roco-balance-lab
        </a>
      </div>
    </header>

    <div class="pvp-top">
      <section class="panel team-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="battle" :size="15" /> 我方阵容</div>
          <span class="chip mono">{{ team.length }} / 6</span>
        </div>
        <div class="panel-body">
          <label class="pet-search">
            <AppIcon name="search" :size="14" />
            <input v-model="search" placeholder="搜索精灵加入阵容，例如 迪莫 / 音速犬" aria-label="搜索精灵" />
            <span v-if="searching" class="status-dot running" />
          </label>
          <div v-if="searchResults.length" class="search-drop">
            <button
              v-for="item in searchResults"
              :key="item.name"
              class="search-item"
              :disabled="team.includes(item.name) || teamFull"
              @click="addPet(item.name)"
            >
              <i :style="{ background: item.elementColor }" />
              <strong>{{ item.name }}</strong>
              <span :style="{ color: item.elementColor }">{{ item.element }}</span>
              <span class="mono">{{ item.total }}</span>
              <span class="search-add">{{ team.includes(item.name) ? '已选' : '+' }}</span>
            </button>
          </div>

          <div class="team-slots">
            <div
              v-for="index in 6"
              :key="index"
              class="team-slot"
              :class="{ filled: team[index - 1], active: team[index - 1] && profileName === team[index - 1] }"
            >
              <span class="slot-index mono">0{{ index }}</span>
              <template v-if="team[index - 1]">
                <div class="slot-orb" :style="{ '--elem': memberAt(index)?.elementColor || '#38bdf8' }">
                  {{ memberAt(index)?.element || '?' }}
                </div>
                <button
                  class="slot-main slot-main-btn"
                  :title="`在数据面板查看 ${team[index - 1]}`"
                  @click="loadProfile(team[index - 1])"
                >
                  <strong>{{ memberAt(index)?.name || team[index - 1] }}</strong>
                  <span
                    v-if="memberAt(index)"
                    class="slot-meta"
                  >
                    {{ memberAt(index)?.role }} ·
                    {{ memberAt(index)?.total }} 种族值
                  </span>
                  <span v-else class="slot-meta">点击查看数据面板</span>
                </button>
                <button class="slot-remove" title="移除" @click="removePet(team[index - 1])">
                  <AppIcon name="close" :size="12" />
                </button>
              </template>
              <span v-else class="slot-empty">空位 · 从上方搜索加入</span>
            </div>
          </div>

          <div class="quick-fill">
            <span class="quick-label">快速填入</span>
            <button
              v-for="item in meta?.opponents || []"
              :key="item.id"
              class="btn btn-sm"
              @click="fillFromOpponent(item)"
            >
              {{ item.name }}
            </button>
            <button class="btn btn-sm" @click="team = []">清空</button>
          </div>
        </div>
      </section>

      <section class="panel analysis-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="activity" :size="15" /> 阵容分析</div>
          <span v-if="analyzing" class="chip"><span class="status-dot running" /> 分析中</span>
          <span v-else-if="analysis" class="chip success">启发式评分</span>
        </div>
        <div v-if="analysis" class="panel-body">
          <div class="score-row">
            <div class="score-dial" :style="{ '--score': `${Math.min(100, analysis.metrics.score)}%` }">
              <strong>{{ analysis.metrics.score }}</strong>
              <small>研究评分</small>
            </div>
            <div class="score-metrics">
              <div><span class="mono">{{ analysis.metrics.avgTotal }}</span><small>平均种族值</small></div>
              <div><span class="mono">{{ analysis.metrics.avgSpeed }}</span><small>平均速度</small></div>
              <div><span class="mono">{{ analysis.metrics.maxSpeed }}</span><small>最高速度</small></div>
              <div><span class="mono">{{ analysis.metrics.avgBulk }}</span><small>平均耐久</small></div>
            </div>
          </div>

          <div class="analysis-sub">属性与定位</div>
          <div class="metric-tags">
            <span
              v-for="element in analysis.metrics.elements"
              :key="element"
              class="element-pill"
              :style="{ color: meta?.dex.elements.find((e) => e.name === element)?.color, borderColor: `${meta?.dex.elements.find((e) => e.name === element)?.color}44` }"
            >
              {{ element }}系
            </span>
            <span v-for="(count, role) in analysis.roles" :key="role" class="role-pill" :style="{ color: roleTone(String(role)) }">
              {{ role }} ×{{ count }}
            </span>
          </div>

          <div class="analysis-sub">技能覆盖</div>
          <div class="coverage-bars">
            <div v-for="(count, category) in analysis.metrics.skillCategories" :key="category" class="coverage-row">
              <span>{{ category }}</span>
              <div class="coverage-track">
                <i :style="{ width: coverageWidth(count, analysis.metrics.skillCategories) }" />
              </div>
              <span class="mono">{{ count }}</span>
            </div>
          </div>

          <div class="notes">
            <div v-for="note in analysis.notes" :key="note" class="note-line">
              <AppIcon name="warning" :size="12" /> {{ note }}
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <AppIcon name="battle" :size="26" />
          <div>从左侧加入精灵后，这里会显示阵容结构分析。</div>
        </div>
      </section>
    </div>

    <div class="section-title" style="margin-top: 26px">
      <h2>数据面板</h2>
      <span class="hint">社区数据集：六维、技能威力与能耗、特性效果、公开使用率；属性相克表已与 BWIKI 合并</span>
    </div>
    <section class="panel dataset-panel">
      <div class="panel-head">
        <div class="panel-title"><AppIcon name="database" :size="15" /> PvP 数据集</div>
        <div class="dataset-chips">
          <span v-if="dataset?.available" class="chip mono">{{ datasetCounts.pet }} 精灵</span>
          <span v-if="dataset?.available" class="chip mono">{{ datasetCounts.skill }} 技能</span>
          <span v-if="dataset?.available" class="chip mono">{{ datasetCounts.trait }} 特性</span>
          <span v-if="dataset?.available" class="chip mono">{{ usageLabel }} 使用率条目</span>
          <span v-if="profileLoading" class="chip"><span class="status-dot running" /> 读取中</span>
        </div>
      </div>

      <div v-if="profile && profile.found && profile.pet && profile.defense && profile.recommended" class="dataset-body">
        <div class="dataset-col">
          <div class="profile-head">
            <div class="profile-name">
              <strong>{{ profile.pet.name }}</strong>
              <span class="mono">NO.{{ profile.pet.no }}</span>
              <span v-if="profile.pet.stageTag" class="chip">{{ profile.pet.stageTag }}</span>
              <span v-if="profile.pet.boss" class="chip amber">首领</span>
              <span
                v-if="profile.variant && profile.variant.colorType !== 'normal'"
                class="chip variant-chip"
                :class="{ shiny: profile.variant.isShiny, polluted: profile.variant.isPolluted }"
                :title="profile.variant.colorEffect"
              >{{ profile.variant.colorLabel }}</span>
              <span v-if="profile.variant?.formLabel" class="chip">{{ profile.variant.formLabel }}</span>
              <span v-if="profile.variant?.season" class="chip mono">S{{ profile.variant.season }}</span>
            </div>
            <div v-if="profile.siblings && profile.siblings.length" class="variant-siblings">
              <span class="variant-label">同族形态</span>
              <button
                v-for="item in profile.siblings"
                :key="item.name"
                class="variant-link"
                :title="item.colorLabel"
                @click="loadProfile(item.name)"
              >{{ item.name }}</button>
            </div>
            <div class="profile-types">
              <span
                v-for="type in profile.pet.types"
                :key="type"
                class="element-pill"
                :style="{ color: meta?.dex.elements.find((e) => e.name === type)?.color, borderColor: `${meta?.dex.elements.find((e) => e.name === type)?.color}44` }"
              >
                {{ type }}系
              </span>
              <span class="chip mono">种族值 {{ profile.pet.total }}</span>
              <span v-if="profile.pet.usagePercent" class="chip success">主流技能 {{ profile.pet.usagePercent }}%</span>
            </div>
          </div>

          <div class="stat-bars">
            <div v-for="row in statRows" :key="row.key" class="stat-row">
              <span>{{ row.label }}</span>
              <div class="stat-track">
                <i :style="{ width: `${Math.round((row.value / maxStat) * 100)}%` }" />
              </div>
              <span class="mono">{{ row.value }}</span>
            </div>
          </div>

          <div v-if="profile.trait" class="trait-box">
            <div class="trait-name">
              <AppIcon name="spark" :size="12" /> {{ profile.trait.name }}
              <span v-if="traitKind" class="mono"> · {{ traitKind }}</span>
            </div>
            <p>{{ profile.trait.effect }}</p>
          </div>

          <div class="analysis-sub">弱点 / 抗性</div>
          <div class="metric-tags">
            <span v-for="item in profile.defense.weak" :key="`w-${item.type}`" class="type-chip weak">
              {{ item.type }} ×{{ item.multiplier }}
            </span>
            <span v-for="item in profile.defense.resist" :key="`r-${item.type}`" class="type-chip resist">
              {{ item.type }} ×{{ item.multiplier }}
            </span>
            <span v-if="!profile.defense.weak.length && !profile.defense.resist.length" class="chip">无显著相克</span>
          </div>
        </div>

        <div class="dataset-col">
          <div class="analysis-sub">公开使用率 · 技能</div>
          <div v-if="usageSkills.length" class="usage-bars">
            <div v-for="item in usageSkills" :key="item.label" class="usage-row">
              <span>{{ item.label }}</span>
              <div class="usage-track">
                <i :style="{ width: `${Math.min(100, item.percent)}%` }" />
              </div>
              <span class="mono">{{ item.percent }}%</span>
            </div>
          </div>
          <div v-else class="chip">该精灵暂无使用率样本</div>

          <div class="analysis-sub">推荐配置</div>
          <div class="kit-lines">
            <div class="kit-line">
              <span>技能</span>
              <strong>{{ profile.recommended.skills.map((s) => s.name).join(' / ') || '暂无' }}</strong>
            </div>
            <div class="kit-line">
              <span>性格</span>
              <strong>{{ profile.recommended.natures.join(' / ') || '暂无' }}</strong>
            </div>
            <div class="kit-line">
              <span>个体</span>
              <strong>{{ ivLabels.join(' / ') || '暂无' }}</strong>
            </div>
            <div class="kit-line">
              <span>热门性格</span>
              <strong>{{ usageNatures.length ? usageNatures.map((n) => `${n.label} ${n.percent}%`).join(' · ') : '暂无' }}</strong>
            </div>
          </div>

          <div class="analysis-sub">技能池 · 威力前 8</div>
          <div class="learn-table">
            <div v-for="item in topLearnset" :key="item.name" class="learn-row">
              <strong>{{ item.name }}</strong>
              <span class="mono">{{ item.element }}</span>
              <span class="mono">{{ item.category }}</span>
              <span class="mono">{{ item.power ?? '—' }} 威 / {{ item.energy ?? '—' }} 能</span>
            </div>
          </div>
          <div v-if="profile.pet.form" class="dataset-note">形态：{{ profile.pet.form }} · 使用率按名字归并到该形态</div>
        </div>
      </div>

      <div v-else-if="dataset && dataset.available === false" class="empty-state">
        <AppIcon name="database" :size="26" />
        <div>
          本机还没有 PvP 数据集：仓库与发行包都不携带第三方游戏数据，按 <code>docs/PUBLISH_SCOPE.md</code> 在本机重建
          —— <code>.\.venv\Scripts\python.exe datasets\tools\pvp\fetch_pvp.py</code> 后跟
          <code>import_pvp.py</code>，刷新本页即可。
        </div>
      </div>

      <div v-else-if="!profileLoading && profileName && profile && !profile.found" class="empty-state">
        <AppIcon name="warning" :size="26" />
        <div>数据集里没有「{{ profileName }}」——换一只精灵，或先跑 <code>datasets/tools/pvp/fetch_pvp.py</code>+<code>import_pvp.py</code> 重建数据。</div>
      </div>

      <div v-else class="empty-state">
        <AppIcon name="database" :size="26" />
        <div>
          {{ profileLoading ? '正在读取数据面板 …' : '点击左侧阵容里的精灵名字，这里会展开它的六维、特性、使用率与技能池。' }}
        </div>
      </div>
    </section>

    <div class="section-title" style="margin-top: 26px">
      <h2>6v6 推演</h2>
      <span class="hint">单局确定性 MCTS；结果受模拟次数与回合上限影响，不代表正式服胜率</span>
    </div>
    <section class="panel matchup-panel">
      <div class="matchup-controls">
        <div class="opponent-picker">
          <button
            v-for="item in meta?.opponents || []"
            :key="item.id"
            class="opponent-card"
            :class="{ active: opponent === item.id }"
            @click="opponent = item.id"
          >
            <span class="opponent-title">{{ item.name }}</span>
            <span class="opponent-desc">{{ item.description }}</span>
            <span class="opponent-members">
              {{ item.members.map((m) => m.name).join(' · ') }}
            </span>
          </button>
        </div>
        <div class="sim-settings">
          <label>
            模拟次数
            <select v-model.number="simulations">
              <option :value="20">20 · 快速</option>
              <option :value="40">40 · 默认</option>
              <option :value="60">60 · 精细</option>
              <option :value="120">120 · 深度</option>
            </select>
          </label>
          <label>
            回合上限
            <select v-model.number="maxTurns">
              <option :value="20">20</option>
              <option :value="30">30</option>
              <option :value="40">40</option>
            </select>
          </label>
          <button class="btn btn-primary" :disabled="running || !teamReady" @click="runMatchup">
            <AppIcon name="play" :size="14" />
            {{ running ? '推演中...' : '开始 6v6 推演' }}
          </button>
        </div>
      </div>

      <div v-if="result?.ok" class="matchup-result">
        <div class="result-banner">
          <span class="result-winner" :class="winnerTone">{{ winnerLabel }}</span>
          <span class="mono">{{ result.turns }} 回合 · {{ result.durationMs }} ms</span>
        </div>
        <div class="result-columns">
          <div>
            <div class="result-head">我方 · {{ team.length }} 人</div>
            <div v-for="member in result.player?.members || []" :key="member.name" class="result-pet">
              <i :style="{ background: member.elementColor }" />
              <span>{{ member.name }}</span>
              <span class="mono">{{ member.role }}</span>
            </div>
          </div>
          <div>
            <div class="result-head">对方 · {{ result.enemy?.members?.length || 0 }} 人</div>
            <div v-for="member in result.enemy?.members || []" :key="member.name" class="result-pet">
              <i :style="{ background: member.elementColor || '#ec4899' }" />
              <span>{{ member.name }}</span>
              <span class="mono">{{ member.element || member.type }}</span>
            </div>
          </div>
        </div>
        <div class="battle-log">
          <div v-for="(log, index) in (result.logs || []).slice(-10)" :key="index" class="battle-log-line" :class="log.kind">
            <span class="mono">{{ log.kind }}</span>
            <span>{{ logText(log) }}</span>
          </div>
        </div>
      </div>
      <div v-else-if="result && !result.ok" class="matchup-error">{{ result.error }}</div>
      <div v-else class="matchup-empty">
        <span class="mono">READY</span>
        <p>选择对手队伍与模拟参数，然后开始推演。结果会显示双方阵容、回合数与最近 10 条战斗日志。</p>
      </div>
    </section>

    <div class="section-title" style="margin-top: 26px">
      <h2>数据观察</h2>
      <span class="hint">按图鉴数据排序，仅用于了解分布，不构成推荐</span>
    </div>
    <div class="obs-grid">
      <section class="panel obs-card">
        <div class="panel-head"><div class="panel-title"><AppIcon name="spark" :size="14" /> 种族值 Top</div></div>
        <div class="panel-body obs-list">
          <div v-for="(item, index) in meta?.observations.topTotal || []" :key="item.name" class="obs-row">
            <span class="obs-rank mono">{{ String(index + 1).padStart(2, '0') }}</span>
            <i :style="{ background: item.elementColor }" />
            <span class="obs-name">{{ item.name }}</span>
            <span class="mono">{{ item.total }}</span>
          </div>
        </div>
      </section>
      <section class="panel obs-card">
        <div class="panel-head"><div class="panel-title"><AppIcon name="clock" :size="14" /> 速度 Top</div></div>
        <div class="panel-body obs-list">
          <div v-for="(item, index) in meta?.observations.topSpeed || []" :key="item.name" class="obs-row">
            <span class="obs-rank mono">{{ String(index + 1).padStart(2, '0') }}</span>
            <i :style="{ background: item.elementColor }" />
            <span class="obs-name">{{ item.name }}</span>
            <span class="mono">{{ item.speed }}</span>
          </div>
        </div>
      </section>
      <section class="panel obs-card">
        <div class="panel-head"><div class="panel-title"><AppIcon name="target" :size="14" /> 耐久 Top</div></div>
        <div class="panel-body obs-list">
          <div v-for="(item, index) in meta?.observations.topBulk || []" :key="item.name" class="obs-row">
            <span class="obs-rank mono">{{ String(index + 1).padStart(2, '0') }}</span>
            <i :style="{ background: item.elementColor }" />
            <span class="obs-name">{{ item.name }}</span>
            <span class="mono">{{ item.bulk }}</span>
          </div>
        </div>
      </section>
    </div>

    <div v-if="meta" class="pvp-note">
      <AppIcon name="warning" :size="14" />
      <span>{{ meta.disclaimer }}</span>
    </div>
  </div>
</template>

<style scoped>
.pvp-top {
  display: grid;
  grid-template-columns: minmax(0, 1.02fr) minmax(0, 0.98fr);
  gap: 16px;
}

.team-panel .panel-body {
  padding-top: 12px;
}

/* PvP 数据集面板：左侧六维与特性，右侧使用率与技能池 */
.dataset-panel .panel-body {
  padding-top: 0;
}

.dataset-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  justify-content: flex-end;
}

.dataset-body {
  display: grid;
  grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.08fr);
  gap: 18px;
  padding: 14px 16px 16px;
}

.dataset-col {
  display: flex;
  flex-direction: column;
  gap: 9px;
  min-width: 0;
}

.profile-head {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.profile-name {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
  font-size: 8.5px;
  color: var(--faint);
}

.profile-name strong {
  font-size: 14px;
  color: var(--ink);
}

.profile-types {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  align-items: center;
}

/* 形态与配色是两条轴：配色标签单独配色，避免和属性/阶段标签混淆。 */
.variant-chip {
  border-color: #7dd3fc55;
  color: #7dd3fc;
}

.variant-chip.shiny {
  border-color: #f0abfc55;
  color: #f0abfc;
}

.variant-chip.polluted {
  border-color: #a78bfa55;
  color: #a78bfa;
}

.variant-siblings {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 9px;
  color: var(--faint);
}

.variant-label {
  letter-spacing: 0.06em;
}

.variant-link {
  background: none;
  border: 1px dashed var(--line);
  border-radius: 4px;
  padding: 1px 6px;
  font-size: 9.5px;
  color: var(--ink-2);
  cursor: pointer;
}

.variant-link:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.stat-bars {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.stat-row {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 34px;
  align-items: center;
  gap: 8px;
  font-size: 8.5px;
  color: var(--muted);
}

.stat-row .mono {
  text-align: right;
  color: var(--ink);
}

.stat-track {
  height: 6px;
  border-radius: 3px;
  background: var(--panel-2);
  overflow: hidden;
}

.stat-track i {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, color-mix(in srgb, var(--primary) 62%, white), var(--primary));
}

.trait-box {
  padding: 8px 10px;
  border: 1px solid color-mix(in srgb, var(--primary) 26%, transparent);
  border-radius: 9px;
  background: color-mix(in srgb, var(--primary) 7%, white);
}

.trait-name {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  font-weight: 600;
  color: var(--ink);
}

.trait-box p {
  margin: 5px 0 0;
  font-size: 9px;
  line-height: 1.55;
  color: var(--muted);
}

.type-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: #fff;
  font-size: 8.5px;
}

.type-chip.weak {
  border-color: #fecdd3;
  background: #fff1f2;
  color: #be123c;
}

.type-chip.resist {
  border-color: #bbf7d0;
  background: #f0fdf4;
  color: #15803d;
}

.usage-bars {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.usage-row {
  display: grid;
  grid-template-columns: minmax(0, 96px) minmax(0, 1fr) 44px;
  align-items: center;
  gap: 8px;
  font-size: 9px;
  color: var(--muted);
}

.usage-row > span:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ink);
}

.usage-row .mono {
  text-align: right;
}

.usage-track {
  height: 6px;
  border-radius: 3px;
  background: var(--panel-2);
  overflow: hidden;
}

.usage-track i {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, #7dd3fc, var(--primary));
}

.kit-lines {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.kit-line {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 8px;
  font-size: 9px;
  color: var(--muted);
}

.kit-line strong {
  font-weight: 500;
  color: var(--ink);
  line-height: 1.5;
}

.learn-table {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border);
  border-radius: 9px;
  overflow: hidden;
}

.learn-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 40px 44px 92px;
  gap: 8px;
  align-items: center;
  padding: 5px 9px;
  font-size: 9px;
  color: var(--muted);
  border-top: 1px solid var(--border);
}

.learn-row:first-child {
  border-top: none;
}

.learn-row strong {
  font-weight: 500;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.learn-row .mono:last-child {
  text-align: right;
}

.dataset-note {
  font-size: 8px;
  color: var(--faint);
}

.slot-main-btn {
  border: none;
  background: none;
  padding: 0;
  text-align: left;
  cursor: pointer;
  border-radius: 6px;
}

.slot-main-btn:hover strong {
  color: #a86f12;
}

.team-slot.active {
  border-color: color-mix(in srgb, var(--primary) 55%, transparent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary) 16%, transparent);
}

.pet-search {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 11px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: #fff;
  box-shadow: inset 0 1px 2px rgba(42, 108, 140, 0.04);
}

.pet-search svg {
  color: var(--primary);
  flex: none;
}

.pet-search input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-size: 12px;
}

.search-drop {
  margin-top: 6px;
  max-height: 240px;
  overflow: auto;
  border: 1px solid var(--border-soft);
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 10px 26px rgba(42, 108, 140, 0.1);
}

.search-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 10px;
  border: none;
  border-bottom: 1px solid rgba(214, 234, 245, 0.6);
  background: transparent;
  text-align: left;
  font-size: 11px;
}

.search-item:last-child {
  border-bottom: none;
}

.search-item:hover:not(:disabled) {
  background: rgba(14, 165, 233, 0.06);
}

.search-item:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.search-item i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex: none;
}

.search-item strong {
  font-size: 11.5px;
}

.search-item > span:nth-of-type(1) {
  font-size: 9px;
}

.search-item .mono {
  margin-left: auto;
  font-size: 9px;
  color: var(--faint);
}

.search-add {
  width: 22px;
  text-align: right;
  color: var(--primary);
  font-size: 10px;
}

.team-slots {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 7px;
  margin-top: 10px;
}

.team-slot {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 52px;
  padding: 8px 9px;
  border: 1px dashed var(--border);
  border-radius: 10px;
  background: rgba(246, 252, 255, 0.6);
}

.team-slot.filled {
  border-style: solid;
  background: #fff;
  box-shadow: 0 4px 12px rgba(42, 108, 140, 0.05);
}

.slot-index {
  font-size: 8px;
  color: var(--faint);
  flex: none;
}

.slot-orb {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--elem) 35%, transparent);
  background: color-mix(in srgb, var(--elem) 14%, white);
  color: var(--elem);
  font-size: 11px;
  font-weight: 700;
  flex: none;
}

.slot-main {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.slot-main strong {
  font-size: 11.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.slot-meta {
  font-size: 8.5px;
  color: var(--faint);
}

.slot-remove {
  margin-left: auto;
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 50%;
  background: var(--panel-2);
  color: var(--muted);
  flex: none;
}

.slot-remove:hover {
  background: #ffe4e9;
  color: #be123c;
}

.slot-empty {
  font-size: 9px;
  color: var(--faint);
}

.quick-fill {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border-soft);
}

.quick-label {
  font-size: 9px;
  color: var(--faint);
  letter-spacing: 0.08em;
}

.analysis-panel .panel-body {
  padding-top: 14px;
}

.score-row {
  display: flex;
  align-items: center;
  gap: 18px;
}

.score-dial {
  position: relative;
  display: grid;
  place-items: center;
  width: 92px;
  height: 92px;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #fff 58%, transparent 59%),
    conic-gradient(var(--primary) var(--score), var(--bg-deep) var(--score));
  flex: none;
}

.score-dial strong {
  font-family: var(--mono);
  font-size: 22px;
  letter-spacing: -0.04em;
}

.score-dial small {
  position: absolute;
  bottom: 20px;
  font-size: 8px;
  color: var(--faint);
}

.score-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 20px;
  flex: 1;
}

.score-metrics > div {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.score-metrics span {
  font-size: 16px;
  color: var(--text);
}

.score-metrics small {
  font-size: 8.5px;
  color: var(--faint);
  letter-spacing: 0.06em;
}

.analysis-sub {
  margin: 16px 0 7px;
  font-size: 9px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--faint);
}

.metric-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.element-pill,
.role-pill {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  border: 1px solid var(--border-soft);
  border-radius: 999px;
  background: #fff;
  font-size: 9px;
}

.coverage-bars {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.coverage-row {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 28px;
  align-items: center;
  gap: 8px;
  font-size: 9px;
  color: var(--muted);
}

.coverage-track {
  height: 5px;
  border-radius: 999px;
  background: #e6f2fa;
  overflow: hidden;
}

.coverage-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #7dd3fc, var(--primary));
}

.coverage-row .mono {
  text-align: right;
  font-size: 9px;
  color: var(--faint);
}

.notes {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.note-line {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 9.5px;
  line-height: 1.55;
  color: var(--amber);
}

.note-line svg {
  flex: none;
  margin-top: 1px;
}

.matchup-panel {
  padding: 14px 16px 16px;
}

.matchup-controls {
  display: flex;
  gap: 16px;
  justify-content: space-between;
  align-items: stretch;
  flex-wrap: wrap;
}

.opponent-picker {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.opponent-card {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 208px;
  padding: 10px 12px;
  border: 1px solid var(--border-soft);
  border-radius: 11px;
  background: #fff;
  text-align: left;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.opponent-card:hover {
  border-color: #a8d4e8;
}

.opponent-card.active {
  border-color: rgba(14, 165, 233, 0.4);
  box-shadow: 0 0 0 1px rgba(14, 165, 233, 0.12);
  background: #f8fdff;
}

.opponent-title {
  font-size: 12px;
  font-weight: 600;
}

.opponent-desc {
  font-size: 9px;
  color: var(--muted);
}

.opponent-members {
  font-size: 8.5px;
  color: var(--faint);
  margin-top: 2px;
}

.sim-settings {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.sim-settings label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 9px;
  color: var(--faint);
}

.sim-settings select {
  height: 30px;
  padding: 0 7px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: #fff;
  color: var(--text-soft);
  font-size: 10px;
}

.matchup-result {
  margin-top: 16px;
  border-top: 1px solid var(--border-soft);
  padding-top: 14px;
}

.result-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.result-winner {
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.result-winner.success {
  color: #047857;
  background: rgba(5, 150, 105, 0.1);
  border: 1px solid rgba(5, 150, 105, 0.24);
}

.result-winner.danger {
  color: #be123c;
  background: rgba(225, 29, 72, 0.08);
  border: 1px solid rgba(225, 29, 72, 0.24);
}

.result-winner.amber {
  color: #b45309;
  background: rgba(251, 191, 36, 0.14);
  border: 1px solid rgba(217, 119, 6, 0.22);
}

.result-banner .mono {
  font-size: 9.5px;
  color: var(--faint);
}

.result-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.result-head {
  font-size: 9px;
  letter-spacing: 0.1em;
  color: var(--faint);
  margin-bottom: 6px;
}

.result-pet {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 4px 0;
  border-bottom: 1px solid rgba(214, 234, 245, 0.5);
  font-size: 10px;
}

.result-pet i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.result-pet .mono {
  margin-left: auto;
  font-size: 8.5px;
  color: var(--faint);
}

.battle-log {
  margin-top: 12px;
  max-height: 190px;
  overflow: auto;
  padding: 8px 10px;
  border: 1px solid var(--border-soft);
  border-radius: 9px;
  background: rgba(246, 252, 255, 0.8);
}

.battle-log-line {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  gap: 8px;
  padding: 3px 0;
  font-size: 9.5px;
  color: var(--text-soft);
  border-bottom: 1px solid rgba(214, 234, 245, 0.45);
}

.battle-log-line:last-child {
  border-bottom: none;
}

.battle-log-line .mono {
  color: var(--primary);
  font-size: 8.5px;
}

.matchup-empty {
  margin-top: 16px;
  padding: 26px 16px;
  text-align: center;
  color: var(--muted);
  border: 1px dashed var(--border);
  border-radius: 11px;
  background: rgba(246, 252, 255, 0.5);
}

.matchup-empty .mono {
  font-size: 9px;
  letter-spacing: 0.2em;
  color: var(--primary);
}

.matchup-empty p {
  margin-top: 5px;
  font-size: 10px;
}

.matchup-error {
  margin-top: 14px;
  padding: 9px 11px;
  border: 1px solid rgba(225, 29, 72, 0.24);
  border-radius: 8px;
  background: rgba(255, 241, 245, 0.8);
  color: #be123c;
  font-size: 10.5px;
}

.obs-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 13px;
}

.obs-list {
  padding-top: 8px;
  padding-bottom: 10px;
}

.obs-row {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 0;
  border-bottom: 1px solid rgba(214, 234, 245, 0.5);
  font-size: 10px;
}

.obs-row:last-child {
  border-bottom: none;
}

.obs-rank {
  width: 18px;
  font-size: 8px;
  color: var(--faint);
}

.obs-row i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.obs-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.obs-row .mono {
  font-size: 9.5px;
  color: var(--text-soft);
}

.pvp-note {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 18px;
  padding: 10px 13px;
  border-radius: 9px;
  border: 1px solid rgba(217, 119, 6, 0.18);
  background: rgba(251, 191, 36, 0.08);
  font-size: 10px;
  line-height: 1.6;
  color: var(--muted);
}

.pvp-note svg {
  color: var(--amber);
  flex: none;
}

@media (max-width: 1100px) {
  .pvp-top {
    grid-template-columns: 1fr;
  }

  .obs-grid {
    grid-template-columns: 1fr;
  }

  .dataset-body {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .team-slots,
  .result-columns {
    grid-template-columns: 1fr;
  }

  .usage-row {
    grid-template-columns: minmax(0, 84px) minmax(0, 1fr) 40px;
  }

  .learn-row {
    grid-template-columns: minmax(0, 1fr) 34px 38px 78px;
  }
}
</style>
