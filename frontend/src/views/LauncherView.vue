<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { api, formatDuration, formatTime } from '../lib/api'
import { appStore, refreshMeta } from '../lib/store'
import { notify } from '../lib/toast'
import type { OneDragonPlan, RealtimeStatus, Run, TrackerStatus, Workflow } from '../types'

const router = useRouter()
const workflows = ref<Workflow[]>([])
const runs = ref<Run[]>([])
const plan = ref<OneDragonPlan | null>(null)
const realtime = ref<RealtimeStatus | null>(null)
const tracker = ref<TrackerStatus | null>(null)
const busy = ref('')
let timer = 0

const target = computed(() => appStore.meta?.target as any)
const enabledTasks = computed(() => plan.value?.tasks.filter((task) => task.enabled).length || 0)

const features = computed(() => [
  {
    id: 'realtime',
    icon: 'crosshair',
    title: '实时任务',
    desc: '持续截图识别战斗、可捕捉精灵与同行请求，自动执行键鼠动作。',
    meta: realtime.value?.running ? `运行中 · ${realtime.value.counters.ticks} 帧` : '待启动',
    status: realtime.value?.running ? 'running' : 'idle',
    action: '打开实时任务',
    to: '/realtime',
    accent: '#0ea5e9',
  },
  {
    id: 'onedragon',
    icon: 'activity',
    title: '一条龙',
    desc: '按顺序执行丢球、战斗、同行确认与资源巡线，可调整任务开关与参数。',
    meta: `${enabledTasks.value} 个任务已启用 · ${plan.value?.loops || 3} 轮`,
    status: 'idle',
    action: '配置任务计划',
    to: '/onedragon',
    accent: '#fbbf24',
  },
  {
    id: 'tracker',
    icon: 'target',
    title: '地图追踪 · SIFT',
    desc: '从小地图识别当前位置，记录轨迹并叠加到世界地图，不读取游戏内存。',
    meta: tracker.value?.running
      ? `追踪中 · 置信度 ${tracker.value.current?.confidence ?? '—'}`
      : tracker.value?.anchor?.cached
        ? `锚点 ${tracker.value.anchor.points} 个`
        : '待建立锚点',
    status: tracker.value?.running ? 'running' : 'idle',
    action: '打开地图追踪',
    to: '/tracker',
    accent: '#34d399',
  },
  {
    id: 'workflows',
    icon: 'workflow',
    title: '独立任务',
    desc: '用可视化工作流编排截图、识别、输入、地图与对战节点。',
    meta: `${workflows.value.length} 个工作流`,
    status: 'idle',
    action: '打开工作流',
    to: '/workflows',
    accent: '#60a5fa',
  },
  {
    id: 'map',
    icon: 'map',
    title: '资源地图',
    desc: '按分类筛选资源点位，规划最近邻路线，并查看当前定位。',
    meta: `${appStore.meta?.map?.pointCount || 0} 个点位 · ${appStore.meta?.map?.categoryCount || 0} 分类`,
    status: 'idle',
    action: '打开资源地图',
    to: '/map',
    accent: '#a78bfa',
  },
  {
    id: 'battle',
    icon: 'battle',
    title: '对战实验室',
    desc: '编辑阵容并运行对抗式 MCTS 推演，查看每回合动作与血量变化。',
    meta: '461 精灵 · 491 技能 · MCTS',
    status: 'idle',
    action: '打开对战实验室',
    to: '/battle',
    accent: '#ec4899',
  },
  {
    id: 'pvp',
    icon: 'battle',
    title: 'PvP 平衡',
    desc: '组 6 人阵容，查看速度线、耐久、物魔与技能覆盖，并跑一局 MCTS 6v6 推演。',
    meta: '图鉴数据 · 阵容分析 · MCTS',
    status: 'idle',
    action: '打开平衡实验室',
    to: '/pvp',
    accent: '#e11d48',
  },
  {
    id: 'dex',
    icon: 'database',
    title: '图鉴速查',
    desc: '按名称、属性、形态快速查询精灵与技能，详情包含六维、特性、进化链。',
    meta: '461 精灵 · 491 技能 · 206 进化链',
    status: 'idle',
    action: '打开图鉴',
    to: '/dex',
    accent: '#d97706',
  },
  {
    id: 'pet',
    icon: 'spark',
    title: '桌宠工坊',
    desc: '挑一只图鉴精灵，生成可拖动的桌面伙伴窗口；纯 CSS 绘制，不依赖游戏素材。',
    meta: '461 精灵 · 待机 / 跳跃 / 睡觉',
    status: 'idle',
    action: '打开桌宠工坊',
    to: '/pet',
    accent: '#f472b6',
  },
  {
    id: 'components',
    icon: 'node',
    title: '组件图谱',
    desc: '6 个引擎、39 个组元如何被 10 个功能按需装配，以及每个组元的复用次数。',
    meta: '功能只取组元 · 组元服务多个功能',
    status: 'idle',
    action: '打开组件图谱',
    to: '/components',
    accent: '#7c3aed',
  },
  {
    id: 'harness',
    icon: 'spark',
    title: 'AI Harness',
    desc: 'DeepSeek Harness 通过 observe / press_key / run_workflow 快速接管引擎。',
    meta: 'HTTP JSON · OpenAI tools · 本地无鉴权',
    status: 'idle',
    action: '打开接入页',
    to: '/harness',
    accent: '#0891b2',
  },
])

const recentRuns = computed(() => runs.value.slice(0, 5))

async function load() {
  try {
    const [workflowList, runList, planData, realtimeData, trackerData] = await Promise.all([
      api<Workflow[]>('/api/workflows'),
      api<Run[]>('/api/runs?limit=8'),
      api<{ plan: OneDragonPlan }>('/api/onedragon/plan'),
      api<RealtimeStatus>('/api/realtime/status'),
      api<TrackerStatus>('/api/tracker/status'),
    ])
    workflows.value = workflowList
    runs.value = runList
    plan.value = planData.plan
    realtime.value = realtimeData
    tracker.value = trackerData
  } catch (error) {
    notify(`启动页加载失败：${error}`, 'error')
  }
}

async function poll() {
  try {
    const [realtimeData, trackerData] = await Promise.all([
      api<RealtimeStatus>('/api/realtime/status'),
      api<TrackerStatus>('/api/tracker/status'),
    ])
    realtime.value = realtimeData
    tracker.value = trackerData
  } catch {
    /* keep last state */
  }
}

async function toggleRealtime() {
  busy.value = 'realtime'
  try {
    if (realtime.value?.running) {
      realtime.value = await api<RealtimeStatus>('/api/realtime/stop', { method: 'POST', body: '{}' })
      notify('实时任务已停止', 'info')
    } else {
      realtime.value = await api<RealtimeStatus>('/api/realtime/start', {
        method: 'POST',
        body: JSON.stringify({ config: realtime.value?.config || {} }),
      })
      notify('实时任务已启动', 'success')
    }
    refreshMeta()
  } catch (error) {
    notify(`操作失败：${error}`, 'error')
  } finally {
    busy.value = ''
  }
}

async function startOneDragon() {
  busy.value = 'onedragon'
  try {
    const result = await api<{ runId: string }>('/api/onedragon/run', { method: 'POST', body: '{}' })
    notify('一条龙已启动', 'success')
    router.push(`/runs/${result.runId}`)
  } catch (error) {
    notify(`启动一条龙失败：${error}`, 'error')
  } finally {
    busy.value = ''
  }
}

function statusLabel(status: string): string {
  return { running: '运行中', succeeded: '已完成', failed: '失败', stopped: '已停止' }[status] || status
}

onMounted(async () => {
  await load()
  refreshMeta()
  timer = window.setInterval(poll, 2500)
})

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <div class="page launcher-page">
    <section class="hero">
      <div class="hero-art" />
      <div class="hero-inner">
        <div class="hero-copy">
          <div class="eyebrow">Rocogi · Local-first NRC Automation</div>
          <h1><span class="brand-word">Rocogi</span><br /><span class="hero-subline">洛克王国：世界 自动化工作台</span></h1>
          <p>
            以 yotta 的工作流结构为骨架，按 BetterGI 的启动器组织，整合抓宠、战斗、地图追踪、对战推演与 AI Harness。所有配置、资源与运行证据都留在本机。
          </p>
          <div class="hero-actions">
            <button class="btn btn-primary" :disabled="busy === 'onedragon'" @click="startOneDragon">
              <AppIcon name="activity" :size="15" />
              {{ busy === 'onedragon' ? '启动中...' : '开始一条龙' }}
            </button>
            <button class="btn hero-btn" @click="router.push('/realtime')">
              <AppIcon name="crosshair" :size="15" /> 实时任务
            </button>
            <button class="btn hero-btn" @click="router.push('/tracker')">
              <AppIcon name="target" :size="15" /> 地图追踪
            </button>
          </div>
        </div>
        <div class="hero-side">
          <div class="hero-chip">
            <span class="status-dot" :class="target?.kind === 'windows' ? 'succeeded' : 'running'" />
            <span>{{ target?.kind === 'windows' ? 'Windows 窗口' : '模拟目标' }}</span>
          </div>
          <div class="hero-metrics">
            <div><b>{{ appStore.meta?.workflowCount || 0 }}</b><span>工作流</span></div>
            <div><b>{{ appStore.meta?.map?.pointCount || 0 }}</b><span>地图点位</span></div>
            <div><b>{{ appStore.meta?.runCount || 0 }}</b><span>执行记录</span></div>
          </div>
          <div class="hero-note mono">Rocogi v{{ appStore.meta?.version || '0.1.0' }}</div>
        </div>
      </div>
    </section>

    <section class="launch-card panel">
      <div class="launch-main">
        <div class="launch-icon" :class="{ live: realtime?.running }">
          <AppIcon name="play" :size="20" />
        </div>
        <div class="launch-copy">
          <div class="launch-title-row">
            <h2>Rocogi 实时引擎，启动！</h2>
            <span class="chip" :class="realtime?.running ? 'primary' : ''">
              {{ realtime?.running ? '实时任务运行中' : '待启动' }}
            </span>
          </div>
          <p>
            启动后持续截取游戏窗口，识别普通/污染战斗、可捕捉精灵与同行请求。模拟目标下不会影响系统，仅记录动作。
          </p>
          <div class="launch-meta">
            <span class="chip mono">目标 {{ target?.kind === 'windows' ? 'Windows' : 'Mock' }}</span>
            <span class="chip mono">输入 {{ appStore.meta?.settings?.input?.backend || 'mock' }}</span>
            <span class="chip mono">SIFT {{ appStore.meta?.platform?.sift ? '可用' : '不可用' }}</span>
            <span class="chip mono">场景 {{ realtime?.scene || 'unknown' }}</span>
          </div>
        </div>
        <div class="launch-actions">
          <button
            class="btn"
            :class="realtime?.running ? 'btn-danger' : 'btn-primary'"
            :disabled="busy === 'realtime'"
            @click="toggleRealtime"
          >
            <AppIcon :name="realtime?.running ? 'stop' : 'play'" :size="15" />
            {{ busy === 'realtime' ? '处理中' : realtime?.running ? '停止' : '启动实时任务' }}
          </button>
          <button class="btn" @click="router.push('/settings')">
            <AppIcon name="settings" :size="14" /> 捕获设置
          </button>
        </div>
      </div>
      <div v-if="realtime?.running" class="launch-counters">
        <div><span class="stat-label">帧</span><b class="mono">{{ realtime.counters.ticks }}</b></div>
        <div><span class="stat-label">动作</span><b class="mono">{{ realtime.counters.actions }}</b></div>
        <div><span class="stat-label">战斗</span><b class="mono">{{ realtime.counters.battles }}</b></div>
        <div><span class="stat-label">丢球</span><b class="mono">{{ realtime.counters.balls }}</b></div>
        <div class="counter-live"><span class="status-dot running" /> 实时采集中</div>
      </div>
    </section>

    <div class="section-title" style="margin-top: 26px">
      <h2>功能模块</h2>
      <span class="hint">按 BetterGI 的启动器结构组织：实时任务、任务计划与独立工具</span>
    </div>

    <div class="feature-grid fade-list">
      <article v-for="feature in features" :key="feature.id" class="feature-card" @click="router.push(feature.to)">
        <div class="feature-top">
          <div class="feature-icon" :style="{ color: feature.accent, background: `${feature.accent}14` }">
            <AppIcon :name="feature.icon" :size="19" />
          </div>
          <span class="status-dot" :class="feature.status" />
        </div>
        <h3>{{ feature.title }}</h3>
        <p>{{ feature.desc }}</p>
        <div class="feature-foot">
          <span class="feature-meta">{{ feature.meta }}</span>
          <span class="feature-link">{{ feature.action }} <AppIcon name="chevron" :size="11" /></span>
        </div>
      </article>
    </div>

    <div class="dashboard-grid">
      <section class="panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="runs" :size="15" /> 最近执行</div>
          <button class="btn btn-sm" @click="router.push('/runs')">全部记录</button>
        </div>
        <div class="panel-body recent-list">
          <RouterLink
            v-for="run in recentRuns"
            :key="run.id"
            :to="`/runs/${run.id}`"
            class="recent-row"
          >
            <span class="status-dot" :class="run.status" />
            <div class="recent-main">
              <span class="recent-name">{{ run.workflowName }}</span>
              <span class="recent-time mono">{{ formatTime(run.startedAt) }}</span>
            </div>
            <span class="chip">{{ statusLabel(run.status) }}</span>
            <span class="mono recent-duration">{{ formatDuration(run.durationMs) }}</span>
          </RouterLink>
          <div v-if="!recentRuns.length" class="empty-state" style="padding: 20px">
            还没有执行记录，启动一条龙或独立任务后会出现在这里。
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="cpu" :size="15" /> 本机能力</div>
          <span class="chip mono">{{ appStore.meta?.platform?.platform }}</span>
        </div>
        <div class="panel-body">
          <div class="capability-list">
            <div class="capability-row">
              <span>截图与目标</span>
              <span class="status-dot succeeded" />
              <span class="mono">{{ target?.title || '模拟窗口' }}</span>
            </div>
            <div class="capability-row">
              <span>SIFT 地图定位</span>
              <span class="status-dot" :class="appStore.meta?.platform?.sift ? 'succeeded' : 'failed'" />
              <span class="mono">{{ tracker?.anchor?.points || 0 }} anchors</span>
            </div>
            <div class="capability-row">
              <span>对战数据</span>
              <span class="status-dot" :class="appStore.meta?.platform?.battle_ai ? 'succeeded' : 'failed'" />
              <span class="mono">461 精灵 · 491 技能</span>
            </div>
            <div class="capability-row">
              <span>地图资源</span>
              <span class="status-dot succeeded" />
              <span class="mono">{{ appStore.meta?.map?.pointCount }} POI</span>
            </div>
          </div>
          <div class="capability-note">
            本机目标与输入方式可在设置中切换；工作流只保存逻辑与目标槽位。
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.launcher-page {
  padding-top: 24px;
}

.hero {
  position: relative;
  min-height: 272px;
  border-radius: 20px;
  border: 1px solid rgba(125, 211, 252, 0.5);
  overflow: hidden;
  background: #f2faff;
  box-shadow: 0 26px 70px rgba(47, 110, 145, 0.16);
}

.hero-art {
  position: absolute;
  inset: 0;
  background-image: url('/brand/rocogi-banner.jpg');
  background-size: cover;
  background-position: center 42%;
  opacity: 1;
}

.hero::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(250, 254, 255, 0.94) 0%, rgba(250, 254, 255, 0.8) 38%, rgba(250, 254, 255, 0.2) 72%, rgba(250, 254, 255, 0.28) 100%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(244, 251, 255, 0.36));
}

.hero-inner {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  gap: 30px;
  padding: 32px 38px 28px;
}

.hero-copy {
  max-width: 620px;
}

.hero-copy h1 {
  font-size: clamp(32px, 3.4vw, 46px);
  line-height: 1.08;
  letter-spacing: -0.04em;
}

.brand-word {
  background: linear-gradient(120deg, #d89522 0%, #ffc65f 45%, #d96a4b 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  font-weight: 750;
}

.hero-subline {
  font-size: 0.43em;
  letter-spacing: -0.02em;
  color: #31556c;
  font-weight: 600;
}

.hero-copy h1 span {
  color: #31556c;
}

.hero-copy p {
  margin-top: 13px;
  max-width: 560px;
  color: #47687e;
  font-size: 12.5px;
  line-height: 1.7;
}

.hero-actions {
  margin-top: 20px;
  display: flex;
  gap: 9px;
  flex-wrap: wrap;
}

.hero-btn {
  background: rgba(255, 255, 255, 0.78);
  color: var(--text);
  border-color: rgba(160, 209, 233, 0.8);
  backdrop-filter: blur(8px);
}

.hero-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: space-between;
  min-width: 200px;
}

.hero-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 11px;
  border-radius: 999px;
  border: 1px solid rgba(160, 209, 233, 0.8);
  background: rgba(255, 255, 255, 0.78);
  font-size: 10.5px;
  color: var(--text);
  backdrop-filter: blur(10px);
}

.hero-metrics {
  display: flex;
  gap: 22px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgba(190, 226, 244, 0.8);
  background: rgba(255, 255, 255, 0.64);
  backdrop-filter: blur(10px);
}

.hero-metrics > div {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
}

.hero-metrics b {
  font-family: var(--mono);
  font-size: 22px;
  font-weight: 700;
  color: #0b4f6c;
  letter-spacing: -0.04em;
}

.hero-metrics span {
  font-size: 9.5px;
  color: #6f8fa3;
  letter-spacing: 0.06em;
}

.hero-note {
  font-size: 9px;
  color: #5b7b90;
  letter-spacing: 0.08em;
}

.launch-card {
  margin-top: 16px;
  overflow: hidden;
}

.launch-main {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px 22px;
}

.launch-icon {
  width: 46px;
  height: 46px;
  border-radius: 13px;
  display: grid;
  place-items: center;
  flex: none;
  color: var(--primary);
  background: rgba(14, 165, 233, 0.09);
  border: 1px solid rgba(14, 165, 233, 0.18);
}

.launch-icon.live {
  box-shadow: 0 0 0 1px rgba(14, 165, 233, 0.36), 0 0 30px rgba(14, 165, 233, 0.18);
  animation: pulse 2s ease-in-out infinite;
}

.launch-copy {
  flex: 1;
  min-width: 0;
}

.launch-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.launch-title-row h2 {
  font-size: 17px;
}

.launch-copy p {
  margin-top: 6px;
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.65;
  max-width: 720px;
}

.launch-meta {
  margin-top: 10px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.launch-actions {
  display: flex;
  flex-direction: column;
  gap: 7px;
  flex: none;
}

.launch-counters {
  display: flex;
  align-items: center;
  gap: 26px;
  padding: 12px 22px;
  border-top: 1px solid var(--border-soft);
  background: rgba(0, 0, 0, 0.18);
}

.launch-counters > div {
  display: flex;
  align-items: baseline;
  gap: 7px;
}

.launch-counters b {
  font-size: 15px;
  color: var(--primary);
  font-weight: 600;
}

.counter-live {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 10px;
  color: var(--primary);
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}

.feature-card {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 188px;
  padding: 18px;
  border-radius: 13px;
  border: 1px solid var(--border-soft);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.92));
  cursor: pointer;
  transition: border-color 0.16s ease, transform 0.16s ease;
}

.feature-card:hover {
  transform: translateY(-2px);
  border-color: #31455a;
}

.feature-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.feature-icon {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  display: grid;
  place-items: center;
}

.feature-card h3 {
  margin-top: 13px;
  font-size: 15px;
  letter-spacing: -0.02em;
}

.feature-card p {
  margin-top: 6px;
  font-size: 11.5px;
  line-height: 1.65;
  color: var(--muted);
}

.feature-foot {
  margin-top: auto;
  padding-top: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.feature-meta {
  font-size: 9.5px;
  color: var(--faint);
  font-family: var(--mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.feature-link {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  flex: none;
  font-size: 10px;
  color: var(--primary);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
  gap: 16px;
  margin-top: 16px;
}

.recent-list {
  padding: 8px 10px 12px;
}

.recent-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 8px;
  border-radius: 8px;
  border-bottom: 1px solid rgba(214, 234, 245, 0.55);
}

.recent-row:last-of-type {
  border-bottom: none;
}

.recent-row:hover {
  background: rgba(255, 255, 255, 0.03);
}

.recent-main {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  flex: 1;
}

.recent-name {
  font-size: 11.5px;
  color: var(--text-soft);
}

.recent-time {
  font-size: 9px;
  color: var(--faint);
}

.recent-duration {
  font-size: 9.5px;
  color: var(--muted);
  width: 66px;
  text-align: right;
}

.capability-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.capability-row {
  display: grid;
  grid-template-columns: 1fr 14px auto;
  align-items: center;
  gap: 9px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(214, 234, 245, 0.55);
  font-size: 10.5px;
  color: var(--muted);
}

.capability-row .mono {
  font-size: 9.5px;
  color: var(--text-soft);
}

.capability-note {
  margin-top: 12px;
  font-size: 9.5px;
  line-height: 1.6;
  color: var(--faint);
}

@media (max-width: 1120px) {
  .hero-inner {
    flex-direction: column;
  }
  .hero-side {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    width: 100%;
  }
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
