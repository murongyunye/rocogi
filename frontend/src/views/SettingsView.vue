<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../lib/api'
import { appStore, refreshMeta } from '../lib/store'
import { notify } from '../lib/toast'
import type { AppSettings } from '../types'

const settings = reactive<AppSettings>({
  target: { slot: 'nrc-game', kind: 'mock', window_title: '洛克王国：世界', capture_fps: 4, scale: 1 },
  input: { backend: 'mock' },
  engine: { max_steps: 1200, max_visits: 80, step_delay_ms: 0 },
  vision: { threshold: 0.5, use_edges: true, downscale: 0.5 },
  map: { position_source: 'mock', sift_max_edge: 1600, cache_anchors: true },
  battle: { simulations: 60, max_turns: 60 },
  demo: { scene: 'auto' },
})
const target = ref<Record<string, any>>({})
const saving = ref(false)
const loading = ref(true)
const demoScene = ref('auto')
const applyingScene = ref(false)

const platform = computed(() => appStore.meta?.platform)
const minimapRegionText = computed({
  get: () => (settings.map.minimap_region || [0.84, 0.0275, 0.1172, 0.1875]).join(', '),
  set: (value: string) => {
    const parts = value
      .split(',')
      .map((item) => Number(item.trim()))
      .filter((item) => Number.isFinite(item))
    if (parts.length === 4) settings.map.minimap_region = parts
  },
})
const scenes = [
  { value: 'auto', label: '自动轮播（推荐）' },
  { value: 'field_pet', label: '野外 · 可捕捉精灵' },
  { value: 'field', label: '野外 · 空视野（触发视角搜索）' },
  { value: 'battle_normal', label: '普通战斗' },
  { value: 'battle_polluted', label: '污染战斗' },
  { value: 'party_confirm', label: '同行请求' },
  { value: 'map', label: '地图' },
]

async function load() {
  try {
    const data = await api<{ settings: AppSettings; target: Record<string, any> }>('/api/settings')
    Object.assign(settings, data.settings)
    demoScene.value = settings.demo?.scene || 'auto'
    target.value = data.target
  } catch (error) {
    notify(`加载设置失败：${error}`, 'error')
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const data = await api<{ settings: AppSettings; target: Record<string, any> }>('/api/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    })
    Object.assign(settings, data.settings)
    target.value = data.target
    notify('设置已保存', 'success')
    refreshMeta()
  } catch (error) {
    notify(`保存失败：${error}`, 'error')
  } finally {
    saving.value = false
  }
}

async function applyScene() {
  applyingScene.value = true
  try {
    await api('/api/demo/scene', { method: 'POST', body: JSON.stringify({ scene: demoScene.value }) })
    settings.demo.scene = demoScene.value
    notify(`模拟窗口已切换到「${scenes.find((item) => item.value === demoScene.value)?.label}」`, 'success')
    refreshMeta()
  } catch (error) {
    notify(`切换失败：${error}`, 'error')
  } finally {
    applyingScene.value = false
  }
}

onMounted(async () => {
  await load()
  refreshMeta()
})
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <div class="eyebrow">Settings</div>
        <h1>设置</h1>
        <p class="page-sub">窗口、输入、识别与定位都绑定在本机。工作流只保存目标槽位，导入到另一台机器后重新绑定即可。</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary" :disabled="saving" @click="save">
          <AppIcon name="save" :size="14" /> {{ saving ? '保存中...' : '保存设置' }}
        </button>
      </div>
    </header>

    <div class="settings-grid">
      <section class="panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="target" :size="15" /> 游戏目标</div>
          <span class="chip" :class="target?.kind === 'windows' ? 'success' : 'primary'">{{ target?.kind === 'windows' ? 'Windows' : '模拟' }}</span>
        </div>
        <div class="panel-body">
          <div class="field">
            <div class="field-label">目标类型</div>
            <select v-model="settings.target.kind" class="select">
              <option value="mock">模拟窗口（无需游戏，适合演示）</option>
              <option value="windows">Windows 游戏窗口</option>
            </select>
            <div class="field-help">Windows 目标需要游戏已启动；模拟目标会生成可识别的合成画面。</div>
          </div>
          <div class="field">
            <div class="field-label">窗口标题关键词</div>
            <input v-model="settings.target.window_title" class="input" placeholder="洛克王国：世界" />
          </div>
          <div class="field-row">
            <div class="field">
              <div class="field-label">采集帧率</div>
              <input v-model.number="settings.target.capture_fps" type="number" min="1" max="30" class="input" />
            </div>
            <div class="field">
              <div class="field-label">缩放</div>
              <input v-model.number="settings.target.scale" type="number" min="0.5" max="2" step="0.05" class="input" />
            </div>
          </div>
          <div class="target-status">
            <span class="status-dot" :class="target?.kind === 'windows' ? 'succeeded' : 'running'" />
            <span>{{ target?.title || '模拟窗口' }}</span>
            <span v-if="target?.width" class="mono">{{ target.width }}×{{ target.height }}</span>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="cpu" :size="15" /> 输入后端</div>
          <span class="chip">{{ settings.input.backend }}</span>
        </div>
        <div class="panel-body">
          <div class="field">
            <div class="field-label">键鼠输入方式</div>
            <select v-model="settings.input.backend" class="select">
              <option value="mock">记录动作（不操作系统）</option>
              <option value="windows">Windows SendInput</option>
              <option value="interception">Interception 驱动（推荐实机）</option>
            </select>
            <div class="field-help">
              Interception 需要安装驱动与 <span class="mono">interception-python</span>，在驱动层模拟键鼠；不可用时请退回 SendInput。
            </div>
          </div>
          <div class="notice">
            <AppIcon name="warning" :size="14" />
            <span>在模拟目标下，所有键鼠动作只写入运行日志，不会影响当前系统。</span>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="search" :size="15" /> 视觉识别</div>
        </div>
        <div class="panel-body">
          <div class="field">
            <div class="field-label">默认匹配阈值 <span class="mono">{{ settings.vision.threshold.toFixed(2) }}</span></div>
            <input v-model.number="settings.vision.threshold" type="range" min="0.1" max="1" step="0.01" class="range" />
            <div class="field-help">阈值越高越严格，越低越容易误判。节点内可单独覆盖。</div>
          </div>
          <div class="toggle-row">
            <span class="field-label">Canny 边缘预处理</span>
            <div class="toggle" :class="{ on: settings.vision.use_edges }" @click="settings.vision.use_edges = !settings.vision.use_edges" />
          </div>
          <div class="field">
            <div class="field-label">识别降采样比例</div>
            <input v-model.number="settings.vision.downscale" type="number" min="0.25" max="1" step="0.05" class="input" />
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="crosshair" :size="15" /> 地图定位</div>
        </div>
        <div class="panel-body">
          <div class="field">
            <div class="field-label">定位源</div>
            <select v-model="settings.map.position_source" class="select">
              <option value="mock">模拟坐标</option>
              <option value="sift">SIFT 小地图识别</option>
            </select>
            <div class="field-help">SIFT 会从小地图截图中提取特征并与世界地图匹配，首次启动需要建立锚点缓存。</div>
          </div>
          <div class="field">
            <div class="field-label">锚点图像最大边长</div>
            <input v-model.number="settings.map.sift_max_edge" type="number" min="800" max="4096" step="128" class="input" />
          </div>
          <div class="field">
            <div class="field-label">小地图裁剪区域</div>
            <input v-model="minimapRegionText" class="input mono" placeholder="0.84, 0.0275, 0.1172, 0.1875" />
            <div class="field-help">左、上、宽、高比例；地图追踪与工作流定位都会使用该区域。</div>
          </div>
          <div class="toggle-row">
            <span class="field-label">缓存 SIFT 锚点</span>
            <div class="toggle" :class="{ on: settings.map.cache_anchors }" @click="settings.map.cache_anchors = !settings.map.cache_anchors" />
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="activity" :size="15" /> 运行引擎</div>
        </div>
        <div class="panel-body">
          <div class="field-row">
            <div class="field">
              <div class="field-label">最大步数</div>
              <input v-model.number="settings.engine.max_steps" type="number" min="100" max="10000" step="100" class="input" />
            </div>
            <div class="field">
              <div class="field-label">单节点循环上限</div>
              <input v-model.number="settings.engine.max_visits" type="number" min="5" max="500" step="5" class="input" />
            </div>
          </div>
          <div class="notice">
            <AppIcon name="route" :size="14" />
            <span>循环通过回边实现，引擎会在超过循环上限时停止运行，避免死循环。</span>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="battle" :size="15" /> 对战默认值</div>
        </div>
        <div class="panel-body">
          <div class="field-row">
            <div class="field">
              <div class="field-label">每回合模拟次数</div>
              <input v-model.number="settings.battle.simulations" type="number" min="10" max="300" step="10" class="input" />
            </div>
            <div class="field">
              <div class="field-label">最大回合</div>
              <input v-model.number="settings.battle.max_turns" type="number" min="4" max="80" step="1" class="input" />
            </div>
          </div>
          <div class="field-help">对战实验室与节点内可分别覆盖这里的默认值。</div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="panel" :size="15" /> 模拟窗口演示</div>
        </div>
        <div class="panel-body">
          <div class="field">
            <div class="field-label">当前演示场景</div>
            <select v-model="demoScene" class="select">
              <option v-for="scene in scenes" :key="scene.value" :value="scene.value">{{ scene.label }}</option>
            </select>
          </div>
          <button class="btn" style="margin-top: 12px" :disabled="applyingScene" @click="applyScene">
            <AppIcon name="refresh" :size="13" /> {{ applyingScene ? '切换中...' : '应用场景' }}
          </button>
          <div class="field-help" style="margin-top: 9px">
            切换后，模拟窗口的下一帧会进入指定场景，方便单独调试识别节点。
          </div>
        </div>
      </section>

      <section class="panel platform-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="cpu" :size="15" /> 运行环境</div>
          <span class="chip mono">v{{ appStore.meta?.version }}</span>
        </div>
        <div class="panel-body">
          <div class="meta-grid">
            <span class="meta-key">系统</span><span class="meta-val mono">{{ platform?.platform }}</span>
            <span class="meta-key">Windows</span><span class="meta-val mono">{{ platform?.windows ? '可用' : '不可用' }}</span>
            <span class="meta-key">SIFT</span><span class="meta-val mono">{{ platform?.sift ? '已启用' : '不可用' }}</span>
            <span class="meta-key">对战数据</span><span class="meta-val mono">{{ platform?.battle_ai ? '已加载' : '缺失' }}</span>
            <span class="meta-key">数据目录</span><span class="meta-val mono">{{ platform?.data_dir }}</span>
            <span class="meta-key">引擎</span><span class="meta-val mono">{{ platform?.engine }}</span>
          </div>
          <div class="notice" style="margin-top: 14px">
            <AppIcon name="warning" :size="14" />
            <span>使用真实游戏窗口前，请在 Windows 上安装 Interception 驱动并重启；桌面端需以管理员身份运行。</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
  align-items: start;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 15px;
}

.field-row .field + .field {
  margin-top: 0;
}

.range {
  width: 100%;
  height: 4px;
  appearance: none;
  background: linear-gradient(90deg, rgba(14, 165, 233, 0.5), rgba(14, 165, 233, 0.12));
  border-radius: 999px;
  outline: none;
  margin-top: 6px;
}

.range::-webkit-slider-thumb {
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--primary-2);
  border: 2px solid #082f49;
}

.target-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 9px 11px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
  font-size: 10.5px;
  color: var(--text-soft);
}

.target-status .mono {
  margin-left: auto;
  color: var(--faint);
}

.notice {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 14px;
  padding: 9px 11px;
  border-radius: 8px;
  border: 1px solid rgba(251, 191, 36, 0.16);
  background: rgba(251, 191, 36, 0.045);
  font-size: 10px;
  line-height: 1.55;
  color: #e8cf94;
}

.meta-grid {
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr);
  gap: 8px 10px;
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

@media (max-width: 900px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
