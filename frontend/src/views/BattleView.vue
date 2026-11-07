<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../lib/api'
import { notify } from '../lib/toast'
import type { BattleResult, BattleTeamMember, Pokemon } from '../types'

interface TeamSlot {
  name: string
  type: string
  hp: number
  maxHp: number
  energy: number
  skills: string[]
}

const presets = ref<{ id: string; name: string; description: string }[]>([])
const playerTeam = ref<TeamSlot[]>([])
const aiTeamKey = ref('wing')
const aiTeam = ref<TeamSlot[]>([])
const pokemonTotal = ref(0)
const search = ref('')
const searchResults = ref<Pokemon[]>([])
const searching = ref(false)
const simulations = ref(40)
const maxTurns = ref(16)
const result = ref<BattleResult | null>(null)
const simulating = ref(false)
let searchTimer = 0

const elementLabels: Record<string, string> = {
  normal: '普通',
  fire: '火',
  water: '水',
  electric: '电',
  grass: '草',
  ice: '冰',
  fighting: '武',
  poison: '毒',
  ground: '地',
  flying: '翼',
  psychic: '幻',
  bug: '虫',
  steel: '机械',
  ghost: '幽',
  dragon: '龙',
  dark: '恶',
  fairy: '萌',
  light: '光',
}

const elementColors: Record<string, string> = {
  光: '#fbbf24',
  火: '#fb7185',
  水: '#38bdf8',
  草: '#4ade80',
  电: '#facc15',
  冰: '#a5f3fc',
  武: '#f97316',
  毒: '#c084fc',
  地: '#d6b58a',
  翼: '#93c5fd',
  幻: '#e879f9',
  虫: '#a3e635',
  机械: '#94a3b8',
  幽: '#a78bfa',
  龙: '#60a5fa',
  恶: '#818cf8',
  萌: '#f9a8d4',
  普通: '#cbd5e1',
}

function elementLabel(type: string): string {
  return elementLabels[type] || type
}

function colorOf(type: string): string {
  return elementColors[elementLabel(type)] || '#94a3b8'
}

const displayA = computed<TeamSlot[]>(() => {
  if (result.value?.ok && result.value.teamA?.length) {
    return result.value.teamA.map((member) => ({
      name: member.name,
      type: member.type,
      hp: member.hp,
      maxHp: member.maxHp,
      energy: member.energy,
      skills: member.skills,
    }))
  }
  return playerTeam.value
})

const displayB = computed<TeamSlot[]>(() => {
  if (result.value?.ok && result.value.teamB?.length) {
    return result.value.teamB.map((member) => ({
      name: member.name,
      type: member.type,
      hp: member.hp,
      maxHp: member.maxHp,
      energy: member.energy,
      skills: member.skills,
    }))
  }
  return aiTeam.value
})

const winnerText = computed(() => {
  if (!result.value?.ok) return ''
  if (result.value.winner === 'a') return '我方胜利'
  if (result.value.winner === 'b') return '对方胜利'
  return '平局'
})

const winnerClass = computed(() => {
  if (!result.value?.ok) return ''
  if (result.value.winner === 'a') return 'win'
  if (result.value.winner === 'b') return 'lose'
  return 'draw'
})

async function load() {
  try {
    const [presetList, species] = await Promise.all([
      api<{ id: string; name: string; description: string }[]>('/api/battle/presets'),
      api<{ total: number }>('/api/battle/pokemon?limit=1'),
    ])
    presets.value = presetList
    pokemonTotal.value = species.total
    await loadPreset('toxic', 'player')
    await loadPreset('wing', 'ai')
  } catch (error) {
    notify(`对战数据加载失败：${error}`, 'error')
  }
}

async function loadPreset(key: string, side: 'player' | 'ai') {
  try {
    const data = await api<{ ok: boolean; members: Omit<TeamSlot, 'maxHp'>[] }>(`/api/battle/presets/${key}`)
    if (!data.ok) return
    const team = data.members.map((member) => ({
      name: member.name,
      type: member.type,
      hp: member.hp,
      maxHp: member.hp,
      energy: member.energy || 10,
      skills: member.skills || [],
    }))
    if (side === 'player') {
      playerTeam.value = team
      result.value = null
    } else {
      aiTeam.value = team
      aiTeamKey.value = key
      result.value = null
    }
  } catch (error) {
    notify(`载入预设阵容失败：${error}`, 'error')
  }
}

function onSearchInput() {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(async () => {
    const keyword = search.value.trim()
    if (!keyword) {
      searchResults.value = []
      return
    }
    searching.value = true
    try {
      const data = await api<{ items: Pokemon[] }>(`/api/battle/pokemon?q=${encodeURIComponent(keyword)}&limit=12`)
      searchResults.value = data.items
    } catch {
      searchResults.value = []
    } finally {
      searching.value = false
    }
  }, 250)
}

function addMember(pokemon: Pokemon) {
  if (playerTeam.value.length >= 6) {
    notify('最多 6 只精灵', 'error')
    return
  }
  if (playerTeam.value.some((member) => member.name === pokemon.name)) {
    notify('阵容中已有这只精灵', 'error')
    return
  }
  playerTeam.value.push({
    name: pokemon.name,
    type: pokemon.element,
    hp: 0,
    maxHp: 0,
    energy: 10,
    skills: [],
  })
  search.value = ''
  searchResults.value = []
  result.value = null
}

function removeMember(index: number) {
  playerTeam.value.splice(index, 1)
  result.value = null
}

function clearResult() {
  result.value = null
}

async function simulate() {
  if (!playerTeam.value.length) {
    notify('请先添加至少一只精灵', 'error')
    return
  }
  simulating.value = true
  result.value = null
  try {
    const data = await api<BattleResult>('/api/battle/simulate', {
      method: 'POST',
      body: JSON.stringify({
        playerTeam: playerTeam.value.map((member) => ({ name: member.name })),
        aiTeam: aiTeamKey.value,
        simulations: simulations.value,
        maxTurns: maxTurns.value,
      }),
    })
    result.value = data
    if (!data.ok) notify(`推演失败：${data.error}`, 'error')
    else notify(`推演完成 · ${winnerText.value}`, 'success')
  } catch (error) {
    notify(`推演请求失败：${error}`, 'error')
  } finally {
    simulating.value = false
  }
}

function hpPercent(member: TeamSlot): number {
  if (!member.maxHp) return 100
  return Math.max(0, Math.min(100, (member.hp / member.maxHp) * 100))
}

onMounted(async () => {
  await load()
})

onBeforeUnmount(() => window.clearTimeout(searchTimer))
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <div class="eyebrow">Battle Lab</div>
        <h1>对战实验室</h1>
        <p class="page-sub">
          用对抗式 MCTS 推演两套阵容。精灵与技能数据来自本地战斗数据库，不依赖网络，也不会操作游戏。
        </p>
      </div>
      <div class="page-actions">
        <span class="chip mono">{{ pokemonTotal }} 精灵</span>
        <span class="chip mono">491 技能</span>
        <span class="chip primary">MCTS</span>
      </div>
    </header>

    <div class="battle-layout">
      <section class="panel team-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="spark" :size="15" /> 我方阵容</div>
          <div class="team-actions">
            <button class="mini-link" @click="loadPreset('toxic', 'player')">毒队</button>
            <button class="mini-link" @click="loadPreset('wing', 'player')">翼王队</button>
            <span class="chip mono">{{ playerTeam.length }}/6</span>
          </div>
        </div>
        <div class="panel-body">
          <div class="team-slots">
            <div v-for="(member, index) in displayA" :key="member.name" class="team-slot">
              <div class="slot-index mono">{{ String(index + 1).padStart(2, '0') }}</div>
              <div class="slot-avatar" :style="{ background: `${colorOf(member.type)}22`, color: colorOf(member.type), borderColor: `${colorOf(member.type)}44` }">
                {{ member.name.slice(0, 1) }}
              </div>
              <div class="slot-main">
                <div class="slot-name-row">
                  <span class="slot-name">{{ member.name }}</span>
                  <span class="slot-type" :style="{ color: colorOf(member.type) }">{{ elementLabel(member.type) }}</span>
                  <span v-if="member.energy !== undefined" class="chip mono" style="height: 18px; font-size: 8px">E{{ member.energy }}</span>
                </div>
                <div class="hp-bar">
                  <span class="hp-fill" :style="{ width: `${hpPercent(member)}%`, background: colorOf(member.type) }" />
                </div>
                <div class="slot-bottom">
                  <span class="mono faint">{{ member.maxHp ? `${member.hp}/${member.maxHp}` : 'HP —' }}</span>
                  <span class="slot-skills">{{ member.skills.slice(0, 3).join(' · ') || '技能自动填充' }}</span>
                </div>
              </div>
              <button v-if="!result?.ok" class="slot-remove" title="移除" @click="removeMember(index)">
                <AppIcon name="close" :size="12" />
              </button>
            </div>
            <div v-for="slot in Math.max(0, 6 - displayA.length)" :key="`empty-a-${slot}`" class="team-slot empty">
              <div class="slot-index mono">—</div>
              <div class="slot-avatar empty-avatar"><AppIcon name="plus" :size="14" /></div>
              <div class="slot-main"><span class="faint" style="font-size: 10px">空位</span></div>
            </div>
          </div>

          <div class="search-block">
            <div class="search-wrap">
              <AppIcon name="search" :size="14" />
              <input v-model="search" placeholder="搜索精灵名称加入阵容..." @input="onSearchInput" />
            </div>
            <div v-if="searchResults.length" class="search-results">
              <button v-for="pokemon in searchResults" :key="pokemon.id" class="search-item" @click="addMember(pokemon)">
                <span class="search-avatar" :style="{ background: `${colorOf(pokemon.element)}20`, color: colorOf(pokemon.element) }">{{ pokemon.name.slice(0, 1) }}</span>
                <span class="search-name">{{ pokemon.name }}</span>
                <span class="search-element" :style="{ color: colorOf(pokemon.element) }">{{ elementLabel(pokemon.element) }}</span>
                <span class="mono faint" style="font-size: 8.5px">#{{ pokemon.id }}</span>
              </button>
            </div>
            <div v-else-if="searching" class="search-hint">搜索中...</div>
          </div>
        </div>
      </section>

      <div class="center-col">
        <div class="versus">
          <span class="vs-line" />
          <span class="vs-mark mono">VS</span>
          <span class="vs-line" />
        </div>

        <div class="control-panel">
          <div class="control-field">
            <div class="field-label">每回合模拟 <span class="mono">{{ simulations }}</span></div>
            <input v-model.number="simulations" type="range" min="10" max="200" step="10" class="range" />
          </div>
          <div class="control-field">
            <div class="field-label">最大回合 <span class="mono">{{ maxTurns }}</span></div>
            <input v-model.number="maxTurns" type="range" min="4" max="40" step="2" class="range" />
          </div>
          <div class="control-field">
            <div class="field-label">对手阵容</div>
            <select v-model="aiTeamKey" class="select" @change="loadPreset(aiTeamKey, 'ai')">
              <option v-for="preset in presets" :key="preset.id" :value="preset.id">{{ preset.name }}</option>
            </select>
          </div>
          <button class="btn btn-primary sim-btn" :disabled="simulating" @click="simulate">
            <AppIcon :name="simulating ? 'refresh' : 'play'" :size="14" />
            {{ simulating ? '推演中...' : '开始推演' }}
          </button>
          <button v-if="result?.ok" class="btn btn-sm" style="width: 100%; margin-top: 7px" @click="clearResult">
            <AppIcon name="refresh" :size="12" /> 恢复初始状态
          </button>
        </div>

        <div v-if="result?.ok" class="result-card" :class="winnerClass">
          <div class="result-label">RESULT</div>
          <div class="result-title">{{ winnerText }}</div>
          <div class="result-meta mono">
            {{ result.turns }} 回合 · {{ result.durationMs }} ms · 模拟 {{ simulations }} 次
          </div>
        </div>
        <div v-else class="center-hint">
          选择阵容与模拟次数，<br />开始一次本地对抗推演。
        </div>
      </div>

      <section class="panel team-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="battle" :size="15" /> 对手阵容</div>
          <div class="team-actions">
            <span class="chip" :class="aiTeamKey === 'wing' ? 'pink' : 'violet'">{{ presets.find((item) => item.id === aiTeamKey)?.name }}</span>
          </div>
        </div>
        <div class="panel-body">
          <div class="preset-desc">{{ presets.find((item) => item.id === aiTeamKey)?.description }}</div>
          <div class="team-slots">
            <div v-for="(member, index) in displayB" :key="member.name" class="team-slot">
              <div class="slot-index mono">{{ String(index + 1).padStart(2, '0') }}</div>
              <div class="slot-avatar" :style="{ background: `${colorOf(member.type)}22`, color: colorOf(member.type), borderColor: `${colorOf(member.type)}44` }">
                {{ member.name.slice(0, 1) }}
              </div>
              <div class="slot-main">
                <div class="slot-name-row">
                  <span class="slot-name">{{ member.name }}</span>
                  <span class="slot-type" :style="{ color: colorOf(member.type) }">{{ elementLabel(member.type) }}</span>
                </div>
                <div class="hp-bar">
                  <span class="hp-fill" :style="{ width: `${hpPercent(member)}%`, background: colorOf(member.type) }" />
                </div>
                <div class="slot-bottom">
                  <span class="mono faint">{{ member.maxHp ? `${member.hp}/${member.maxHp}` : 'HP —' }}</span>
                  <span class="slot-skills">{{ member.skills.slice(0, 3).join(' · ') }}</span>
                </div>
              </div>
            </div>
            <div v-for="slot in Math.max(0, 6 - displayB.length)" :key="`empty-b-${slot}`" class="team-slot empty">
              <div class="slot-index mono">—</div>
              <div class="slot-avatar empty-avatar"><AppIcon name="dot" :size="12" /></div>
              <div class="slot-main"><span class="faint" style="font-size: 10px">空位</span></div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <section class="panel log-panel">
      <div class="panel-head">
        <div class="panel-title"><AppIcon name="activity" :size="15" /> 推演日志</div>
        <span class="chip mono">{{ result?.logs?.length || 0 }} 条</span>
      </div>
      <div class="panel-body log-body">
        <div v-if="result?.ok" class="log-list">
          <div v-for="(log, index) in result.logs" :key="index" class="log-row" :class="log.kind">
            <template v-if="log.kind === 'turn'">
              <span class="log-turn mono">T{{ String(log.turn).padStart(2, '0') }}</span>
              <span class="log-a">我方 · {{ log.a }}</span>
              <span class="log-vs">VS</span>
              <span class="log-b">对方 · {{ log.b }}</span>
              <span class="log-delta mono" :class="{ negative: (log.deltaA || 0) < 0 }">A {{ log.deltaA }}</span>
              <span class="log-delta mono" :class="{ negative: (log.deltaB || 0) < 0 }">B {{ log.deltaB }}</span>
            </template>
            <template v-else>
              <span class="log-turn mono">{{ log.kind === 'start' ? 'START' : 'END' }}</span>
              <span class="log-text">{{ log.text }}</span>
            </template>
          </div>
        </div>
        <div v-else-if="simulating" class="log-placeholder">MCTS 正在展开对抗树...</div>
        <div v-else class="log-placeholder">点击「开始推演」后，这里会显示每回合的双方动作与血量变化。</div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.battle-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 230px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.team-panel {
  min-height: 420px;
}

.team-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mini-link {
  border: none;
  background: transparent;
  color: var(--faint);
  font-size: 9.5px;
  padding: 0;
}

.mini-link:hover {
  color: var(--primary);
}

.team-slots {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.team-slot {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--border-soft);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.018);
  min-height: 62px;
}

.team-slot.empty {
  opacity: 0.46;
  border-style: dashed;
}

.slot-index {
  font-size: 8.5px;
  color: var(--faint);
  width: 16px;
}

.slot-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 14px;
  font-weight: 650;
  border: 1px solid transparent;
  flex: none;
}

.empty-avatar {
  border: 1px dashed var(--border);
  color: var(--faint);
}

.slot-main {
  flex: 1;
  min-width: 0;
}

.slot-name-row {
  display: flex;
  align-items: center;
  gap: 7px;
}

.slot-name {
  font-size: 12px;
  font-weight: 600;
}

.slot-type {
  font-size: 9.5px;
}

.hp-bar {
  margin-top: 5px;
  height: 3px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.07);
  overflow: hidden;
}

.hp-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  transition: width 0.5s ease;
}

.slot-bottom {
  margin-top: 4px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 9px;
}

.slot-skills {
  color: var(--faint);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.slot-remove {
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: var(--faint);
  opacity: 0;
}

.team-slot:hover .slot-remove {
  opacity: 1;
}

.slot-remove:hover {
  color: var(--danger);
  background: rgba(248, 113, 113, 0.08);
}

.search-block {
  margin-top: 10px;
  position: relative;
}

.search-wrap {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.55);
  color: var(--faint);
}

.search-wrap input {
  width: 100%;
  border: none;
  background: transparent;
  outline: none;
  font-size: 11.5px;
  color: var(--text);
}

.search-wrap input::placeholder {
  color: var(--faint);
}

.search-results {
  position: absolute;
  left: 0;
  right: 0;
  top: 36px;
  z-index: 10;
  max-height: 280px;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 18px 44px rgba(0, 0, 0, 0.5);
  padding: 4px;
}

.search-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 6px 7px;
  border: none;
  border-radius: 6px;
  background: transparent;
  text-align: left;
  color: var(--text-soft);
}

.search-item:hover {
  background: rgba(14, 165, 233, 0.12);
}

.search-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 10px;
  font-weight: 600;
  flex: none;
}

.search-name {
  font-size: 11px;
}

.search-element {
  font-size: 9px;
}

.search-item .mono {
  margin-left: auto;
}

.search-hint {
  margin-top: 6px;
  font-size: 9.5px;
  color: var(--faint);
}

.preset-desc {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-soft);
  background: rgba(255, 255, 255, 0.02);
  font-size: 10px;
  line-height: 1.6;
  color: var(--muted);
  margin-bottom: 10px;
}

.center-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding-top: 8px;
}

.versus {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.vs-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(14, 165, 233, 0.35), transparent);
}

.vs-mark {
  font-size: 11px;
  letter-spacing: 0.3em;
  color: var(--primary);
  background: rgba(14, 165, 233, 0.12);
  border: 1px solid rgba(14, 165, 233, 0.18);
  padding: 4px 8px;
  border-radius: 999px;
}

.control-panel {
  width: 100%;
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.85);
  padding: 14px;
}

.control-field + .control-field {
  margin-top: 13px;
}

.range {
  width: 100%;
  height: 4px;
  appearance: none;
  background: linear-gradient(90deg, rgba(14, 165, 233, 0.5), rgba(14, 165, 233, 0.1));
  border-radius: 999px;
  outline: none;
  margin-top: 7px;
}

.range::-webkit-slider-thumb {
  appearance: none;
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: #38bdf8;
  border: 2px solid #082f49;
}

.sim-btn {
  width: 100%;
  margin-top: 14px;
}

.result-card {
  width: 100%;
  text-align: center;
  padding: 15px 12px;
  border-radius: 12px;
  border: 1px solid var(--border-soft);
  background: rgba(255, 255, 255, 0.8);
}

.result-card.win {
  border-color: rgba(14, 165, 233, 0.35);
  background: rgba(14, 165, 233, 0.06);
}

.result-card.lose {
  border-color: rgba(248, 113, 113, 0.3);
  background: rgba(248, 113, 113, 0.05);
}

.result-label {
  font-size: 8.5px;
  letter-spacing: 0.18em;
  color: var(--faint);
}

.result-title {
  margin-top: 4px;
  font-size: 20px;
  font-weight: 650;
  letter-spacing: -0.02em;
}

.result-card.win .result-title {
  color: var(--primary);
}

.result-card.lose .result-title {
  color: #fca5a5;
}

.result-meta {
  margin-top: 4px;
  font-size: 9px;
  color: var(--faint);
}

.center-hint {
  text-align: center;
  font-size: 10px;
  line-height: 1.7;
  color: var(--faint);
}

.log-panel {
  margin-top: 16px;
}

.log-body {
  max-height: 260px;
  overflow: auto;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.log-row {
  display: grid;
  grid-template-columns: 44px 1fr auto 1fr 62px 62px;
  gap: 8px;
  align-items: center;
  padding: 5px 4px;
  border-bottom: 1px solid rgba(214, 234, 245, 0.5);
  font-size: 10.5px;
}

.log-row.start,
.log-row.end {
  grid-template-columns: 44px minmax(0, 1fr);
}

.log-turn {
  font-size: 9px;
  color: var(--primary);
}

.log-a,
.log-b {
  color: var(--text-soft);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.log-vs {
  font-size: 8px;
  color: var(--faint);
}

.log-delta {
  font-size: 9px;
  text-align: right;
  color: var(--muted);
}

.log-delta.negative {
  color: #fca5a5;
}

.log-text {
  color: var(--text-soft);
}

.log-row.end .log-text {
  color: var(--primary);
}

.log-placeholder {
  padding: 26px 6px;
  text-align: center;
  font-size: 11px;
  color: var(--faint);
}

@media (max-width: 1180px) {
  .battle-layout {
    grid-template-columns: 1fr;
  }
  .center-col {
    order: -1;
  }
}
</style>
