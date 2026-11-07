<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../lib/api'
import { notify } from '../lib/toast'

const manifest = ref<any>(null)
const toolData = ref<any>(null)
const observation = ref<any>(null)
const observing = ref(false)
const copied = ref('')

const baseUrl = computed(() => window.location.origin)
const tools = computed(() => toolData.value?.tools || [])
const state = computed(() => manifest.value?.state || {})

async function load() {
  try {
    const [man, tool] = await Promise.all([api<any>('/api/harness/manifest'), api<any>('/api/harness/tools')])
    manifest.value = man
    toolData.value = tool
  } catch (error) {
    notify(`读取 Harness 信息失败：${error}`, 'error')
  }
}

async function observe() {
  observing.value = true
  try {
    const result = await api<any>('/api/harness/act', {
      method: 'POST',
      body: JSON.stringify({ action: 'observe' }),
    })
    observation.value = result.result
    toastInfo('已获取最新观察')
  } catch (error) {
    notify(`观察失败：${error}`, 'error')
  } finally {
    observing.value = false
  }
}

function toastInfo(message: string) {
  notify(message, 'success')
}

async function copy(text: string, key: string) {
  try {
    await navigator.clipboard.writeText(text)
    copied.value = key
    window.setTimeout(() => (copied.value = ''), 1500)
    toastInfo('已复制')
  } catch {
    notify('复制失败，请手动选择文本', 'error')
  }
}

function toolName(item: any): string {
  return item.function?.name || item.name || ''
}

function toolDesc(item: any): string {
  return item.function?.description || item.description || ''
}

function toolParams(item: any): number {
  return Object.keys(item.function?.parameters?.properties || item.parameters?.properties || {}).length
}

const quickstart = computed(
  () => `# 1. 读取 manifest\ncurl ${baseUrl.value}/api/harness/manifest\n\n# 2. 观察画面\ncurl -X POST ${baseUrl.value}/api/harness/act \\\n  -H 'Content-Type: application/json' \\\n  -d '{"action":"observe"}'\n\n# 3. 执行动作\ncurl -X POST ${baseUrl.value}/api/harness/act \\\n  -H 'Content-Type: application/json' \\\n  -d '{"action":"press_key","params":{"key":"x"}}'`,
)

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <div class="eyebrow">DeepSeek Harness Gateway</div>
        <div class="title-row">
          <h1>AI Harness</h1>
          <span class="chip primary">本地 · 无鉴权</span>
          <span class="status-dot succeeded" />
          <span class="chip mono">v{{ manifest?.version || '0.4.0' }}</span>
        </div>
        <p class="page-sub">
          DeepSeek Harness 或任意 agent 通过 HTTP 接管 Rocogi：读取 manifest、观察场景、按键/点击、运行工作流、查询运行证据，无需了解内部节点。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn" @click="copy(JSON.stringify(manifest, null, 2), 'manifest')">
          <AppIcon name="copy" :size="14" /> 复制 Manifest
        </button>
        <button class="btn btn-primary" :disabled="observing" @click="observe">
          <AppIcon name="crosshair" :size="14" /> {{ observing ? '观察中...' : '观察一次' }}
        </button>
      </div>
    </header>

    <div class="harness-layout">
      <section class="panel access-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="external" :size="15" /> 接入信息</div>
          <span class="chip mono">HTTP JSON</span>
        </div>
        <div class="panel-body">
          <div class="endpoint-row">
            <span class="endpoint-label">Base URL</span>
            <span class="endpoint-value mono">{{ baseUrl }}</span>
            <button class="mini-btn" @click="copy(baseUrl, 'base')">{{ copied === 'base' ? '已复制' : '复制' }}</button>
          </div>
          <div class="endpoint-row">
            <span class="endpoint-label">Manifest</span>
            <span class="endpoint-value mono">/api/harness/manifest</span>
            <button class="mini-btn" @click="copy(baseUrl + '/api/harness/manifest', 'manifestUrl')">{{ copied === 'manifestUrl' ? '已复制' : '复制' }}</button>
          </div>
          <div class="endpoint-row">
            <span class="endpoint-label">Tools</span>
            <span class="endpoint-value mono">/api/harness/tools</span>
            <button class="mini-btn" @click="copy(baseUrl + '/api/harness/tools', 'toolsUrl')">{{ copied === 'toolsUrl' ? '已复制' : '复制' }}</button>
          </div>
          <div class="endpoint-row">
            <span class="endpoint-label">Act</span>
            <span class="endpoint-value mono">POST /api/harness/act</span>
          </div>

          <div class="state-grid">
            <div><span class="stat-label">目标</span><b class="mono">{{ state.target?.kind === 'windows' ? 'Windows' : 'Mock' }}</b></div>
            <div><span class="stat-label">引擎预设</span><b class="mono">{{ state.enginePreset }}</b></div>
            <div><span class="stat-label">工作流</span><b class="mono">{{ state.workflows }}</b></div>
            <div><span class="stat-label">活动运行</span><b class="mono">{{ state.activeRuns }}</b></div>
          </div>

          <div class="prompt-head">
            <span class="panel-title"><AppIcon name="spark" :size="14" /> 系统提示词</span>
            <button class="mini-btn" @click="copy(manifest?.systemPrompt || '', 'prompt')">{{ copied === 'prompt' ? '已复制' : '复制' }}</button>
          </div>
          <pre class="prompt-block">{{ manifest?.systemPrompt }}</pre>

          <div class="quick-head">
            <span class="panel-title"><AppIcon name="route" :size="14" /> 三步接入</span>
            <button class="mini-btn" @click="copy(quickstart, 'quick')">{{ copied === 'quick' ? '已复制' : '复制' }}</button>
          </div>
          <pre class="code-block">{{ quickstart }}</pre>
        </div>
      </section>

      <section class="panel observe-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="image" :size="15" /> 最新观察</div>
          <span class="chip">{{ observation ? observation.scene?.kind : '尚未观察' }}</span>
        </div>
        <div class="panel-body">
          <div v-if="observation" class="observe-content">
            <img :src="observation.screenshot" alt="Harness observation" class="observe-image" />
            <div class="observe-grid">
              <div><span class="stat-label">Scene</span><b class="mono">{{ observation.scene?.kind }}</b></div>
              <div><span class="stat-label">Position</span><b class="mono">{{ Math.round(observation.position?.x || 0) }}, {{ Math.round(observation.position?.y || 0) }}</b></div>
              <div><span class="stat-label">实时任务</span><b class="mono">{{ observation.sessions?.realtime }}</b></div>
              <div><span class="stat-label">地图追踪</span><b class="mono">{{ observation.sessions?.tracker }}</b></div>
            </div>
            <div class="score-list">
              <div v-for="(score, key) in observation.scene?.scores || {}" :key="key" class="score-row">
                <span class="mono">{{ key }}</span>
                <div class="score-track"><span :style="{ width: `${Math.round(Number(score) * 100)}%` }" /></div>
                <span class="mono">{{ Number(score).toFixed(3) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="observe-empty">
            <div class="observe-icon"><AppIcon name="crosshair" :size="26" /></div>
            <div>点击「观察一次」后，这里会显示截图、场景分类、坐标与模板分数。</div>
            <div class="faint mono">{{ 'POST /api/harness/act {"action":"observe"}' }}</div>
          </div>
        </div>
      </section>
    </div>

    <section class="panel tools-panel">
      <div class="panel-head">
        <div class="panel-title"><AppIcon name="workflow" :size="15" /> 工具列表</div>
        <span class="chip mono">{{ tools.length }} tools · OpenAI schema</span>
      </div>
      <div class="panel-body">
        <div class="tool-grid">
          <article v-for="item in tools" :key="toolName(item)" class="tool-card">
            <div class="tool-head">
              <span class="tool-name mono">{{ toolName(item) }}</span>
              <span class="chip">{{ toolParams(item) }} params</span>
            </div>
            <p>{{ toolDesc(item) }}</p>
          </article>
        </div>
      </div>
    </section>

    <div class="harness-note">
      <AppIcon name="warning" :size="14" />
      <span>
        Harness 接口默认只监听本机、无鉴权；请勿直接暴露到公网。完整接入说明：
        <a href="/docs/deepseek-harness.md" target="_blank">docs/deepseek-harness.md</a>
      </span>
    </div>
  </div>
</template>

<style scoped>
.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.harness-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.endpoint-row {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr) 46px;
  align-items: center;
  gap: 8px;
  padding: 7px 0;
  border-bottom: 1px solid rgba(190, 220, 237, 0.45);
}

.endpoint-label {
  font-size: 9.5px;
  color: var(--faint);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.endpoint-value {
  font-size: 10px;
  color: var(--text-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mini-btn {
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: 9px;
  padding: 0;
  text-align: right;
}

.mini-btn:hover {
  text-decoration: underline;
}

.state-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 14px;
  padding: 12px;
  border-radius: 9px;
  background: rgba(14, 165, 233, 0.04);
  border: 1px solid rgba(14, 165, 233, 0.1);
}

.state-grid b {
  display: block;
  margin-top: 2px;
  font-size: 13px;
  color: var(--text-soft);
}

.prompt-head,
.quick-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  margin-bottom: 7px;
}

.prompt-block,
.code-block {
  margin: 0;
  padding: 11px 12px;
  border-radius: 9px;
  border: 1px solid var(--border-soft);
  background: #f7fcff;
  color: #31556c;
  font-family: var(--mono);
  font-size: 9.5px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 170px;
  overflow: auto;
}

.code-block {
  max-height: 210px;
}

.observe-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.observe-image {
  width: 100%;
  border-radius: 10px;
  border: 1px solid var(--border-soft);
  display: block;
  background: var(--panel-3);
}

.observe-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.observe-grid b {
  display: block;
  margin-top: 2px;
  font-size: 12.5px;
  color: var(--text-soft);
}

.score-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.score-row {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr) 44px;
  align-items: center;
  gap: 8px;
  font-size: 9px;
  color: var(--muted);
}

.score-track {
  height: 4px;
  border-radius: 999px;
  background: rgba(14, 165, 233, 0.1);
  overflow: hidden;
}

.score-track span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--primary-2), var(--primary));
}

.score-row .mono:last-child {
  text-align: right;
  color: var(--faint);
}

.observe-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  min-height: 340px;
  text-align: center;
  color: var(--muted);
  font-size: 11px;
  padding: 20px;
}

.observe-icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  color: var(--primary);
  background: rgba(14, 165, 233, 0.07);
  border: 1px solid rgba(14, 165, 233, 0.14);
}

.tools-panel {
  margin-top: 16px;
}

.tool-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 10px;
}

.tool-card {
  padding: 12px;
  border: 1px solid var(--border-soft);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.6);
}

.tool-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.tool-name {
  font-size: 10px;
  color: var(--primary);
}

.tool-card p {
  margin-top: 6px;
  font-size: 10px;
  line-height: 1.55;
  color: var(--muted);
}

.harness-note {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 10px 13px;
  border-radius: 9px;
  border: 1px solid rgba(217, 119, 6, 0.15);
  background: rgba(251, 191, 36, 0.07);
  font-size: 10.5px;
  color: #8a5a10;
}

.harness-note a {
  color: var(--primary);
  text-decoration: underline;
}

@media (max-width: 1150px) {
  .harness-layout {
    grid-template-columns: 1fr;
  }
}
</style>
