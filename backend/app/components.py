"""Engine component registry.

Rocogi follows the layering used by SCH-CMYK/game-automation:

    engine (components)  ->  automation / features (subsets)  ->  sessions

A feature never owns a whole engine. It picks the components it needs, and the
same component is re-used by as many features as want it. This module keeps
that contract in one place so the API and the UI can show the reuse graph.
"""

from __future__ import annotations

from typing import Any, Dict, List


ENGINES: List[Dict[str, Any]] = [
    {
        "id": "capture",
        "name": "截图引擎",
        "icon": "image",
        "accent": "#0ea5e9",
        "layer": "engine · 感知",
        "summary": "把窗口、模拟场景统一成带时间戳的帧，供其余引擎消费。",
        "source": "backend/app/adapters/{mock,frame}.py",
        "components": [
            {
                "id": "capture.mock_window",
                "name": "模拟窗口",
                "detail": "合成采集/战斗/小地图场景，离线也能跑完整闭环。",
                "code": "adapters/mock.py::MockGameTarget",
            },
            {
                "id": "capture.windows_window",
                "name": "Windows 窗口捕获",
                "detail": "按窗口标题抓取客户区，失败时回退桌面区域。",
                "code": "adapters/mock.py::WindowsGameTarget",
            },
            {
                "id": "capture.frame_digest",
                "name": "帧摘要",
                "detail": "统一尺寸、时间戳、缩略图与场景元数据。",
                "code": "adapters/frame.py::Frame",
            },
            {
                "id": "capture.scene_switch",
                "name": "演示场景切换",
                "detail": "自动 / 采集 / 战斗 / 小地图四种演示态。",
                "code": "services.py::set_scene",
            },
            {
                "id": "capture.foreground",
                "name": "窗口前台与焦点",
                "detail": "查找窗口、从最小化恢复并置前，保证截图与输入落在游戏窗口。",
                "code": "adapters/window.py::ensure_foreground",
            },
        ],
    },
    {
        "id": "vision",
        "name": "视觉识别",
        "icon": "search",
        "accent": "#7c3aed",
        "layer": "engine · 感知",
        "summary": "模板匹配与场景分类，把像素翻译成可判断的语义。",
        "source": "backend/app/adapters/vision.py",
        "components": [
            {
                "id": "vision.template_match",
                "name": "模板匹配",
                "detail": "多尺度 matchTemplate，返回坐标、分数与阈值判定。",
                "code": "adapters/vision.py::match_template",
            },
            {
                "id": "vision.edge_preprocess",
                "name": "边缘预处理",
                "detail": "灰度 / Canny / 降采样，提升低对比 UI 的稳定性。",
                "code": "adapters/vision.py::preprocess",
            },
            {
                "id": "vision.scene_classify",
                "name": "场景分类",
                "detail": "汇总区域分数，归类为采集、战斗、小地图等场景。",
                "code": "adapters/vision.py::classify_scene",
            },
            {
                "id": "vision.roi",
                "name": "ROI 解析",
                "detail": "归一化区域与像素区域互转，供模板与小地图裁剪复用。",
                "code": "adapters/vision.py::resolve_roi",
            },
            {
                "id": "vision.sprite_detector",
                "name": "精灵候选检测",
                "detail": "优先加载 ONNX 模型；无模型时用轮廓/模板回退，输出候选框。",
                "code": "adapters/detector.py::SpriteDetector",
            },
            {
                "id": "vision.ocr",
                "name": "数字与文本 OCR",
                "detail": "内置数字/百分比识别；安装 Tesseract 后支持中英文通用文本。",
                "code": "adapters/ocr.py::read_text",
            },
        ],
    },
    {
        "id": "input",
        "name": "输入引擎",
        "icon": "cpu",
        "accent": "#ea580c",
        "layer": "engine · 执行",
        "summary": "同一套按键语义，可在模拟、SendInput、驱动层三种后端间切换。",
        "source": "backend/app/adapters/input.py",
        "components": [
            {
                "id": "input.mock",
                "name": "模拟输入",
                "detail": "只记录按键与点击，不触碰操作系统，用于回放与测试。",
                "code": "adapters/input.py::MockInput",
            },
            {
                "id": "input.sendinput",
                "name": "SendInput",
                "detail": "系统级键鼠事件，兼容性优先，无需额外驱动。",
                "code": "adapters/input.py::WindowsInput",
            },
            {
                "id": "input.interception",
                "name": "Interception",
                "detail": "驱动层注入，适合高节奏采集与连续移动。",
                "code": "adapters/input.py::InterceptionInput",
            },
            {
                "id": "input.key_queue",
                "name": "按键队列",
                "detail": "按住时长、连按次数、随机抖动与客户区坐标换算。",
                "code": "adapters/input.py::create_input",
            },
            {
                "id": "input.hotkey",
                "name": "全局热键",
                "detail": "Windows RegisterHotKey，F9 启动实时、F10 停止、F11 切换追踪。",
                "code": "hotkeys.py::HotkeyManager",
            },
        ],
    },
    {
        "id": "sift",
        "name": "SIFT 定位",
        "icon": "target",
        "accent": "#059669",
        "layer": "engine · 定位",
        "summary": "不读内存，仅用小地图特征点匹配大地图完成实时定位。",
        "source": "backend/app/adapters/{position,mapdata}.py",
        "components": [
            {
                "id": "sift.minimap_region",
                "name": "小地图区域",
                "detail": "归一化裁剪 + 椭圆掩膜，隔离小地图外的 UI 干扰。",
                "code": "adapters/position.py::SiftPositionSource",
            },
            {
                "id": "sift.features",
                "name": "SIFT 特征",
                "detail": "地图端 6000 特征点，帧端按掩膜实时提取。",
                "code": "adapters/position.py::SiftPositionSource._load_map",
            },
            {
                "id": "sift.anchor_index",
                "name": "锚点索引",
                "detail": "按最大边长缓存地图锚点到 runtime/cache。",
                "code": "adapters/position.py::SiftPositionSource._cache_path",
            },
            {
                "id": "sift.homography",
                "name": "单应性定位",
                "detail": "Lowe 比值筛选 + RANSAC 内点校验，输出地图坐标。",
                "code": "adapters/position.py::SiftPositionSource.locate",
            },
            {
                "id": "sift.trajectory",
                "name": "轨迹重建",
                "detail": "会话内轨迹缓冲、置信度过滤与丢失重定位。",
                "code": "sessions.py::TrackerSession",
            },
            {
                "id": "sift.kalman_tracker",
                "name": "卡尔曼与多目标追踪",
                "detail": "位置平滑、跳变重置；精灵候选按 IoU 关联并保持稳定 ID。",
                "code": "adapters/tracking.py::MultiTargetTracker",
            },
            {
                "id": "sift.route_plan",
                "name": "路线规划",
                "detail": "按点位最近邻排序并拼接可执行路线。",
                "code": "services.py::plan_route",
            },
            {
                "id": "sift.external_tracker",
                "name": "外置 SIFT Map Tracker",
                "detail": "v0.10.2 WPF 客户端 + 自包含 service.exe，可选 Windows 包。",
                "code": "optional/sift-tracker/",
            },
        ],
    },
    {
        "id": "battle",
        "name": "对战引擎",
        "icon": "battle",
        "accent": "#db2777",
        "layer": "engine · 决策",
        "summary": "以 NRC_AI 数据与 MCTS 搜索回答“这一回合出什么”。",
        "source": "backend/app/adapters/battle.py",
        "components": [
            {
                "id": "battle.dataset",
                "name": "精灵 / 技能库",
                "detail": "461 精灵、491 技能的本地 SQLite 数据。",
                "code": "vendor/nrc_ai/data/nrc.db",
            },
            {
                "id": "battle.team_builder",
                "name": "队伍预设",
                "detail": "读取预设队伍并生成双方初始快照。",
                "code": "adapters/battle.py::BattleLab.presets",
            },
            {
                "id": "battle.mcts",
                "name": "MCTS 决策",
                "detail": "可配置模拟次数与回合上限，输出最优动作序列。",
                "code": "adapters/battle.py::BattleLab.decide",
            },
            {
                "id": "battle.damage_model",
                "name": "伤害与效果模型",
                "detail": "技能效果扁平化，统一供模拟与响应使用。",
                "code": "adapters/battle.py::flatten_effects",
            },
            {
                "id": "battle.turn_state",
                "name": "战斗回合状态识别",
                "detail": "读取敌方血条、回合数、技能可用性与污染状态，输出结构化状态。",
                "code": "adapters/turn_state.py::read_turn_state",
            },
            {
                "id": "battle.responder",
                "name": "战斗响应",
                "detail": "实时会话检测到战斗后自动调用决策链。",
                "code": "sessions.py::RealtimeSession",
            },
        ],
    },
    {
        "id": "scheduler",
        "name": "调度引擎",
        "icon": "activity",
        "accent": "#0891b2",
        "layer": "engine · 编排",
        "summary": "把组元编成 DAG、会话循环或一条龙计划，并统一推送事件。",
        "source": "backend/app/engine + sessions.py",
        "components": [
            {
                "id": "scheduler.dag",
                "name": "DAG 编译",
                "detail": "23 种节点契约、环检测与执行顺序计算。",
                "code": "engine/compiler.py::compile_graph",
            },
            {
                "id": "scheduler.executor",
                "name": "节点执行器",
                "detail": "执行节点、维护变量环境、输出截图证据。",
                "code": "engine/runtime.py::Runtime",
            },
            {
                "id": "scheduler.branch",
                "name": "条件分支",
                "detail": "branch 节点按表达式选择后继路径。",
                "code": "engine/runtime.py::Runtime._run_branch",
            },
            {
                "id": "scheduler.foreach",
                "name": "循环遍历",
                "detail": "foreach 节点按列表迭代并聚合结果。",
                "code": "engine/runtime.py::Runtime._run_foreach",
            },
            {
                "id": "scheduler.subgraph",
                "name": "子图调用",
                "detail": "workflow.call 复用另一张工作流图。",
                "code": "engine/runtime.py::Runtime._run_workflow_call",
            },
            {
                "id": "scheduler.event_bus",
                "name": "事件总线",
                "detail": "seq 事件持久化 + WebSocket 实时回放。",
                "code": "run_manager.py::RunManager",
            },
            {
                "id": "scheduler.session_loop",
                "name": "会话循环",
                "detail": "实时任务 / 地图追踪的周期线程与状态机。",
                "code": "sessions.py::RealtimeSession",
            },
            {
                "id": "scheduler.capture_fsm",
                "name": "捕捉状态机",
                "detail": "扫描→丢球→验证→重试，空视野平移搜索（AutoCapture 参考）。",
                "code": "sessions.py::RealtimeSession._run",
            },
            {
                "id": "scheduler.onedragon_plan",
                "name": "一条龙计划",
                "detail": "任务开关、顺序与共享参数。",
                "code": "onedragon.py::load_plan",
            },
        ],
    },
]


FEATURES: List[Dict[str, Any]] = [
    {
        "id": "onedragon",
        "name": "一条龙",
        "route": "/onedragon",
        "icon": "activity",
        "accent": "#0ea5e9",
        "summary": "从启动游戏到日常收尾的全流程编排，只取需要的感知、输入、对战与调度组元。",
        "components": [
            "capture.mock_window",
            "capture.windows_window",
            "capture.frame_digest",
            "vision.template_match",
            "vision.edge_preprocess",
            "vision.scene_classify",
            "input.mock",
            "input.sendinput",
            "input.interception",
            "input.key_queue",
            "battle.dataset",
            "battle.team_builder",
            "battle.mcts",
            "battle.damage_model",
            "battle.responder",
            "battle.turn_state",
            "capture.foreground",
            "vision.sprite_detector",
            "vision.ocr",
            "scheduler.dag",
            "scheduler.executor",
            "scheduler.branch",
            "scheduler.foreach",
            "scheduler.subgraph",
            "scheduler.event_bus",
            "scheduler.onedragon_plan",
        ],
    },
    {
        "id": "realtime",
        "name": "实时任务",
        "route": "/realtime",
        "icon": "crosshair",
        "accent": "#f59e0b",
        "summary": "低延迟轮询：自动丢球、遇敌响应、同行确认；不需要 DAG 与路线规划。",
        "components": [
            "capture.mock_window",
            "capture.windows_window",
            "capture.frame_digest",
            "vision.template_match",
            "vision.edge_preprocess",
            "vision.scene_classify",
            "input.mock",
            "input.sendinput",
            "input.interception",
            "input.key_queue",
            "battle.dataset",
            "battle.team_builder",
            "battle.mcts",
            "battle.damage_model",
            "battle.responder",
            "battle.turn_state",
            "capture.foreground",
            "vision.sprite_detector",
            "vision.ocr",
            "input.hotkey",
            "sift.kalman_tracker",
            "scheduler.session_loop",
            "scheduler.capture_fsm",
            "scheduler.event_bus",
        ],
    },
    {
        "id": "tracker",
        "name": "地图追踪",
        "route": "/tracker",
        "icon": "target",
        "accent": "#059669",
        "summary": "只关心定位：小地图区域、SIFT 特征、锚点、单应性与轨迹，完全不需要输入与对战。",
        "components": [
            "capture.mock_window",
            "capture.windows_window",
            "capture.frame_digest",
            "sift.minimap_region",
            "sift.features",
            "sift.anchor_index",
            "sift.homography",
            "sift.trajectory",
            "sift.external_tracker",
            "sift.kalman_tracker",
            "capture.foreground",
            "scheduler.session_loop",
            "scheduler.event_bus",
        ],
    },
    {
        "id": "workflow",
        "name": "独立任务",
        "route": "/workflows",
        "icon": "workflow",
        "accent": "#7c3aed",
        "summary": "自绘 DAG：分支、循环、子图与变量；按节点实际用到的组元装配执行环境。",
        "components": [
            "capture.mock_window",
            "capture.windows_window",
            "capture.frame_digest",
            "vision.template_match",
            "vision.edge_preprocess",
            "vision.scene_classify",
            "vision.roi",
            "input.mock",
            "input.sendinput",
            "input.interception",
            "input.key_queue",
            "battle.turn_state",
            "capture.foreground",
            "vision.sprite_detector",
            "vision.ocr",
            "scheduler.dag",
            "scheduler.executor",
            "scheduler.branch",
            "scheduler.foreach",
            "scheduler.subgraph",
            "scheduler.event_bus",
        ],
    },
    {
        "id": "map",
        "name": "资源地图",
        "route": "/map",
        "icon": "map",
        "accent": "#2563eb",
        "summary": "大地图浏览、点位筛选与路线生成，共用 SIFT 定位与路线组元。",
        "components": [
            "capture.mock_window",
            "capture.windows_window",
            "capture.frame_digest",
            "capture.foreground",
            "vision.roi",
            "sift.minimap_region",
            "sift.features",
            "sift.anchor_index",
            "sift.homography",
            "sift.route_plan",
        ],
    },
    {
        "id": "battle",
        "name": "对战实验室",
        "route": "/battle",
        "icon": "battle",
        "accent": "#db2777",
        "summary": "纯决策功能：只用对战引擎的数据库、队伍、MCTS 与伤害模型，不接截图和输入。",
        "components": [
            "battle.dataset",
            "battle.team_builder",
            "battle.mcts",
            "battle.damage_model",
        ],
    },
    {
        "id": "dex",
        "name": "图鉴速查",
        "route": "/dex",
        "icon": "database",
        "accent": "#d97706",
        "summary": "只读取对战引擎的图鉴数据组元，提供精灵/技能快速查询，不接截图、输入或 MCTS。",
        "components": [
            "battle.dataset",
        ],
    },
    {
        "id": "pvp",
        "name": "PvP 平衡",
        "route": "/pvp",
        "icon": "battle",
        "accent": "#e11d48",
        "summary": "只用对战引擎的数据、队伍、MCTS 与伤害模型做 6v6 阵容研究与推演，不接截图与实时输入。",
        "components": [
            "battle.dataset",
            "battle.team_builder",
            "battle.mcts",
            "battle.damage_model",
        ],
    },
    {
        "id": "pet",
        "name": "桌宠工坊",
        "route": "/pet",
        "icon": "spark",
        "accent": "#f472b6",
        "summary": "只读取图鉴数据组元，用 CSS 呈现可拖动的桌面伙伴；不触发任何游戏操作。",
        "components": [
            "battle.dataset",
        ],
    },
    {
        "id": "harness",
        "name": "AI Harness",
        "route": "/harness",
        "icon": "spark",
        "accent": "#0891b2",
        "summary": "给外部智能体的控制面：按需调用感知、输入、定位、对战与调度组元。",
        "components": [
            "capture.mock_window",
            "capture.windows_window",
            "capture.frame_digest",
            "capture.scene_switch",
            "capture.foreground",
            "vision.template_match",
            "vision.edge_preprocess",
            "vision.scene_classify",
            "vision.roi",
            "vision.sprite_detector",
            "vision.ocr",
            "input.mock",
            "input.sendinput",
            "input.interception",
            "input.key_queue",
            "input.hotkey",
            "sift.minimap_region",
            "sift.features",
            "sift.anchor_index",
            "sift.homography",
            "sift.trajectory",
            "sift.kalman_tracker",
            "sift.route_plan",
            "battle.dataset",
            "battle.team_builder",
            "battle.mcts",
            "battle.damage_model",
            "battle.turn_state",
            "scheduler.dag",
            "scheduler.executor",
            "scheduler.session_loop",
            "scheduler.event_bus",
            "scheduler.onedragon_plan",
        ],
    },
]


COMPONENT_STATUS: Dict[str, tuple[str, str]] = {
    "capture.mock_window": ("ready", "模拟场景端到端验证"),
    "capture.windows_window": ("partial", "Windows 实机窗口未在当前沙箱验证"),
    "capture.frame_digest": ("ready", ""),
    "capture.scene_switch": ("partial", "仅用于模拟目标演示"),
    "vision.template_match": ("ready", ""),
    "vision.edge_preprocess": ("ready", ""),
    "vision.scene_classify": ("ready", ""),
    "vision.roi": ("ready", ""),
    "input.mock": ("ready", ""),
    "input.sendinput": ("partial", "Windows 实机未在当前沙箱验证"),
    "input.interception": ("partial", "需要 Interception 驱动，未实机验证"),
    "input.key_queue": ("ready", ""),
    "sift.minimap_region": ("ready", ""),
    "sift.features": ("ready", ""),
    "sift.anchor_index": ("ready", ""),
    "sift.homography": ("ready", ""),
    "sift.trajectory": ("partial", "已接卡尔曼平滑与短时预测，丢失重定位仍依赖下一帧 SIFT"),
    "sift.route_plan": ("partial", "最近邻路线，未做避障或真实路网"),
    "sift.external_tracker": ("partial", "Windows WPF 可选包；Linux 只能解包与校验，不能启动"),
    "battle.dataset": ("ready", ""),
    "battle.team_builder": ("ready", ""),
    "battle.mcts": ("ready", ""),
    "battle.damage_model": ("ready", ""),
    "battle.responder": ("partial", "已接回合状态识别，策略仍以配置规则为主"),
    "scheduler.dag": ("ready", ""),
    "scheduler.executor": ("ready", ""),
    "scheduler.branch": ("ready", ""),
    "scheduler.foreach": ("ready", ""),
    "scheduler.subgraph": ("ready", ""),
    "scheduler.event_bus": ("ready", ""),
    "scheduler.session_loop": ("ready", ""),
    "scheduler.capture_fsm": ("partial", "已接候选检测与跟踪，未接瞄准 PID"),
    "scheduler.onedragon_plan": ("ready", ""),
    "capture.foreground": ("partial", "Windows 实机焦点切换未在当前沙箱验证"),
    "vision.sprite_detector": ("ready", "轮廓/模板回退已验证；ONNX 模型可选"),
    "vision.ocr": ("partial", "内置数字/百分比 OCR 已验证；通用中文文本需安装 Tesseract"),
    "input.hotkey": ("partial", "Windows RegisterHotKey 已实现，未在实机验证"),
    "sift.kalman_tracker": ("ready", "位置平滑与 IoU 多目标关联已验证"),
    "battle.turn_state": ("ready", "模拟战斗界面已验证血条/回合/技能；实机 ROI 需校准"),
}

MISSING_COMPONENTS: List[Dict[str, str]] = []

ENGINE_GROUPS: List[Dict[str, Any]] = [
    {
        "id": "sense",
        "name": "感知引擎",
        "exe": "RocogiSense",
        "engines": ["capture", "vision"],
        "summary": "截图 + 模板匹配 + 场景分类，输出像素与语义。",
        "actions": ["capture", "classify", "match", "observe", "templates", "sprites", "ocr", "foreground"],
    },
    {
        "id": "input",
        "name": "输入引擎",
        "exe": "RocogiInput",
        "engines": ["input"],
        "summary": "模拟 / SendInput / Interception 键鼠动作。",
        "actions": ["press", "click", "move", "sequence", "backend", "hotkey"],
    },
    {
        "id": "sift",
        "name": "定位引擎",
        "exe": "RocogiSift",
        "engines": ["sift"],
        "summary": "SIFT 特征、锚点、单应性定位、路线规划与可选 Windows 外置工具。",
        "actions": ["locate", "meta", "points", "route", "anchors", "tracker_info", "tracker_prepare", "tracker_launch"],
    },
    {
        "id": "battle",
        "name": "对战引擎",
        "exe": "RocogiBattle",
        "engines": ["battle", "dex", "pvp"],
        "summary": "图鉴数据、阵容分析、MCTS 决策与 6v6 推演。",
        "actions": ["dex_list", "dex_detail", "dex_skills", "analyze", "decide", "simulate", "matchup", "meta", "turn_state"],
    },
    {
        "id": "flow",
        "name": "调度引擎",
        "exe": "RocogiFlow",
        "engines": ["scheduler"],
        "summary": "工作流 DAG、节点执行、运行事件与一条龙计划。",
        "actions": ["workflows", "run", "status", "stop", "onedragon_plan", "onedragon_run", "settings"],
    },
    {
        "id": "core",
        "name": "统一小引擎",
        "exe": "RocogiEngine",
        "engines": ["capture", "vision", "input", "sift", "battle", "scheduler"],
        "summary": "无 FastAPI / 无 UI 的 headless 统一入口，按 group.action 路由。",
        "actions": ["*"],
    },
]


def _component_index() -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for engine in ENGINES:
        for component in engine["components"]:
            if component["id"] in index:
                raise ValueError(f"duplicate component id: {component['id']}")
            index[component["id"]] = {**component, "engineId": engine["id"]}
    return index


def build_registry() -> Dict[str, Any]:
    """Return the full engine/component/feature reuse graph."""
    index = _component_index()
    unknown = sorted(
        {cid for feature in FEATURES for cid in feature["components"] if cid not in index}
    )
    if unknown:
        raise ValueError(f"features reference unknown components: {', '.join(unknown)}")
    unknown_status = sorted(set(COMPONENT_STATUS) - set(index))
    if unknown_status:
        raise ValueError(f"COMPONENT_STATUS references unknown components: {', '.join(unknown_status)}")
    missing_status = sorted(set(index) - set(COMPONENT_STATUS))
    if missing_status:
        raise ValueError(f"COMPONENT_STATUS missing components: {', '.join(missing_status)}")

    usage: Dict[str, List[str]] = {cid: [] for cid in index}
    for feature in FEATURES:
        for cid in feature["components"]:
            usage[cid].append(feature["id"])

    engines: List[Dict[str, Any]] = []
    for engine in ENGINES:
        components = []
        for component in engine["components"]:
            features = usage[component["id"]]
            status, note = COMPONENT_STATUS.get(
                component["id"], ("partial", "尚未标注实现状态")
            )
            components.append(
                {
                    **component,
                    "engineId": engine["id"],
                    "features": features,
                    "reuse": len(features),
                    "status": status,
                    "statusNote": note,
                }
            )
        engines.append({**engine, "components": components})

    features: List[Dict[str, Any]] = []
    for feature in FEATURES:
        ids = feature["components"]
        engine_ids = sorted({index[cid]["engineId"] for cid in ids}, key=[e["id"] for e in ENGINES].index)
        features.append(
            {
                **feature,
                "componentCount": len(ids),
                "engineCount": len(engine_ids),
                "engines": engine_ids,
                "componentDetails": [
                    {"id": cid, "name": index[cid]["name"], "engineId": index[cid]["engineId"]}
                    for cid in ids
                ],
            }
        )

    matrix = {
        feature["id"]: {
            engine["id"]: [cid for cid in feature["components"] if index[cid]["engineId"] == engine["id"]]
            for engine in ENGINES
        }
        for feature in features
    }

    component_count = len(index)
    feature_count = len(features)
    binding_count = sum(len(feature["components"]) for feature in features)
    reuses = [len(usage[cid]) for cid in index]
    reusable = [cid for cid in index if len(usage[cid]) > 1]

    stats = {
        "engineCount": len(engines),
        "componentCount": component_count,
        "featureCount": feature_count,
        "bindingCount": binding_count,
        "reusableComponents": len(reusable),
        "singleUseComponents": component_count - len(reusable),
        "readyComponents": sum(
            1 for component in index.values() if COMPONENT_STATUS.get(component["id"], ("partial",))[0] == "ready"
        ),
        "partialComponents": sum(
            1 for component in index.values() if COMPONENT_STATUS.get(component["id"], ("partial",))[0] != "ready"
        ),
        "gapCount": len(MISSING_COMPONENTS),
        "maxReuse": max(reuses) if reuses else 0,
        "avgComponentsPerFeature": round(binding_count / feature_count, 1) if feature_count else 0,
        "avgEnginesPerFeature": round(
            sum(feature["engineCount"] for feature in features) / feature_count, 1
        )
        if feature_count
        else 0,
        "coverage": round(binding_count / (component_count * feature_count), 3) if component_count else 0,
    }

    groups = []
    for group in ENGINE_GROUPS:
        component_ids = [
            component["id"]
            for engine in engines
            if engine["id"] in group["engines"]
            for component in engine["components"]
        ]
        groups.append(
            {
                **group,
                "componentCount": len(component_ids),
                "readyCount": sum(
                    1
                    for cid in component_ids
                    if COMPONENT_STATUS.get(cid, ("partial",))[0] == "ready"
                ),
                "components": component_ids,
            }
        )

    return {
        "version": "0.4.6",
        "principle": {
            "title": "功能只取组元，组元服务多个功能",
            "rules": [
                "一个主要功能只装配完成它所需的那部分引擎组元。",
                "同一个引擎组元可以被任意多个功能复用，不复制实现。",
                "引擎负责能力边界，功能负责场景编排。",
            ],
            "reference": {
                "name": "SCH-CMYK/game-automation",
                "url": "https://github.com/SCH-CMYK/game-automation",
                "pattern": "src/engine 提供截图 / 视觉 / 定位 / 输入组元；src/automation 只组合其中一部分来实现导航、采矿、逃跑等功能。",
            },
        },
        "stats": stats,
        "engines": engines,
        "features": features,
        "groups": groups,
        "gaps": MISSING_COMPONENTS,
        "matrix": matrix,
        "usage": usage,
    }
