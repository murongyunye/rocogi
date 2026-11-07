from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

if getattr(sys, "frozen", False):
    ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    RUNTIME_DIR = Path(sys.executable).resolve().parent / "runtime"
else:
    ROOT = Path(__file__).resolve().parents[2]
    RUNTIME_DIR = ROOT / "runtime"

DATA_DIR = ROOT / "data"
DB_PATH = RUNTIME_DIR / "rocoflow.db"
TEMPLATE_DIR = DATA_DIR / "templates"
MAP_DIR = DATA_DIR / "map"
BATTLE_DB = ROOT / "backend" / "vendor" / "nrc_ai" / "data" / "nrc.db"
# preferred battle dataset: BWIKI Lua modules import (see datasets/bwiki/PROVENANCE.md)
BWIKI_DB = Path(os.environ.get("ROCOFLOW_BWIKI_DB", "")) if os.environ.get("ROCOFLOW_BWIKI_DB") \
    else ROOT / "datasets" / "bwiki" / "bwiki_battle.db"
# community PvP dataset: six stats, skill power/energy, traits, usage stats
# built by datasets/tools/pvp/{fetch,import}_pvp.py from three upstream repos
PVP_DB = Path(os.environ.get("ROCOFLOW_PVP_DB", "")) if os.environ.get("ROCOFLOW_PVP_DB") \
    else ROOT / "datasets" / "pvp" / "pvp_data.db"
VENDOR_DIR = ROOT / "backend" / "vendor" / "nrc_ai"
FRONTEND_DIST = ROOT / "frontend" / "dist"

if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

DEFAULT_SETTINGS: Dict[str, Any] = {
    "target": {
        "slot": "nrc-game",
        "kind": "mock",
        "window_title": "洛克王国：世界",
        "capture_fps": 4,
        "scale": 1.0,
    },
    "input": {
        "backend": "mock",
    },
    "hotkeys": {
        "enabled": True,
        "start": "f9",
        "stop": "f10",
        "tracker": "f11",
    },
    "engine": {
        "max_steps": 1200,
        "max_visits": 80,
        "step_delay_ms": 0,
    },
    "vision": {
        "threshold": 0.5,
        "use_edges": True,
        "downscale": 0.5,
    },
    "map": {
        "position_source": "mock",
        "sift_max_edge": 1600,
        "cache_anchors": True,
        "minimap_region": [0.84, 0.0275, 0.1172, 0.1875],
    },
    "battle": {
        "simulations": 40,
        "max_turns": 24,
    },
    "realtime": {
        "interval": 0.6,
        "auto_ball": True,
        "battle_response": True,
        "party_confirm": True,
        "normal_strategy": "gather",
        "polluted_strategy": "escape",
        "threshold": 0.45,
        "save_screenshots": True,
        # 捕捉状态机：扫描 → 丢球 → 验证 → 重试，空视野平移搜索
        "capture_retries": 3,
        "capture_verify": 1.2,
        "capture_pan": True,
        "capture_pan_steps": 6,
        "capture_pan_pixels": 90,
    },
    "tracker": {
        "interval": 0.5,
        "confidenceMin": 0.25,
        "screenshotEvery": 2,
    },
    "demo": {
        "scene": "auto",
    },
}

ENGINE_PRESETS = {
    "demo": {
        "name": "演示 / 模拟目标",
        "description": "无需游戏，使用合成窗口演示全部能力，适合首次启动与调试节点。",
        "tag": "推荐首次使用",
        "settings": {
            "target": {"kind": "mock", "window_title": "洛克王国：世界", "capture_fps": 4, "scale": 1.0},
            "input": {"backend": "mock"},
            "vision": {"threshold": 0.5, "use_edges": True, "downscale": 0.5},
            "map": {"position_source": "mock", "sift_max_edge": 1600, "cache_anchors": True},
            "engine": {"max_steps": 1200, "max_visits": 80},
            "battle": {"simulations": 40, "max_turns": 24},
            "realtime": {"interval": 0.6, "threshold": 0.45},
            "tracker": {"interval": 0.5, "confidenceMin": 0.25},
            "demo": {"scene": "auto"},
        },
    },
    "windows_sendinput": {
        "name": "Windows 实机 · SendInput",
        "description": "连接真实游戏窗口，使用系统级 SendInput；兼容性优先，无需安装驱动。",
        "tag": "实机入门",
        "settings": {
            "target": {"kind": "windows", "window_title": "洛克王国：世界", "capture_fps": 4, "scale": 1.0, "force_foreground": True},
            "input": {"backend": "windows"},
            "vision": {"threshold": 0.55, "use_edges": True, "downscale": 0.5},
            "map": {"position_source": "sift", "sift_max_edge": 1600, "cache_anchors": True},
            "engine": {"max_steps": 1400, "max_visits": 100},
            "battle": {"simulations": 50, "max_turns": 28},
            "realtime": {"interval": 0.5, "threshold": 0.5},
            "tracker": {"interval": 0.5, "confidenceMin": 0.3},
        },
    },
    "windows_interception": {
        "name": "Windows 实机 · Interception",
        "description": "驱动层键鼠模拟，适合需要更稳定输入的实机环境；需要 Interception 驱动。",
        "tag": "实机推荐",
        "settings": {
            "target": {"kind": "windows", "window_title": "洛克王国：世界", "capture_fps": 5, "scale": 1.0, "force_foreground": True},
            "input": {"backend": "interception"},
            "vision": {"threshold": 0.52, "use_edges": True, "downscale": 0.5},
            "map": {"position_source": "sift", "sift_max_edge": 1600, "cache_anchors": True},
            "engine": {"max_steps": 1600, "max_visits": 120},
            "battle": {"simulations": 60, "max_turns": 30},
            "realtime": {"interval": 0.4, "threshold": 0.48},
            "tracker": {"interval": 0.4, "confidenceMin": 0.3},
        },
    },
    "low_latency": {
        "name": "低延迟实时",
        "description": "提高采帧频率、降低识别与模拟规模，适合实时战斗和高速丢球。",
        "tag": "实时优先",
        "settings": {
            "target": {"kind": "windows", "window_title": "洛克王国：世界", "capture_fps": 8, "scale": 1.0, "force_foreground": True},
            "input": {"backend": "interception"},
            "vision": {"threshold": 0.58, "use_edges": True, "downscale": 0.5},
            "map": {"position_source": "sift", "sift_max_edge": 1200, "cache_anchors": True},
            "engine": {"max_steps": 2000, "max_visits": 160},
            "battle": {"simulations": 20, "max_turns": 16},
            "realtime": {"interval": 0.25, "threshold": 0.5},
            "tracker": {"interval": 0.25, "confidenceMin": 0.25},
        },
    },
    "accuracy": {
        "name": "高精度识别",
        "description": "提高模板阈值与 SIFT 锚点精度、增加 MCTS 模拟次数，适合离线分析与稳定跑图。",
        "tag": "精度优先",
        "settings": {
            "target": {"kind": "windows", "window_title": "洛克王国：世界", "capture_fps": 3, "scale": 1.0, "force_foreground": True},
            "input": {"backend": "windows"},
            "vision": {"threshold": 0.65, "use_edges": True, "downscale": 0.6},
            "map": {"position_source": "sift", "sift_max_edge": 2048, "cache_anchors": True},
            "engine": {"max_steps": 1000, "max_visits": 60},
            "battle": {"simulations": 120, "max_turns": 40},
            "realtime": {"interval": 1.0, "threshold": 0.55},
            "tracker": {"interval": 0.8, "confidenceMin": 0.2},
        },
    },
}


def ensure_dirs() -> None:
    for path in (RUNTIME_DIR, RUNTIME_DIR / "runs", RUNTIME_DIR / "cache"):
        path.mkdir(parents=True, exist_ok=True)


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_settings(db) -> Dict[str, Any]:
    stored = db.get_setting("app", {}) or {}
    return deep_merge(DEFAULT_SETTINGS, stored)


def save_settings(db, patch: Dict[str, Any]) -> Dict[str, Any]:
    current = load_settings(db)
    merged = deep_merge(current, patch)
    db.set_setting("app", merged)
    return merged


def apply_engine_preset(db, preset_id: str) -> Dict[str, Any]:
    preset = ENGINE_PRESETS.get(preset_id)
    if not preset:
        raise ValueError(f"unknown engine preset: {preset_id}")
    settings = save_settings(db, preset["settings"])
    settings["engine"]["preset"] = preset_id
    db.set_setting("app", settings)
    return {"preset": preset_id, "name": preset["name"], "settings": settings}


def resolve_asset(rel: str) -> Path:
    """Resolve a data asset path without allowing traversal."""
    candidate = (DATA_DIR / rel).resolve()
    if DATA_DIR not in candidate.parents and candidate != DATA_DIR:
        raise ValueError("invalid asset path")
    return candidate


def platform_capabilities() -> Dict[str, Any]:
    return {
        "platform": sys.platform,
        "windows": sys.platform.startswith("win"),
        "mock_target": True,
        "interception": os.environ.get("ROCOFLOW_INTERCEPTION", "") == "1",
        "sift": True,
        "battle_ai": BATTLE_DB.exists(),
        "bwiki_battle": BWIKI_DB.exists(),
        "reads_game_memory": False,
        "data_dir": str(DATA_DIR),
        "engine": "python",
    }
