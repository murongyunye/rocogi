<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { api, assetUrl } from '../lib/api'
import { appStore, refreshMeta } from '../lib/store'
import { notify } from '../lib/toast'
import type { MapMeta, Resource } from '../types'

const router = useRouter()
const resources = ref<Resource[]>([])
const mapMeta = ref<MapMeta | null>(null)
const pokemonTotal = ref(0)
const tab = ref<'templates' | 'map' | 'data'>('templates')
const preview = ref<Resource | null>(null)
const loading = ref(true)

const templates = computed(() => resources.value.filter((resource) => resource.kind === 'template'))

const stats = computed(() => [
  { label: 'Templates', value: templates.value.length, hint: '视觉模板' },
  { label: 'POI', value: mapMeta.value?.pointCount ?? 0, hint: '地图点位' },
  { label: 'Marker Types', value: mapMeta.value?.markerTypeCount ?? 0, hint: '点位类型' },
  { label: 'Species', value: pokemonTotal.value, hint: '对战数据' },
])

async function load() {
  try {
    const [resourceList, meta, pokemon] = await Promise.all([
      api<Resource[]>('/api/resources'),
      api<MapMeta>('/api/map/meta'),
      api<{ total: number }>('/api/battle/pokemon?limit=1'),
    ])
    resources.value = resourceList
    mapMeta.value = meta
    pokemonTotal.value = pokemon.total
  } catch (error) {
    notify(`加载资源失败：${error}`, 'error')
  } finally {
    loading.value = false
  }
}

function openPreview(resource: Resource) {
  preview.value = resource
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
        <div class="eyebrow">Resource Library</div>
        <h1>资源库</h1>
        <p class="page-sub">视觉模板、地图点位与对战数据都在这里统一管理。资源属于本机，工作流只引用资源名称。</p>
      </div>
      <div class="page-actions">
        <button class="btn" @click="router.push('/map')">
          <AppIcon name="map" :size="14" /> 打开地图
        </button>
      </div>
    </header>

    <div class="stat-grid" style="margin-bottom: 24px">
      <div v-for="stat in stats" :key="stat.label" class="stat-cell">
        <div class="stat-label">{{ stat.label }}</div>
        <div class="stat-value">{{ stat.value }}<small>{{ stat.hint }}</small></div>
      </div>
    </div>

    <div class="tabs">
      <button class="tab" :class="{ active: tab === 'templates' }" @click="tab = 'templates'">
        <AppIcon name="image" :size="14" /> 视觉模板
        <span class="mono">{{ templates.length }}</span>
      </button>
      <button class="tab" :class="{ active: tab === 'map' }" @click="tab = 'map'">
        <AppIcon name="map" :size="14" /> 地图资源
      </button>
      <button class="tab" :class="{ active: tab === 'data' }" @click="tab = 'data'">
        <AppIcon name="database" :size="14" /> 数据来源
      </button>
    </div>

    <div v-if="loading" class="panel empty-state">正在加载资源...</div>

    <div v-else-if="tab === 'templates'" class="template-grid fade-list">
      <article v-for="resource in templates" :key="resource.id" class="template-card" @click="openPreview(resource)">
        <div class="template-image">
          <img :src="assetUrl((resource.data as any)?.url)" :alt="resource.name" loading="lazy" />
          <div class="template-overlay"><AppIcon name="search" :size="16" /></div>
        </div>
        <div class="template-info">
          <div class="template-name mono">{{ resource.name }}</div>
          <div class="template-tags">
            <span v-for="tag in resource.tags" :key="tag" class="chip" style="height: 20px; font-size: 9px">{{ tag }}</span>
          </div>
        </div>
      </article>
    </div>

    <div v-else-if="tab === 'map'" class="map-resource">
      <section class="panel map-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="map" :size="15" /> 世界地图底图</div>
          <span class="chip mono">6144 × 5888</span>
        </div>
        <div class="map-preview" @click="router.push('/map')">
          <img :src="'/api/assets/map/base_map.jpg'" alt="洛克王国世界地图" loading="lazy" />
          <div class="map-preview-overlay">
            <div class="map-preview-title">资源地图</div>
            <div class="map-preview-sub">{{ mapMeta?.pointCount }} 个点位 · {{ mapMeta?.categoryCount }} 个分类 · 点击进入</div>
          </div>
        </div>
      </section>

      <section class="panel category-panel">
        <div class="panel-head">
          <div class="panel-title"><AppIcon name="filter" :size="15" /> 资源分类</div>
        </div>
        <div class="panel-body category-list">
          <div v-for="category in mapMeta?.categories || []" :key="category.id" class="category-row">
            <span class="cat-dot" :style="{ background: category.color }" />
            <span class="cat-name">{{ category.label }}</span>
            <span class="cat-count mono">{{ category.count }}</span>
          </div>
        </div>
      </section>
    </div>

    <div v-else class="source-grid fade-list">
      <section class="panel source-card">
        <div class="source-icon"><AppIcon name="image" :size="18" /></div>
        <h3>视觉模板</h3>
        <p>战斗、污染、丢球、同行确认等界面元素来自 RocoPilot / Auto-Roco 的模板库，使用 OpenCV 边缘模板匹配。</p>
        <span class="chip">MIT · 9 个模板</span>
      </section>
      <section class="panel source-card">
        <div class="source-icon"><AppIcon name="map" :size="18" /></div>
        <h3>地图点位</h3>
        <p>点位与图标来自 roco-map-tracker 的 Easy-Roco / TapTap 社区地图数据，底座来自洛克王国世界 Wiki。</p>
        <span class="chip">{{ mapMeta?.pointCount }} 点位 · {{ mapMeta?.markerTypeCount }} 类型</span>
      </section>
      <section class="panel source-card">
        <div class="source-icon"><AppIcon name="battle" :size="18" /></div>
        <h3>对战数据</h3>
        <p>精灵、技能、特性与效果数据来自 NRC_AI 的 SQLite 数据库，内置对抗式 MCTS 决策引擎。</p>
        <span class="chip">{{ pokemonTotal }} 精灵 · 491 技能</span>
      </section>
      <section class="panel source-card">
        <div class="source-icon"><AppIcon name="crosshair" :size="18" /></div>
        <h3>地图定位</h3>
        <p>定位算法参考 luoke_location 的 SIFT 小地图跟踪方案，本地缓存锚点，不读取游戏内存。</p>
        <span class="chip">SIFT · 锚点缓存</span>
      </section>
      <section class="panel source-card">
        <div class="source-icon"><AppIcon name="workflow" :size="18" /></div>
        <h3>工作台蓝图</h3>
        <p>工作流、节点契约、目标绑定、资源库与运行证据的产品结构来自 yottaapp/yotta，以本地优先工作台为蓝图。</p>
        <span class="chip">Workflow · Node Contract</span>
      </section>
      <section class="panel source-card">
        <div class="source-icon"><AppIcon name="upload" :size="18" /></div>
        <h3>数据目录</h3>
        <p>所有资源保存在 <span class="mono">data/</span>，运行记录在 <span class="mono">runtime/</span>。可通过替换目录在本地更新数据。</p>
        <span class="chip mono">local-first</span>
      </section>
    </div>

    <div v-if="preview" class="dialog-backdrop" @click.self="preview = null">
      <div class="preview-dialog">
        <div class="preview-head">
          <div>
            <div class="preview-name mono">{{ preview.name }}</div>
            <div class="preview-path">{{ preview.path }}</div>
          </div>
          <button class="icon-btn" @click="preview = null"><AppIcon name="close" :size="15" /></button>
        </div>
        <div class="preview-image">
          <img :src="assetUrl((preview.data as any)?.url)" :alt="preview.name" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 4px;
  padding: 4px;
  width: fit-content;
  border: 1px solid var(--border-soft);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.02);
  margin-bottom: 18px;
}

.tab {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 12px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  font-size: 11.5px;
}

.tab:hover {
  color: var(--text);
}

.tab.active {
  background: rgba(14, 165, 233, 0.1);
  color: var(--primary);
}

.tab .mono {
  font-size: 9px;
  opacity: 0.7;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
}

.template-card {
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.9);
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.16s ease, transform 0.16s ease;
}

.template-card:hover {
  border-color: #31455a;
  transform: translateY(-2px);
}

.template-image {
  position: relative;
  height: 132px;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at 50% 40%, rgba(14, 165, 233, 0.06), transparent 65%),
    repeating-conic-gradient(rgba(255, 255, 255, 0.025) 0% 25%, transparent 0% 50%) 50% / 18px 18px;
}

.template-image img {
  max-width: 74%;
  max-height: 74%;
  image-rendering: auto;
  filter: drop-shadow(0 8px 18px rgba(0, 0, 0, 0.5));
}

.template-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--primary);
  background: rgba(255, 255, 255, 0.42);
  opacity: 0;
  transition: opacity 0.16s ease;
}

.template-card:hover .template-overlay {
  opacity: 1;
}

.template-info {
  padding: 10px 12px;
  border-top: 1px solid var(--border-soft);
}

.template-name {
  font-size: 10.5px;
  color: var(--text-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-tags {
  margin-top: 6px;
  display: flex;
  gap: 4px;
}

.map-resource {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
}

.map-panel {
  overflow: hidden;
}

.map-preview {
  position: relative;
  height: 420px;
  overflow: hidden;
  cursor: pointer;
}

.map-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.82;
  filter: saturate(0.85);
  transition: transform 0.5s ease, opacity 0.3s ease;
}

.map-preview:hover img {
  transform: scale(1.03);
  opacity: 1;
}

.map-preview::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 40%, rgba(255, 255, 255, 0.9));
}

.map-preview-overlay {
  position: absolute;
  left: 20px;
  bottom: 20px;
  z-index: 1;
}

.map-preview-title {
  font-size: 18px;
  font-weight: 650;
  letter-spacing: -0.02em;
}

.map-preview-sub {
  margin-top: 4px;
  font-size: 11px;
  color: var(--muted);
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 420px;
  overflow: auto;
}

.category-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 7px 6px;
  border-radius: 6px;
}

.category-row:hover {
  background: rgba(255, 255, 255, 0.03);
}

.cat-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.cat-name {
  font-size: 11.5px;
  color: var(--text-soft);
}

.cat-count {
  margin-left: auto;
  font-size: 9.5px;
  color: var(--faint);
}

.source-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.source-card {
  padding: 18px;
}

.source-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: var(--primary);
  background: rgba(14, 165, 233, 0.12);
  border: 1px solid rgba(14, 165, 233, 0.14);
  margin-bottom: 12px;
}

.source-card h3 {
  font-size: 14px;
}

.source-card p {
  margin-top: 7px;
  font-size: 11px;
  line-height: 1.65;
  color: var(--muted);
  min-height: 54px;
}

.source-card .chip {
  margin-top: 10px;
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  place-items: center;
  background: rgba(3, 6, 10, 0.7);
  backdrop-filter: blur(8px);
}

.preview-dialog {
  width: min(640px, calc(100vw - 48px));
  border: 1px solid var(--border);
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 30px 100px rgba(0, 0, 0, 0.65);
  overflow: hidden;
}

.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-soft);
}

.preview-name {
  font-size: 12px;
}

.preview-path {
  margin-top: 3px;
  font-size: 9.5px;
  color: var(--faint);
}

.preview-image {
  padding: 26px;
  display: grid;
  place-items: center;
  background: repeating-conic-gradient(rgba(255, 255, 255, 0.02) 0% 25%, transparent 0% 50%) 50% / 22px 22px;
}

.preview-image img {
  max-width: 100%;
  max-height: 60vh;
}

.icon-btn {
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--faint);
}

.icon-btn:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.05);
}

@media (max-width: 1020px) {
  .map-resource {
    grid-template-columns: 1fr;
  }
}
</style>
