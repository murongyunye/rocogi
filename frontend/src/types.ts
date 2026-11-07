export type FieldType =
  | 'text'
  | 'textarea'
  | 'number'
  | 'boolean'
  | 'select'
  | 'expression'
  | 'resource'
  | 'target'

export interface NodeField {
  key: string
  label: string
  type: FieldType
  default: unknown
  options?: { value: string; label: string }[]
  placeholder?: string
  help?: string
  required?: boolean
  minimum?: number
  maximum?: number
  step?: number
  rows?: number
}

export interface NodePort {
  id: string
  label: string
  kind: string
}

export interface NodeContract {
  type: string
  title: string
  category: string
  categoryLabel?: string
  accent?: string
  description: string
  inputs: NodePort[]
  outputs: NodePort[]
  fields: NodeField[]
  tags: string[]
  icon: string
}

export interface GraphNode {
  id: string
  type: string
  x: number
  y: number
  config: Record<string, unknown>
  disabled?: boolean
  title?: string
  [key: string]: unknown
}

export interface GraphEdge {
  id: string
  from: string
  fromPort: string
  to: string
  toPort: string
}

export interface WorkflowGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
  subgraphs?: Record<string, unknown>
  variables?: Record<string, unknown>
}

export interface RunSummary {
  stats?: Record<string, unknown>
  vars?: Record<string, unknown>
  position?: Record<string, unknown>
  nodeOutputs?: Record<string, Record<string, unknown>>
  [key: string]: unknown
}

export interface Run {
  id: string
  workflowId: string
  workflowName: string
  status: 'running' | 'succeeded' | 'failed' | 'stopped'
  trigger: string
  startedAt: string
  finishedAt?: string
  durationMs: number
  error?: string
  summary: RunSummary
}

export interface Workflow {
  id: string
  name: string
  description: string
  graph: WorkflowGraph
  targetSlot: string
  tags: string[]
  revision: number
  createdAt: string
  updatedAt: string
  lastRun?: Run | null
  issues?: { level: string; message: string; node_id?: string }[]
}

export interface RunEvent {
  seq: number
  ts: string
  type: string
  nodeId?: string | null
  message: string
  data: Record<string, unknown>
  runId?: string
}

export interface Resource {
  id: string
  kind: string
  name: string
  tags: string[]
  data: Record<string, unknown>
  path?: string
  createdAt: string
}

export interface CategoryStat {
  id: string
  label: string
  count: number
  color?: string
}

export interface MapMeta {
  pointCount: number
  categoryCount: number
  labelCount: number
  categories: CategoryStat[]
  labels: CategoryStat[]
  mapWidth: number
  mapHeight: number
  baseMap: string
  markerTypeCount: number
}

export interface PoiPoint {
  id: string
  title: string
  label: string
  category: string
  markType: number
  x: number
  y: number
  source: string
  icon: string
}

export interface RoutePlan {
  start: { x: number; y: number }
  route: PoiPoint[]
  count: number
  distancePx: number
  estimatedMinutes: number
  labels: string[]
  categories: string[]
}

export interface Pokemon {
  id: number
  name: string
  element: string
  stage: string
  ability: string
  stats: Record<string, number>
}

export interface BattleTeamMember {
  name: string
  type: string
  hp: number
  maxHp: number
  energy: number
  fainted: boolean
  active: boolean
  skills: string[]
}

export interface BattleTurnLog {
  kind: string
  turn?: number
  a?: string
  b?: string
  hpA?: number
  hpB?: number
  deltaA?: number
  deltaB?: number
  text?: string
}

export interface BattleResult {
  ok: boolean
  error?: string
  winner?: string
  turns?: number
  durationMs?: number
  teamA?: BattleTeamMember[]
  teamB?: BattleTeamMember[]
  logs?: BattleTurnLog[]
  records?: { turn: number; teamA: BattleTeamMember[]; teamB: BattleTeamMember[] }[]
}

export interface AppSettings {
  target: {
    slot: string
    kind: string
    window_title: string
    capture_fps: number
    scale: number
  }
  input: { backend: string }
  engine: { max_steps: number; max_visits: number; step_delay_ms: number }
  vision: { threshold: number; use_edges: boolean; downscale: number }
  map: { position_source: string; sift_max_edge: number; cache_anchors: boolean; minimap_region?: number[] }
  battle: { simulations: number; max_turns: number }
  demo: { scene: string }
}

export interface AppMeta {
  version: string
  platform: {
    platform: string
    windows: boolean
    mock_target: boolean
    interception: boolean
    sift: boolean
    battle_ai: boolean
    data_dir: string
    engine: string
  }
  target: Record<string, unknown>
  settings: AppSettings
  workflowCount: number
  runCount: number
  map: MapMeta
  resources: number
  activeRuns: number
  realtime?: { running: boolean }
  tracker?: { running: boolean }
}

export interface RealtimeLog {
  ts: string
  kind: string
  message: string
}

export interface RealtimeStatus {
  running: boolean
  status: string
  error: string
  startedAt?: string
  scene: string
  phase?: string
  scores: Record<string, number>
  config: {
    interval: number
    auto_ball: boolean
    battle_response: boolean
    party_confirm: boolean
    normal_strategy: string
    polluted_strategy: string
    threshold: number
    save_screenshots: boolean
    capture_retries?: number
    capture_verify?: number
    capture_pan?: boolean
    capture_pan_steps?: number
    capture_pan_pixels?: number
  }
  capture?: {
    attempts: number
    emptyScans: number
    panCount: number
  }
  counters: {
    ticks: number
    actions: number
    battles: number
    balls: number
    confirms: number
  }
  latestUrl?: string | null
  logs: RealtimeLog[]
}

export interface TrackerStatus {
  running: boolean
  status: string
  error: string
  rebuilding: boolean
  config: {
    interval: number
    confidenceMin: number
    screenshotEvery: number
  }
  current?: {
    x: number
    y: number
    lat?: number
    lng?: number
    confidence?: number
    source?: string
  } | null
  trail: {
    x: number
    y: number
    lat?: number
    lng?: number
    confidence?: number
    ts: string
  }[]
  stats: {
    ticks: number
    located: number
    lost: number
    latencyMs: number
  }
  latestUrl?: string | null
  logs: RealtimeLog[]
  startedAt?: string
  anchor: {
    maxEdge?: number | null
    cached: boolean
    points: number
  }
}

export interface OneDragonTask {
  id: string
  name: string
  description: string
  defaults: Record<string, unknown>
}

export interface OneDragonPlanItem {
  id: string
  enabled: boolean
  config: Record<string, any>
}

export interface OneDragonPlan {
  loops: number
  tasks: OneDragonPlanItem[]
}
