import { createRouter, createWebHistory } from 'vue-router'

import WorkflowsView from './views/WorkflowsView.vue'
import WorkflowEditorView from './views/WorkflowEditorView.vue'
import RunsView from './views/RunsView.vue'
import RunDetailView from './views/RunDetailView.vue'
import ResourcesView from './views/ResourcesView.vue'
import MapView from './views/MapView.vue'
import BattleView from './views/BattleView.vue'
import SettingsView from './views/SettingsView.vue'
import LauncherView from './views/LauncherView.vue'
import OneDragonView from './views/OneDragonView.vue'
import RealtimeView from './views/RealtimeView.vue'
import TrackerView from './views/TrackerView.vue'
import EnginesView from './views/EnginesView.vue'
import HarnessView from './views/HarnessView.vue'
import ComponentsView from './views/ComponentsView.vue'
import DexView from './views/DexView.vue'
import PvpView from './views/PvpView.vue'
import PetView from './views/PetView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/launcher' },
    { path: '/launcher', component: LauncherView, meta: { title: '启动' } },
    { path: '/onedragon', component: OneDragonView, meta: { title: '一条龙' } },
    { path: '/realtime', component: RealtimeView, meta: { title: '实时任务' } },
    { path: '/tracker', component: TrackerView, meta: { title: '地图追踪' } },
    { path: '/workflows', component: WorkflowsView, meta: { title: '独立任务' } },
    { path: '/workflows/:id', component: WorkflowEditorView, meta: { title: '工作流编辑器' } },
    { path: '/runs', component: RunsView, meta: { title: '执行记录' } },
    { path: '/runs/:id', component: RunDetailView, meta: { title: '运行详情' } },
    { path: '/resources', component: ResourcesView, meta: { title: '资源库' } },
    { path: '/map', component: MapView, meta: { title: '资源地图' } },
    { path: '/battle', component: BattleView, meta: { title: '对战实验室' } },
    { path: '/settings', component: SettingsView, meta: { title: '设置' } },
    { path: '/engines', component: EnginesView, meta: { title: '引擎参数' } },
    { path: '/components', component: ComponentsView, meta: { title: '组件图谱' } },
    { path: '/dex', component: DexView, meta: { title: '图鉴速查' } },
    { path: '/pvp', component: PvpView, meta: { title: 'PvP 平衡实验室' } },
    { path: '/pet', component: PetView, meta: { title: '桌宠工坊' } },
    { path: '/harness', component: HarnessView, meta: { title: 'AI Harness' } },
  ],
})
