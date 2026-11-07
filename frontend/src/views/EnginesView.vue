<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../lib/api'
import { appStore, refreshMeta } from '../lib/store'
import { notify } from '../lib/toast'

interface Preset {
  id: string
  name: string
  description: string
  tag: string
  settings: Record<string, any>
}

interface EngineData {
  applied: string
  presets: Preset[]
  current: Record<string, any>
  status: Record<string, any>
}

const data = ref<EngineData | null>(null)
const applying = ref('')

const engines = computed(() => {
  const current = data.value?.current || {}
  const status = data.value?.status || {}
  return [
    {
      id: 'capture',
      name: '截图引擎',
      icon: 'image',
      accent: '#0ea5e9',
      ok: status.capture?.ok,
      params: [
        ['目标类型', current.target?.kind === 'windows' ? 'Windows 窗口' : '模拟窗口'],
        ['窗口', current.target?.title || current.target?.error || '模拟窗口'],
        ['采帧率', `${current.capture?.capture_fps ?? 4} fps`],
        ['缩放', String(current.capture?.scale ?? 1)],
      ],
    },
    {
      id: 'vision',
      name: '视觉识别',
      icon: 'search',
      accent: '#7c3aed',
      ok: status.vision?.ok,
      params: [
        ['匹配阈值', String(current.vision?.threshold ?? 0.5)],
        ['边缘预处理', current.vision?.use_edges ? '开启' : '关闭'],
        ['降采样', String(current.vision?.downscale ?? 0.5)],
        ['模板数', String(status.vision?.templates ?? 0)],
      ],
    },
    {
      id: 'input',
      name: '输入引擎',
      icon: 'cpu',
      accent: '#ea580c',
      ok: status.input?.ok,
      params: [
        ['输入后端', current.input?.backend || 'mock'],
        ['平台支持', appStore.meta?.platform?.windows ? 'Windows' : '模拟'],
        ['坐标转换', 'ClientToScreen'],
        ['按键队列', '单步 / 连按'],
      ],
    },
    {
      id: 'sift',
      name: 'SIFT 定位',
      icon: 'target',
      accent: '#059669',
      ok: status.sift?.ok,
      params: [
        ['锚点最大边长', `${current.map?.sift_max_edge ?? 1600} px`],
        ['锚点缓存', current.map?.cache_anchors ? '开启' : '关闭'],
        ['锚点数量', String(status.sift?.anchors ?? 0)],
        ['小地图区域', (current.map?.minimap_region || []).join(', ') || '默认'],
      ],
    },
    {
      id: 'battle',
      name: '对战引擎',
      icon: 'battle',
      accent: '#db2777',
      ok: status.battle?.ok,
      params: [
        ['MCTS 模拟', String(current.battle?.simulations ?? 40)],
        ['最大回合', String(current.battle?.max_turns ?? 24)],
        ['精灵数据', '461'],
        ['技能数据', '491'],
      ],
    },
    {
      id: 'scheduler',
      name: '会话调度',
      icon: 'activity',
      accent: '#0891b2',
      ok: true,
      params: [
        ['实时任务间隔', `${current.realtime?.interval ?? 0.6}s`],
        ['实时阈值', String(current.realtime?.threshold ?? 0.45)],
        ['追踪间隔', `${current.tracker?.interval ?? 0.5}s`],
        ['步数 / 循环上限', `${current.engine?.max_steps ?? 1200} / ${current.engine?.max_visits ?? 80}`],
      ],
    },
  ]
})

async function load() {
  try {
    data.value = await api<EngineData>('/api/engines')
  } catch (error) {
    notify(`读取引擎参数失败：${error}`, 'error')
  }
}

async function applyPreset(preset: Preset) {
  applying.value = preset.id
  try {
    const result = await api<{ ok: boolean; name: string; target: Record<string, any> }>('/api/engines/apply', {
      method: 'POST',
      body: JSON.stringify({ presetId: preset.id }),
    })
    notify(`已应用「${result.name}」引擎预设`, 'success')
    await load()
    refreshMeta()
  } catch (error: any) {
    notify(`应用预设失败：${error?.payload?.detail || error}`, 'error')
  } finally {
    applying.value = ''
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <div class="eyebrow">Engine Configuration</div>
        <h1>引擎参数</h1>
        <p class="page-sub">
          截图、视觉、输入、SIFT、对战与调度引擎的参数集中在这里。选择预设即可一键套用到本机，也可以在设置页逐项微调。
        </p>
      </div>
      <div class="page-actions">
        <span class="chip primary">当前 {{ data?.applied || 'demo' }}</span>
        <button class="btn" @click="load"><AppIcon name="refresh" :size="14" /> 刷新</button>
      </div>
    </header>

    <div class="section-title">
      <h2>引擎预设</h2>
      <span class="hint">一键应用目标、输入、识别、定位与对战参数</span>
    </div>
    <div class="preset-grid">
      <article
        v-for="preset in data?.presets || []"
        :key="preset.id"
        class="preset-card"
        :class="{ active: data?.applied === preset.id }"
      >
        <div class="preset-head">
          <span class="chip">{{ preset.tag }}</span>
          <span v-if="data?.applied === preset.id" class="chip success">已应用</span>
        </div>
        <h3>{{ preset.name }}</h3>
        <p>{{ preset.description }}</p>
        <button class="btn" :class="data?.applied === preset.id ? '' : 'btn-primary'" :disabled="applying === preset.id" @click="applyPreset(preset)">
          {{ applying === preset.id ? '应用中...' : data?.applied === preset.id ? '重新应用' : '应用预设' }}
        </button>
      </article>
    </div>

    <div class="section-title" style="margin-top: 26px">
      <h2>当前引擎</h2>
      <span class="hint">参数来自本机设置，修改后立即生效</span>
    </div>
    <div class="engine-grid">
      <section v-for="engine in engines" :key="engine.id" class="panel engine-card">
        <div class="panel-head">
          <div class="panel-title">
            <span class="engine-icon" :style="{ color: engine.accent, background: `${engine.accent}14` }">
              <AppIcon :name="engine.icon" :size="16" />
            </span>
            {{ engine.name }}
          </div>
          <span class="status-dot" :class="engine.ok ? 'succeeded' : 'failed'" />
        </div>
        <div class="panel-body">
          <div v-for="[label, value] in engine.params" :key="label" class="engine-row">
            <span>{{ label }}</span>
            <span class="mono">{{ value }}</span>
          </div>
        </div>
      </section>
    </div>

    <div class="engine-note">
      <AppIcon name="spark" :size="14" />
      <span>
        Windows 实机预设会切换目标为游戏窗口并启用 SIFT；在模拟环境请使用「演示 / 模拟目标」预设。
      </span>
    </div>
  </div>
</template>

<style scoped>
.preset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 13px;
}

.preset-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
}

.preset-card:hover {
  transform: translateY(-1px);
  border-color: #a8d4e8;
  box-shadow: 0 12px 28px rgba(42, 108, 140, 0.08);
}

.preset-card.active {
  border-color: rgba(14, 165, 233, 0.4);
  background: rgba(240, 250, 255, 0.95);
  box-shadow: 0 0 0 1px rgba(14, 165, 233, 0.12);
}

.preset-head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.preset-card h3 {
  font-size: 14px;
  margin-top: 2px;
}

.preset-card p {
  font-size: 10.5px;
  line-height: 1.6;
  color: var(--muted);
  min-height: 50px;
}

.preset-card .btn {
  margin-top: auto;
  width: 100%;
}

.engine-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}

.engine-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: grid;
  place-items: center;
}

.engine-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 7px 0;
  border-bottom: 1px solid rgba(190, 220, 237, 0.45);
  font-size: 10.5px;
  color: var(--muted);
}

.engine-row:last-child {
  border-bottom: none;
}

.engine-row .mono {
  color: var(--text-soft);
  font-size: 9.5px;
  max-width: 62%;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.engine-note {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 18px;
  padding: 10px 13px;
  border-radius: 9px;
  border: 1px solid rgba(14, 165, 233, 0.16);
  background: rgba(14, 165, 233, 0.05);
  font-size: 10.5px;
  color: var(--muted);
}

.engine-note svg {
  color: var(--primary);
}
</style>
